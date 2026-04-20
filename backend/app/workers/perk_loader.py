"""
Perk loader worker.

Reads scripts/perks.csv, categorizes each perk, and upserts into the database.

CSV format:
    name,description,owner
    Adrenaline,"You've been through...",Meg Thomas
    Dead Hard,"For one brief moment...",David King
    Self-Care,"You have developed...",Claudette Morel
"""
import asyncio
import csv
import logging
import sys
import os

# Add app to path when run as script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from app.db.session import AsyncSessionLocal, init_db
from app.models.perk import Perk
from app.models.survivor import Survivor
from app.services.categorizer import classify_perk_description
from app.core.config import settings
from sqlalchemy import select

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CSV_PATH = os.environ.get("PERKS_CSV", "/scripts/perks.csv")

# Base game survivors (always available)
BASE_SURVIVORS = {
    "Dwight Fairfield",
    "Meg Thomas",
    "Claudette Morel",
    "Jake Park",
    "Nea Karlsson",
    "Bill Overbeck",
    "Feng Min",
    "David King",
    "Quentin Smith",
    "Detective Tapp",
    "Kate Denson",
    "Adam Francis",
    "Jeff Johansen",
    "Jane Romero",
    "Ash Williams",
    "Nancy Wheeler",
    "Steve Harrington",
    "Yui Kimura",
    "Zarina Kassir",
    "Cheryl Mason",
}


async def load_perks_from_csv(csv_path: str = CSV_PATH) -> None:
    await init_db()

    async with AsyncSessionLocal() as db:
        if not os.path.exists(csv_path):
            logger.error(f"CSV not found at {csv_path}")
            logger.info("Creating sample CSV at that path for reference...")
            _write_sample_csv(csv_path)
            return

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        logger.info(f"Loading {len(rows)} perks from {csv_path}")

        survivor_names: set[str] = set()
        for row in rows:
            owner = (row.get("owner") or "").strip()
            if owner:
                survivor_names.add(owner)

        # Upsert survivors
        for name in survivor_names:
            existing = (
                await db.execute(select(Survivor).where(Survivor.name == name))
            ).scalar_one_or_none()
            if not existing:
                db.add(Survivor(
                    name=name,
                    is_base=name in BASE_SURVIVORS,
                    owned=name in BASE_SURVIVORS,
                ))

        await db.flush()

        # Upsert perks
        loaded = 0
        for row in rows:
            name = (row.get("name") or "").strip()
            description = (row.get("description") or "").strip()
            owner = (row.get("owner") or "").strip() or None

            if not name or not description:
                logger.warning(f"Skipping incomplete row: {row}")
                continue

            categories = classify_perk_description(description)

            existing = (
                await db.execute(select(Perk).where(Perk.name == name))
            ).scalar_one_or_none()

            if existing:
                existing.description = description
                existing.owner = owner
                existing.categories = categories
            else:
                db.add(Perk(
                    name=name,
                    description=description,
                    owner=owner,
                    categories=categories,
                    pick_rate=0.0,
                    category_weight=0.0,
                ))
            loaded += 1

        await db.commit()
        logger.info(f"Successfully loaded {loaded} perks and {len(survivor_names)} survivors.")
        logger.info("Next step: run a Nightlight sync to populate pick rates and graph weights.")


def _write_sample_csv(path: str) -> None:
    """Write a sample CSV so users know the format."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "description", "owner"])
        writer.writerows([
            ["Adrenaline", "You've been through a lot. When the exit gates are powered, you gain a burst of speed and are healed one health state.", "Meg Thomas"],
            ["Dead Hard", "For one brief moment you can avoid damage by activating Dead Hard. You become briefly intangible.", "David King"],
            ["Self-Care", "You have developed the skill to treat yourself. Heal yourself without a Med-Kit at 50% of the normal healing speed.", "Claudette Morel"],
            ["Borrowed Time", "When unhooking a Survivor within the Killer's Terror Radius, the unhooked Survivor benefits from the Endurance status effect.", "Bill Overbeck"],
            ["Decisive Strike", "After being unhooked or unhooking yourself, Decisive Strike activates. If grabbed by the Killer, stun them and escape their grasp.", "Laurie Strode"],
            ["Urban Evasion", "Years of evading people that were after you have made you a natural at moving while crouching. Increases your crouching movement speed.", "Nea Karlsson"],
            ["Spine Chill", "You have a preternatural ability to sense danger. A distant stare sets your teeth on edge. Gain information when the Killer is looking in your direction.", "base"],
            ["Lithe", "After performing a rushed vault, break into a sprint. Causes the Exhausted status effect.", "Feng Min"],
            ["Resilience", "You are motivated in dire situations. While injured, gain a speed bonus to all actions.", "base"],
            ["We'll Make It", "The sight of a crying friend in need fills you with energy. After unhooking a Survivor, gain a temporary boost to healing speed.", "base"],
        ])
    logger.info(f"Sample CSV written to {path}")


if __name__ == "__main__":
    asyncio.run(load_perks_from_csv())
