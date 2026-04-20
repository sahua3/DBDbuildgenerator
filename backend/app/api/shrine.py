from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.shrine import Shrine
from app.models.perk import Perk
from app.schemas.schemas import ShrineResponse
from app.workers.shrine import run_shrine_sync
from app.workers.nightlight import run_full_nightlight_sync

router = APIRouter(tags=["Shrine & Admin"])


@router.get("/shrine", response_model=ShrineResponse)
async def get_current_shrine(db: AsyncSession = Depends(get_db)):
    latest = (
        await db.execute(select(Shrine).order_by(Shrine.scraped_at.desc()).limit(1))
    ).scalar_one_or_none()

    if not latest:
        return {
            "perk_names": [],
            "perks": [],
            "scraped_at": None,
            "valid_until": None,
        }

    perks = []
    for name in latest.perk_names:
        perk = (
            await db.execute(select(Perk).where(Perk.name.ilike(f"%{name}%")))
        ).scalar_one_or_none()
        if perk:
            perks.append(perk)

    return {
        "perk_names": latest.perk_names,
        "perks": perks,
        "scraped_at": latest.scraped_at,
        "valid_until": latest.valid_until,
    }


@router.post("/admin/sync/shrine")
async def trigger_shrine_sync(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a shrine sync."""
    background_tasks.add_task(run_shrine_sync, db)
    return {"message": "Shrine sync triggered"}


@router.post("/admin/sync/nightlight")
async def trigger_nightlight_sync(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a full Nightlight sync."""
    background_tasks.add_task(run_full_nightlight_sync, db)
    return {"message": "Nightlight sync triggered"}
