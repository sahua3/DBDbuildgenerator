"""
Nightlight.gg scraper.

Nightlight is a React SPA — we use Playwright to headlessly render the page,
wait for the table to hydrate, then extract perk pick rates and top builds.

Target URL:
https://nightlight.gg/perks/viewer?role=survivor&shown=escape_rate&sort=pick&start_days=28&compact=true
"""
import asyncio
import logging
import re
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

NIGHTLIGHT_URL = (
    "https://nightlight.gg/perks/viewer"
    "?role=survivor&shown=escape_rate&sort=pick&start_days=28&compact=true"
)

NIGHTLIGHT_BUILDS_URL = "https://nightlight.gg/builds?role=survivor&sort=recent&start_days=28"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def scrape_perk_pick_rates() -> list[dict]:
    """
    Scrape Nightlight perk viewer for survivor perk pick rates.

    Returns list of:
    {
        "name": str,
        "pick_rate": float,   # 0.0 - 1.0
        "rank": int,
    }
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info(f"Navigating to {NIGHTLIGHT_URL}")
            await page.goto(NIGHTLIGHT_URL, wait_until="networkidle", timeout=30000)

            # Wait for the perk table rows to appear
            await page.wait_for_selector("table tbody tr", timeout=15000)

            # Extract perk data from table rows
            rows = await page.query_selector_all("table tbody tr")

            perks = []
            for rank, row in enumerate(rows, start=1):
                cells = await row.query_selector_all("td")
                if len(cells) < 2:
                    continue

                # First cell usually has perk name
                name_el = await cells[0].query_selector("span, a, div")
                if not name_el:
                    name_text = await cells[0].inner_text()
                else:
                    name_text = await name_el.inner_text()

                name = name_text.strip()
                if not name:
                    continue

                # Look for pick rate percentage in any cell
                pick_rate = 0.0
                for cell in cells[1:]:
                    text = (await cell.inner_text()).strip()
                    match = re.search(r"(\d+\.?\d*)%", text)
                    if match:
                        pick_rate = float(match.group(1)) / 100.0
                        break

                perks.append({
                    "name": name,
                    "pick_rate": pick_rate,
                    "rank": rank,
                })

            await browser.close()
            logger.info(f"Scraped {len(perks)} perks from Nightlight")
            return perks

    except Exception as e:
        logger.error(f"Nightlight scrape failed: {e}")
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def scrape_top_builds() -> list[list[str]]:
    """
    Scrape top survivor builds from Nightlight.
    Returns list of builds, each build is a list of 4 perk names.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info(f"Navigating to {NIGHTLIGHT_BUILDS_URL}")
            await page.goto(NIGHTLIGHT_BUILDS_URL, wait_until="networkidle", timeout=30000)

            # Wait for build cards
            await page.wait_for_selector("[class*='build'], [class*='perk-set']", timeout=15000)

            builds = []

            # Try to extract build cards — each card should have 4 perk names
            build_cards = await page.query_selector_all("[class*='build-card'], [class*='build ']")

            for card in build_cards[:50]:  # Limit to top 50
                perk_elements = await card.query_selector_all(
                    "[class*='perk-name'], [class*='perk'] span, [alt]"
                )
                perk_names = []
                for el in perk_elements:
                    tag = await el.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "img":
                        alt = await el.get_attribute("alt")
                        if alt:
                            perk_names.append(alt.strip())
                    else:
                        text = (await el.inner_text()).strip()
                        if text and len(text) > 2:
                            perk_names.append(text)

                if len(perk_names) >= 4:
                    builds.append(perk_names[:4])

            await browser.close()
            logger.info(f"Scraped {len(builds)} builds from Nightlight")
            return builds

    except Exception as e:
        logger.error(f"Nightlight builds scrape failed: {e}")
        return []


def compute_co_occurrence(builds: list[list[str]]) -> dict[tuple[str, str], int]:
    """
    Given a list of builds (each a list of perk names),
    count how many times each pair of perks appears together.
    Returns {(perk_a_name, perk_b_name): count} — pair always sorted alphabetically.
    """
    counts: dict[tuple[str, str], int] = {}

    for build in builds:
        perks = list(set(build))  # deduplicate within build
        for i in range(len(perks)):
            for j in range(i + 1, len(perks)):
                pair = tuple(sorted([perks[i], perks[j]]))
                counts[pair] = counts.get(pair, 0) + 1

    return counts


async def run_full_nightlight_sync(db) -> dict:
    """
    Full sync: scrape pick rates + builds, update DB weights, rebuild graph.
    """
    from sqlalchemy import select, update
    from app.models.perk import Perk
    from app.models.edge import PerkEdge
    from app.services.graph import load_graph_from_db
    import uuid

    logger.info("Starting full Nightlight sync...")

    # 1. Scrape pick rates
    pick_data = await scrape_perk_pick_rates()

    if pick_data:
        # Build name → data map
        pick_map = {p["name"].lower(): p for p in pick_data}
        max_pick = max((p["pick_rate"] for p in pick_data), default=1.0) or 1.0

        # Update perk pick rates in DB
        perk_rows = (await db.execute(select(Perk))).scalars().all()
        for perk in perk_rows:
            data = pick_map.get(perk.name.lower())
            if data:
                perk.pick_rate = data["pick_rate"] / max_pick
                perk.nightlight_rank = data["rank"]
        await db.flush()

        # Recompute category weights
        from sqlalchemy import func
        for cat in ["healing", "stealth", "chase", "gen_speed", "information",
                    "altruism", "escape", "anti_hook", "aura_reading",
                    "exhaustion", "endurance", "second_chance"]:
            cat_perks = [p for p in perk_rows if cat in (p.categories or [])]
            if not cat_perks:
                continue
            max_w = max(p.pick_rate for p in cat_perks) or 1.0
            for p in cat_perks:
                p.category_weight = p.pick_rate / max_w
        await db.flush()

    # 2. Scrape builds and compute co-occurrence
    builds = await scrape_top_builds()
    co_counts = compute_co_occurrence(builds)

    if co_counts:
        # Map perk names → IDs
        perk_rows = (await db.execute(select(Perk))).scalars().all()
        name_to_id = {p.name.lower(): str(p.id) for p in perk_rows}

        max_count = max(co_counts.values(), default=1)

        for (name_a, name_b), count in co_counts.items():
            id_a = name_to_id.get(name_a.lower())
            id_b = name_to_id.get(name_b.lower())
            if not id_a or not id_b:
                continue

            # Ensure canonical ordering (smaller UUID first)
            if id_a > id_b:
                id_a, id_b = id_b, id_a

            weight = count / max_count

            # Upsert edge
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

        await db.flush()

    await db.commit()

    # 3. Rebuild in-memory graph
    await load_graph_from_db(db)

    logger.info("Nightlight sync complete.")
    return {
        "perks_updated": len(pick_data),
        "builds_scraped": len(builds),
        "edges_computed": len(co_counts),
    }
