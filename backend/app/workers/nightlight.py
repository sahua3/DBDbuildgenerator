"""
Nightlight.gg scraper.

Nightlight is a React SPA. We use Playwright to render it, then extract
perk data from whatever DOM structure is actually present.

Target URL:
https://nightlight.gg/perks/viewer?role=survivor&shown=escape_rate&sort=pick&start_days=28&compact=true
"""
import asyncio
import logging
import re
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

NIGHTLIGHT_PERKS_URL = (
    "https://nightlight.gg/perks/viewer"
    "?role=survivor&shown=escape_rate&sort=pick&start_days=28&compact=true"
)
NIGHTLIGHT_BUILDS_URL = (
    "https://nightlight.gg/builds?role=survivor&sort=popular&start_days=28"
)


async def _get_page_html(url: str, wait_for_text: Optional[str] = None) -> Optional[str]:
    """
    Launch headless Chromium, load url, optionally wait until some text
    appears in the page, then return full page HTML.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            logger.info(f"Loading {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Give React time to hydrate — wait up to 12s for *any* content
            for _ in range(12):
                content = await page.content()
                if wait_for_text and wait_for_text in content:
                    break
                if not wait_for_text and len(content) > 5000:
                    break
                await asyncio.sleep(1)

            html = await page.content()
            await browser.close()
            return html
    except Exception as e:
        logger.error(f"Playwright error loading {url}: {e}")
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=15))
async def scrape_perk_pick_rates() -> list[dict]:
    """
    Scrape Nightlight perk viewer for survivor perk pick rates.
    Returns list of {"name": str, "pick_rate": float, "rank": int}
    """
    html = await _get_page_html(NIGHTLIGHT_PERKS_URL, wait_for_text="pick")
    if not html:
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    perks = []

    # Strategy 1: look for any element whose text matches a % pattern near a name
    # Nightlight renders rows as divs with perk name + stats
    # Try multiple selector patterns and use whichever finds data

    # Pattern A: table rows (some layouts do use tables)
    rows = soup.select("table tbody tr")
    if rows:
        logger.info(f"Found {len(rows)} table rows")
        for rank, row in enumerate(rows, 1):
            cells = row.find_all("td")
            if not cells:
                continue
            name = cells[0].get_text(strip=True)
            pick_rate = 0.0
            for cell in cells[1:]:
                m = re.search(r"(\d+\.?\d*)%", cell.get_text())
                if m:
                    pick_rate = float(m.group(1)) / 100.0
                    break
            if name:
                perks.append({"name": name, "pick_rate": pick_rate, "rank": rank})

    # Pattern B: div/li rows — Nightlight often uses a list of stat rows
    if not perks:
        # Find all elements that contain a percentage AND a nearby text that looks like a perk name
        stat_rows = soup.select("[class*='row'], [class*='perk'], [class*='item'], [class*='stat']")
        logger.info(f"Trying {len(stat_rows)} stat-row elements")
        seen = set()
        for rank, el in enumerate(stat_rows, 1):
            text = el.get_text(" ", strip=True)
            pct_match = re.search(r"(\d+\.?\d*)%", text)
            if not pct_match:
                continue
            # Extract the name — usually the first significant text node
            name_el = el.find(["span", "a", "div", "p"])
            name = (name_el.get_text(strip=True) if name_el else text.split("%")[0]).strip()
            name = re.sub(r"\s+", " ", name)[:80]
            if not name or name in seen or len(name) < 3:
                continue
            seen.add(name)
            pick_rate = float(pct_match.group(1)) / 100.0
            perks.append({"name": name, "pick_rate": pick_rate, "rank": rank})

    # Pattern C: scrape any text block that has "Perk Name ... X.XX%" pattern
    if not perks:
        logger.info("Falling back to regex over full page text")
        page_text = soup.get_text(" ")
        # Match lines like "Dead Hard  12.34%"
        for rank, m in enumerate(
            re.finditer(r"([A-Z][a-zA-Z ':!-]{3,50})\s+(\d+\.\d+)%", page_text), 1
        ):
            name = m.group(1).strip()
            pick_rate = float(m.group(2)) / 100.0
            perks.append({"name": name, "pick_rate": pick_rate, "rank": rank})
            if rank >= 80:
                break

    logger.info(f"Scraped {len(perks)} perks from Nightlight")
    return perks


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=15))
async def scrape_top_builds() -> list[list[str]]:
    """
    Scrape top survivor builds from Nightlight.
    Returns list of builds, each a list of 4 perk names.
    """
    html = await _get_page_html(NIGHTLIGHT_BUILDS_URL, wait_for_text="perk")
    if not html:
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    builds = []

    # Strategy: find groups of 4 perk-like names clustered together
    # Nightlight build cards usually have img[alt] or span text for each perk

    # Pattern A: explicit build card containers
    for card_sel in [
        "[class*='build-card']",
        "[class*='build ']",
        "[class*='BuildCard']",
        "[class*='perk-set']",
        "[class*='loadout']",
    ]:
        cards = soup.select(card_sel)
        if cards:
            logger.info(f"Found {len(cards)} build cards via '{card_sel}'")
            for card in cards[:60]:
                names = _extract_perk_names_from_element(card)
                if len(names) >= 4:
                    builds.append(names[:4])
            if builds:
                break

    # Pattern B: find all img[alt] that look like perk names and group by proximity
    if not builds:
        logger.info("Trying img[alt] grouping strategy")
        all_imgs = soup.find_all("img", alt=True)
        perk_like = [
            img["alt"].strip()
            for img in all_imgs
            if _looks_like_perk_name(img["alt"])
        ]
        # Group into chunks of 4
        for i in range(0, len(perk_like) - 3, 4):
            chunk = perk_like[i : i + 4]
            if len(set(chunk)) == 4:  # all unique
                builds.append(chunk)
        logger.info(f"Extracted {len(builds)} builds from img alts")

    logger.info(f"Total builds scraped: {len(builds)}")
    return builds


def _extract_perk_names_from_element(el) -> list[str]:
    """Pull perk names out of a BeautifulSoup element."""
    names = []
    # img alt tags first
    for img in el.find_all("img", alt=True):
        alt = img["alt"].strip()
        if _looks_like_perk_name(alt):
            names.append(alt)
    # span/div text if no imgs found
    if not names:
        for tag in el.find_all(["span", "div", "p"]):
            text = tag.get_text(strip=True)
            if _looks_like_perk_name(text):
                names.append(text)
    return names[:4]


def _looks_like_perk_name(text: str) -> bool:
    """Heuristic: perk names are title-cased, 3-50 chars, no URLs or numbers."""
    text = text.strip()
    if not (3 <= len(text) <= 60):
        return False
    if re.search(r"https?://|\.com|\.gg|\d{4}", text):
        return False
    if text[0].isupper() and " " in text:
        return True
    # Single-word title-cased names like "Adrenaline"
    if text[0].isupper() and text.isalpha():
        return True
    return False


def compute_co_occurrence(builds: list[list[str]]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for build in builds:
        perks = list(set(build))
        for i in range(len(perks)):
            for j in range(i + 1, len(perks)):
                pair = tuple(sorted([perks[i], perks[j]]))
                counts[pair] = counts.get(pair, 0) + 1
    return counts


async def run_full_nightlight_sync(db) -> dict:
    """Full sync: scrape pick rates + builds, update DB, rebuild graph."""
    from sqlalchemy import select
    from app.models.perk import Perk
    from app.models.edge import PerkEdge
    from app.services.graph import load_graph_from_db
    import uuid

    logger.info("Starting Nightlight sync...")

    # ── 1. Pick rates ────────────────────────────────────────────────────────
    pick_data = await scrape_perk_pick_rates()
    perks_updated = 0

    if pick_data:
        pick_map = {p["name"].lower(): p for p in pick_data}
        max_pick = max((p["pick_rate"] for p in pick_data), default=1.0) or 1.0

        perk_rows = (await db.execute(select(Perk))).scalars().all()
        for perk in perk_rows:
            data = pick_map.get(perk.name.lower())
            if data:
                perk.pick_rate = data["pick_rate"] / max_pick
                perk.nightlight_rank = data["rank"]
                perks_updated += 1

        await db.flush()

        # Recompute per-category weights
        from app.core.config import PERK_CATEGORIES
        for cat in PERK_CATEGORIES:
            cat_perks = [p for p in perk_rows if cat in (p.categories or [])]
            if not cat_perks:
                continue
            max_w = max(p.pick_rate for p in cat_perks) or 1.0
            for p in cat_perks:
                p.category_weight = p.pick_rate / max_w
        await db.flush()
    else:
        logger.warning("No pick rate data scraped — skipping weight update")

    # ── 2. Co-occurrence graph ───────────────────────────────────────────────
    builds = await scrape_top_builds()
    co_counts = compute_co_occurrence(builds)
    edges_written = 0

    if co_counts:
        perk_rows = (await db.execute(select(Perk))).scalars().all()
        name_to_id = {p.name.lower(): str(p.id) for p in perk_rows}
        max_count = max(co_counts.values(), default=1)

        for (name_a, name_b), count in co_counts.items():
            id_a = name_to_id.get(name_a.lower())
            id_b = name_to_id.get(name_b.lower())
            if not id_a or not id_b:
                continue
            if id_a > id_b:
                id_a, id_b = id_b, id_a

            weight = count / max_count
            existing = (
                await db.execute(
                    select(PerkEdge).where(
                        PerkEdge.perk_a_id == uuid.UUID(id_a),
                        PerkEdge.perk_b_id == uuid.UUID(id_b),
                    )
                )
            ).scalar_one_or_none()

            if existing:
                existing.weight = weight
            else:
                db.add(PerkEdge(
                    perk_a_id=uuid.UUID(id_a),
                    perk_b_id=uuid.UUID(id_b),
                    weight=weight,
                ))
            edges_written += 1

        await db.flush()
    else:
        logger.warning("No build co-occurrence data — graph edges unchanged")

    await db.commit()
    await load_graph_from_db(db)

    result = {
        "perks_updated": perks_updated,
        "builds_scraped": len(builds),
        "edges_computed": edges_written,
    }
    logger.info(f"Nightlight sync complete: {result}")
    return result
