"""
Background scheduler for periodic scraping tasks.

Jobs:
  - Nightlight sync: every 6 hours
  - Shrine sync: weekly, Tuesdays at 12:00 PM EST (shrine resets Tuesdays)
"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
from app.db.session import AsyncSessionLocal, init_db
from app.workers.nightlight import run_full_nightlight_sync
from app.workers.shrine import run_shrine_sync

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def nightlight_job():
    logger.info("Running scheduled Nightlight sync...")
    async with AsyncSessionLocal() as db:
        result = await run_full_nightlight_sync(db)
    logger.info(f"Nightlight sync result: {result}")


async def shrine_job():
    logger.info("Running scheduled Shrine sync...")
    async with AsyncSessionLocal() as db:
        result = await run_shrine_sync(db)
    logger.info(f"Shrine sync result: {result}")


async def run_initial_syncs():
    """Run both syncs on startup to seed fresh data."""
    logger.info("Running initial syncs on startup...")
    try:
        await shrine_job()
    except Exception as e:
        logger.warning(f"Initial shrine sync failed (non-fatal): {e}")

    try:
        await nightlight_job()
    except Exception as e:
        logger.warning(f"Initial Nightlight sync failed (non-fatal): {e}")


async def main():
    await init_db()

    scheduler = AsyncIOScheduler(timezone=settings.shrine_scrape_cron_timezone)

    # Nightlight: every N hours
    scheduler.add_job(
        nightlight_job,
        trigger=IntervalTrigger(hours=settings.nightlight_scrape_interval_hours),
        id="nightlight_sync",
        replace_existing=True,
    )

    # Shrine: weekly on Tuesday at configured time (shrine resets Tuesday EST)
    scheduler.add_job(
        shrine_job,
        trigger=CronTrigger(
            day_of_week="tue",
            hour=settings.shrine_scrape_cron_hour,
            timezone=settings.shrine_scrape_cron_timezone,
        ),
        id="shrine_sync",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started. Nightlight every {settings.nightlight_scrape_interval_hours}h, "
        f"Shrine weekly Tuesday {settings.shrine_scrape_cron_hour}:00 EST"
    )

    # Run initial syncs
    await run_initial_syncs()

    # Keep worker alive
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
