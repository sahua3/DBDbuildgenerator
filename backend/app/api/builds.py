from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.cache import cache_get, cache_set
from app.schemas.schemas import (
    ThemeBuildRequest,
    CategoryBuildRequest,
    BuildResponse,
    SaveBuildRequest,
    SavedBuildResponse,
)
from app.services.builder import generate_theme_build, generate_category_build
from app.services.explainer import generate_explanation
from app.models.build import SavedBuild
from app.models.perk import Perk
import hashlib
import json
import uuid

router = APIRouter(prefix="/builds", tags=["Builds"])


def _perk_to_dict(perk) -> dict:
    return {
        "id": str(perk.id),
        "name": perk.name,
        "description": perk.description,
        "owner": perk.owner,
        "categories": perk.categories or [],
        "pick_rate": perk.pick_rate,
        "category_weight": perk.category_weight,
        "in_shrine": perk.in_shrine,
        "icon_url": perk.icon_url,
        "nightlight_rank": perk.nightlight_rank,
    }


@router.post("/theme", response_model=BuildResponse)
async def generate_from_theme(
    request: ThemeBuildRequest,
    db: AsyncSession = Depends(get_db),
):
    # Cache key based on request params
    cache_key = f"build:theme:{hashlib.md5(json.dumps(request.dict(), sort_keys=True).encode()).hexdigest()}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    perks = await generate_theme_build(
        db=db,
        theme=request.theme,
        owned_only=request.owned_only,
        owned_survivors=request.owned_survivors if request.owned_survivors else None,
    )

    if len(perks) < 2:
        raise HTTPException(
            status_code=422,
            detail="Not enough perks found for this theme. Try disabling 'owned only' or expand your survivor roster.",
        )

    perk_dicts = [_perk_to_dict(p) for p in perks]
    explanation = await generate_explanation(perk_dicts, theme=request.theme, generation_mode="theme")

    result = {
        "perks": perk_dicts,
        "explanation": explanation,
        "theme": request.theme,
        "generation_mode": "theme",
    }

    await cache_set(cache_key, result, ttl=600)
    return result


@router.post("/category", response_model=BuildResponse)
async def generate_from_categories(
    request: CategoryBuildRequest,
    db: AsyncSession = Depends(get_db),
):
    if request.total_perks() != 4:
        raise HTTPException(
            status_code=422,
            detail=f"Category selections must total exactly 4 perks (got {request.total_perks()})",
        )

    cache_key = f"build:cat:{hashlib.md5(json.dumps(request.dict(), sort_keys=True).encode()).hexdigest()}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    perks = await generate_category_build(
        db=db,
        category_selections=request.category_selections,
        owned_only=request.owned_only,
        owned_survivors=request.owned_survivors if request.owned_survivors else None,
    )

    if len(perks) < 2:
        raise HTTPException(
            status_code=422,
            detail="Not enough perks found for these categories.",
        )

    perk_dicts = [_perk_to_dict(p) for p in perks]
    explanation = await generate_explanation(perk_dicts, generation_mode="category")

    result = {
        "perks": perk_dicts,
        "explanation": explanation,
        "theme": None,
        "generation_mode": "category",
    }

    await cache_set(cache_key, result, ttl=600)
    return result


@router.post("/random", response_model=BuildResponse)
async def generate_random_build(
    owned_only: bool = False,
    owned_survivors: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Pick 4 completely random perks — no AI explanation, instant response."""
    import random
    from sqlalchemy import func

    stmt = select(Perk).order_by(func.random()).limit(50)

    if owned_only and owned_survivors:
        names = [n.strip() for n in owned_survivors.split(",") if n.strip()]
        stmt = select(Perk).where(
            (Perk.owner == None) | (Perk.owner.in_(names))  # noqa
        ).order_by(func.random()).limit(50)

    candidates = (await db.execute(stmt)).scalars().all()

    if len(candidates) < 4:
        raise HTTPException(status_code=422, detail="Not enough perks in database.")

    picked = random.sample(list(candidates), 4)
    perk_dicts = [_perk_to_dict(p) for p in picked]

    return {
        "perks": perk_dicts,
        "explanation": "",
        "theme": None,
        "generation_mode": "random",
    }


@router.post("/save", response_model=SavedBuildResponse)
async def save_build(
    request: SaveBuildRequest,
    db: AsyncSession = Depends(get_db),
):
    # Fetch perks by ID to embed in response
    perk_objects = []
    for pid in request.perk_ids:
        perk = (
            await db.execute(select(Perk).where(Perk.id == uuid.UUID(pid)))
        ).scalar_one_or_none()
        if perk:
            perk_objects.append(perk)

    build = SavedBuild(
        name=request.name,
        perk_ids=request.perk_ids,
        theme=request.theme,
        ai_explanation=request.ai_explanation,
        generation_mode=request.generation_mode,
    )
    db.add(build)
    await db.commit()
    await db.refresh(build)

    return {
        "id": build.id,
        "name": build.name,
        "perks": [_perk_to_dict(p) for p in perk_objects],
        "theme": build.theme,
        "ai_explanation": build.ai_explanation,
        "generation_mode": build.generation_mode,
        "created_at": build.created_at,
    }


@router.get("/saved", response_model=list[SavedBuildResponse])
async def list_saved_builds(db: AsyncSession = Depends(get_db)):
    builds = (
        await db.execute(select(SavedBuild).order_by(SavedBuild.created_at.desc()).limit(50))
    ).scalars().all()

    results = []
    for build in builds:
        perk_objects = []
        for pid in (build.perk_ids or []):
            perk = (
                await db.execute(select(Perk).where(Perk.id == uuid.UUID(pid)))
            ).scalar_one_or_none()
            if perk:
                perk_objects.append(perk)
        results.append({
            "id": build.id,
            "name": build.name,
            "perks": [_perk_to_dict(p) for p in perk_objects],
            "theme": build.theme,
            "ai_explanation": build.ai_explanation,
            "generation_mode": build.generation_mode,
            "created_at": build.created_at,
        })
    return results


@router.delete("/saved/{build_id}")
async def delete_saved_build(build_id: str, db: AsyncSession = Depends(get_db)):
    build = (
        await db.execute(select(SavedBuild).where(SavedBuild.id == uuid.UUID(build_id)))
    ).scalar_one_or_none()
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    await db.delete(build)
    await db.commit()
    return {"deleted": True}
