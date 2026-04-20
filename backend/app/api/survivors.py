from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.survivor import Survivor
from app.schemas.schemas import SurvivorResponse, SurvivorOwnershipUpdate
import uuid

router = APIRouter(prefix="/survivors", tags=["Survivors"])


@router.get("/", response_model=list[SurvivorResponse])
async def list_survivors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Survivor).order_by(Survivor.name.asc()))
    return result.scalars().all()


@router.patch("/{survivor_id}/owned", response_model=SurvivorResponse)
async def update_ownership(
    survivor_id: str,
    body: SurvivorOwnershipUpdate,
    db: AsyncSession = Depends(get_db),
):
    survivor = (
        await db.execute(select(Survivor).where(Survivor.id == uuid.UUID(survivor_id)))
    ).scalar_one_or_none()
    if not survivor:
        raise HTTPException(status_code=404, detail="Survivor not found")
    survivor.owned = body.owned
    await db.commit()
    return survivor


@router.get("/owned", response_model=list[str])
async def get_owned_survivor_names(db: AsyncSession = Depends(get_db)):
    """Returns just the names of owned survivors (for use in build filters)."""
    result = await db.execute(
        select(Survivor.name).where(Survivor.owned == True)  # noqa
    )
    return [row[0] for row in result.all()]
