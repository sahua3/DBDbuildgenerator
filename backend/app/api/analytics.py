from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.db.cache import cache_get, cache_set
from app.models.feedback import BuildEvent, PerkAffinityScore
from app.models.perk import Perk
from app.services.feedback import record_event, get_similar_perks
from app.services.evaluator import run_evaluation
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class FeedbackRequest(BaseModel):
    perk_ids: list[str]
    event_type: str           # "saved" | "rerolled" | "ignored"
    generation_mode: Optional[str] = None
    theme: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a user interaction with a build."""
    await record_event(
        db=db,
        perk_ids=request.perk_ids,
        event_type=request.event_type,
        generation_mode=request.generation_mode,
        theme=request.theme,
    )
    await db.commit()
    return {"recorded": True}


@router.get("/similar/{perk_id}")
async def get_similar(
    perk_id: str,
    top_n: int = Query(default=8, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    'Users who save builds with this perk also tend to use these perks.'
    Returns top-N perks by co-occurrence in saved builds.
    """
    cache_key = f"similar:{perk_id}:{top_n}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    similar_raw = await get_similar_perks(db, perk_id, top_n)

    # Hydrate with perk names
    result = []
    for item in similar_raw:
        perk = (await db.execute(
            select(Perk).where(Perk.id == uuid.UUID(item["perk_id"]))
        )).scalar_one_or_none()
        if perk:
            result.append({
                "perk_id": item["perk_id"],
                "perk_name": perk.name,
                "owner": perk.owner,
                "categories": perk.categories,
                "affinity_score": round(item["affinity_score"], 3),
                "save_count": item["save_count"],
            })

    await cache_set(cache_key, result, ttl=300)
    return result


@router.get("/evaluation")
async def get_evaluation(
    n_builds: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Run a comparative evaluation of all recommendation strategies.
    Returns scores for: random baseline, weighted rules, graph-enhanced, user feedback.
    """
    cache_key = f"eval:{n_builds}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    report = await run_evaluation(db, n_builds=n_builds)
    await cache_set(cache_key, report, ttl=600)
    return report


@router.get("/stats")
async def get_feedback_stats(db: AsyncSession = Depends(get_db)):
    """Summary of feedback data collected so far."""
    cached = await cache_get("feedback:stats")
    if cached:
        return cached

    total_events = (await db.execute(select(func.count(BuildEvent.id)))).scalar()
    by_type = (await db.execute(
        select(BuildEvent.event_type, func.count(BuildEvent.id))
        .group_by(BuildEvent.event_type)
    )).all()
    affinity_pairs = (await db.execute(select(func.count(PerkAffinityScore.id)))).scalar()

    # Top 5 most saved perk combos
    top_saves = (await db.execute(
        select(BuildEvent.perk_ids_key, func.count(BuildEvent.id).label("count"))
        .where(BuildEvent.event_type == "saved")
        .group_by(BuildEvent.perk_ids_key)
        .order_by(func.count(BuildEvent.id).desc())
        .limit(5)
    )).all()

    result = {
        "total_events": total_events,
        "by_type": {row[0]: row[1] for row in by_type},
        "affinity_pairs_computed": affinity_pairs,
        "top_saved_combos": [{"key": r[0], "count": r[1]} for r in top_saves],
    }
    await cache_set("feedback:stats", result, ttl=60)
    return result
