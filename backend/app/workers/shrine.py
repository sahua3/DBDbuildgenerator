"""
Shrine of Secrets scraper.

Scrapes https://dbd.tricky.lol/shrine weekly.
Updates the shrine_history table and flags perks with in_shrine=True.
"""
import logging
import httpx
from datetime import datetime, timedelta, timezone
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

SHRINE_URL = "https://dbd.tricky.lol/shrine"
SHRINE_API_URL = "https://dbd.tricky.lol/api/shrine"  # JSON API if available


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def scrape_shrine() -> list[str]:
    """
    Scrape current Shrine of Secrets perk names.
    Returns list of 4 perk names.
    
    Tries JSON API first, falls back to HTML parsing.
    """
    # Try JSON API endpoint first
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(SHRINE_API_URL)
            if resp.status_code == 200:
                data = resp.json()
                # Handle various response shapes from dbd.tricky.lol
                if isinstance(data, dict):
                    perks = data.get("perks") or data.get("shrine") or []
                    if isinstance(perks, list) and perks:
                        names = []
                        for p in perks:
                            if isinstance(p, str):
                                names.append(p)
                            elif isinstance(p, dict):
                                n = p.get("name") or p.get("perkName") or p.get("id", "")
                                if n:
                                    names.append(n)
                        if names:
                            logger.info(f"Shrine perks via API: {names}")
                            return names[:4]
    except Exception as e:
        logger.warning(f"Shrine API call failed, falling back to HTML: {e}")

    # Fall back to HTML scraping
    try:
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                SHRINE_URL,
                headers={"User-Agent": "Mozilla/5.0 (compatible; DBDBuilds/1.0)"},
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        perk_names = []

        # Try common patterns used by dbd.tricky.lol
        # Pattern 1: elements with perk names in data-name or title attributes
        for el in soup.select("[data-name], [data-perk]"):
            name = el.get("data-name") or el.get("data-perk")
            if name and name not in perk_names:
                perk_names.append(name)

        # Pattern 2: h2/h3/h4 inside shrine sections
        if not perk_names:
            for el in soup.select(".perk-name, .shrine-perk h3, .perk h2"):
                name = el.get_text(strip=True)
                if name and name not in perk_names:
                    perk_names.append(name)

        # Pattern 3: img alt tags in shrine section
        if not perk_names:
            shrine_section = soup.select_one(".shrine, #shrine, [class*='shrine']")
            if shrine_section:
                for img in shrine_section.select("img[alt]"):
                    alt = img.get("alt", "").strip()
                    if alt and "perk" not in alt.lower():
                        perk_names.append(alt)

        logger.info(f"Shrine perks via HTML: {perk_names[:4]}")
        return perk_names[:4]

    except Exception as e:
        logger.error(f"Shrine HTML scrape failed: {e}")
        return []


async def update_shrine_in_db(db, perk_names: list[str]) -> None:
    """
    1. Clear all in_shrine flags
    2. Set in_shrine=True for matching perks
    3. Insert new shrine record
    """
    from sqlalchemy import select, update
    from app.models.perk import Perk
    from app.models.shrine import Shrine

    if not perk_names:
        logger.warning("No shrine perks found, skipping DB update")
        return

    # Clear all shrine flags
    await db.execute(update(Perk).values(in_shrine=False))

    # Set shrine flags for matched perks
    for name in perk_names:
        # Case-insensitive fuzzy match
        perk = (
            await db.execute(
                select(Perk).where(Perk.name.ilike(f"%{name}%"))
            )
        ).scalar_one_or_none()

        if perk:
            perk.in_shrine = True
            logger.info(f"Marked shrine perk: {perk.name}")
        else:
            logger.warning(f"Shrine perk not found in DB: {name}")

    # Insert shrine history record
    valid_until = datetime.now(timezone.utc) + timedelta(days=7)
    db.add(Shrine(perk_names=perk_names, valid_until=valid_until))

    await db.commit()
    logger.info(f"Shrine updated: {perk_names}")


async def run_shrine_sync(db) -> dict:
    """Full shrine sync: scrape + update DB."""
    perk_names = await scrape_shrine()
    if perk_names:
        await update_shrine_in_db(db, perk_names)
    return {"shrine_perks": perk_names}
