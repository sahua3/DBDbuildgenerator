from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.db.session import get_db
from app.db.cache import cache_get, cache_set
from app.models.perk import Perk
from app.schemas.schemas import PerkResponse, PerkStatsResponse
from app.core.config import PERK_CATEGORIES, CATEGORY_DISPLAY
import json

router = APIRouter(prefix="/perks", tags=["Perks"])


@router.get("/", response_model=list[PerkResponse])
async def list_perks(
    category: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    in_shrine: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Perk)

    if category:
        stmt = stmt.where(Perk.categories.any(category))
    if owner:
        stmt = stmt.where(Perk.owner == owner)
    if in_shrine is not None:
        stmt = stmt.where(Perk.in_shrine == in_shrine)
    if search:
        stmt = stmt.where(Perk.name.ilike(f"%{search}%"))

    stmt = stmt.order_by(Perk.nightlight_rank.asc().nullslast(), Perk.name.asc())

    result = await db.execute(stmt)
    perks = result.scalars().all()
    return perks


@router.get("/categories")
async def list_categories():
    return [
        {"id": cat, "label": CATEGORY_DISPLAY[cat]}
        for cat in PERK_CATEGORIES
    ]


@router.get("/stats", response_model=PerkStatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    cached = await cache_get("perk:stats")
    if cached:
        return cached

    total = (await db.execute(select(func.count(Perk.id)))).scalar()

    from app.models.shrine import Shrine
    latest_shrine = (
        await db.execute(select(Shrine).order_by(Shrine.scraped_at.desc()).limit(1))
    ).scalar_one_or_none()

    category_counts = {}
    for cat in PERK_CATEGORIES:
        count = (
            await db.execute(
                select(func.count(Perk.id)).where(Perk.categories.any(cat))
            )
        ).scalar()
        category_counts[cat] = count

    categorized = (
        await db.execute(
            select(func.count(Perk.id)).where(func.array_length(Perk.categories, 1) > 0)
        )
    ).scalar()

    result = {
        "total_perks": total,
        "categorized_perks": categorized,
        "categories": category_counts,
        "last_nightlight_sync": None,
        "shrine_perks": latest_shrine.perk_names if latest_shrine else [],
    }

    await cache_set("perk:stats", result, ttl=300)
    return result


@router.get("/{perk_id}", response_model=PerkResponse)
async def get_perk(perk_id: str, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    import uuid
    perk = (
        await db.execute(select(Perk).where(Perk.id == uuid.UUID(perk_id)))
    ).scalar_one_or_none()
    if not perk:
        raise HTTPException(status_code=404, detail="Perk not found")
    return perk
