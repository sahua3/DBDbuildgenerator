"""
Shrine of Secrets scraper.

dbd.tricky.lol/api/shrine returns JSON like:
{
  "shrine": [
    {"id": "flipFlop", "name": "Flip Flop", ...},
    {"id": "backgroundPlayer", "name": "Background Player", ...},
    ...
  ]
}

The "id" field is camelCase — we use "name" when available, falling back
to converting the id to Title Case.
"""
import logging
import re
import httpx
from datetime import datetime, timedelta, timezone
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

SHRINE_API_URL = "https://dbd.tricky.lol/api/shrine"
SHRINE_FALLBACK_URL = "https://dbd.tricky.lol/shrine"


def camel_to_title(s: str) -> str:
    """Convert camelCase / PascalCase to Title Case words. e.g. 'backgroundPlayer' → 'Background Player'"""
    # Insert space before each uppercase letter that follows a lowercase
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    # Also handle runs like 'BBQ' → keep as-is but separate from next word
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return spaced.title()


def extract_name_from_entry(entry) -> str | None:
    """Extract a clean perk name from a shrine API entry (str or dict)."""
    if isinstance(entry, str):
        # Raw string — might be camelCase id or already a name
        if entry[0].islower() or "_" in entry:
            return camel_to_title(entry.replace("_", " "))
        return entry.strip()

    if isinstance(entry, dict):
        # Prefer explicit "name" field
        name = entry.get("name") or entry.get("perkName") or entry.get("displayName")
        if name and isinstance(name, str) and len(name) > 1:
            return name.strip()
        # Fall back to converting the id
        perk_id = entry.get("id") or entry.get("perkId") or entry.get("slug") or ""
        if perk_id:
            return camel_to_title(str(perk_id).replace("_", " "))

    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def scrape_shrine() -> list[str]:
    """
    Fetch current Shrine of Secrets perk names.
    Returns list of up to 4 perk names (survivors only when possible).
    """
    # ── Try JSON API ──────────────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                SHRINE_API_URL,
                headers={"User-Agent": "Mozilla/5.0 (compatible; DBDBuilds/1.0)"},
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.debug(f"Shrine API raw response: {str(data)[:500]}")

                entries = []
                # Handle {"shrine": [...]} or {"perks": [...]} or bare list
                if isinstance(data, list):
                    entries = data
                elif isinstance(data, dict):
                    entries = (
                        data.get("shrine")
                        or data.get("perks")
                        or data.get("items")
                        or data.get("results")
                        or []
                    )
                    # Some APIs wrap it deeper: {"data": {"shrine": [...]}}
                    if not entries and "data" in data:
                        inner = data["data"]
                        if isinstance(inner, list):
                            entries = inner
                        elif isinstance(inner, dict):
                            entries = inner.get("shrine") or inner.get("perks") or []

                names = []
                for entry in entries:
                    name = extract_name_from_entry(entry)
                    if name and name not in names:
                        # Skip obvious killer perks if role info is available
                        if isinstance(entry, dict):
                            role = (entry.get("role") or entry.get("type") or "").lower()
                            if "killer" in role:
                                continue
                        names.append(name)

                if names:
                    logger.info(f"Shrine perks via API: {names}")
                    return names[:4]

    except Exception as e:
        logger.warning(f"Shrine JSON API failed: {e}")

    # ── Fallback: scrape the HTML page ────────────────────────────────────────
    try:
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                SHRINE_FALLBACK_URL,
                headers={"User-Agent": "Mozilla/5.0 (compatible; DBDBuilds/1.0)"},
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        names = []

        # data-name / data-perk attributes
        for el in soup.select("[data-name],[data-perk],[data-perkname]"):
            n = el.get("data-name") or el.get("data-perk") or el.get("data-perkname")
            if n and n not in names:
                names.append(n.strip())

        # img alt tags in shrine sections
        if not names:
            section = soup.select_one(".shrine,.perks,[class*='shrine'],[class*='perk-list']")
            target = section or soup
            for img in target.find_all("img", alt=True):
                alt = img["alt"].strip()
                if alt and len(alt) > 3 and alt not in names:
                    names.append(alt)

        if names:
            logger.info(f"Shrine perks via HTML scrape: {names}")
            return names[:4]

    except Exception as e:
        logger.error(f"Shrine HTML scrape failed: {e}")

    return []


async def update_shrine_in_db(db, perk_names: list[str]) -> None:
    """Clear old shrine flags, set new ones, insert history record."""
    from sqlalchemy import select, update
    from app.models.perk import Perk
    from app.models.shrine import Shrine

    if not perk_names:
        logger.warning("No shrine perks — skipping DB update")
        return

    await db.execute(update(Perk).values(in_shrine=False))

    matched = []
    for name in perk_names:
        # Exact match first
        perk = (await db.execute(
            select(Perk).where(Perk.name.ilike(name))
        )).scalar_one_or_none()

        # Fuzzy match fallback
        if not perk:
            perk = (await db.execute(
                select(Perk).where(Perk.name.ilike(f"%{name}%"))
            )).scalar_one_or_none()

        if perk:
            perk.in_shrine = True
            matched.append(perk.name)
            logger.info(f"Marked shrine perk: {perk.name}")
        else:
            logger.warning(f"Shrine perk not found in DB: '{name}'")

    valid_until = datetime.now(timezone.utc) + timedelta(days=7)
    db.add(Shrine(perk_names=perk_names, valid_until=valid_until))
    await db.commit()
    logger.info(f"Shrine updated. Matched {len(matched)}/{len(perk_names)}: {matched}")


async def run_shrine_sync(db) -> dict:
    perk_names = await scrape_shrine()
    if perk_names:
        await update_shrine_in_db(db, perk_names)
    return {"shrine_perks": perk_names}
