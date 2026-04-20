from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


# ── Perk ─────────────────────────────────────────────────────────────────────

class PerkBase(BaseModel):
    name: str
    description: str
    owner: Optional[str] = None
    categories: list[str] = []
    pick_rate: float = 0.0
    category_weight: float = 0.0
    in_shrine: bool = False
    icon_url: Optional[str] = None
    nightlight_rank: Optional[int] = None


class PerkResponse(PerkBase):
    id: UUID

    class Config:
        from_attributes = True


# ── Survivor ──────────────────────────────────────────────────────────────────

class SurvivorResponse(BaseModel):
    id: UUID
    name: str
    is_base: bool
    icon_url: Optional[str]
    owned: bool

    class Config:
        from_attributes = True


class SurvivorOwnershipUpdate(BaseModel):
    owned: bool


# ── Build Generation ──────────────────────────────────────────────────────────

class ThemeBuildRequest(BaseModel):
    theme: str = Field(..., min_length=3, max_length=300)
    owned_only: bool = False
    owned_survivors: list[str] = []  # survivor names the user owns


class CategoryBuildRequest(BaseModel):
    category_selections: dict[str, int] = Field(
        ...,
        description="Map of category name → how many perks from that category (total must be 4)"
    )
    owned_only: bool = False
    owned_survivors: list[str] = []

    def total_perks(self) -> int:
        return sum(self.category_selections.values())


class BuildResponse(BaseModel):
    perks: list[PerkResponse]
    explanation: str
    theme: Optional[str] = None
    generation_mode: str


# ── Saved Build ───────────────────────────────────────────────────────────────

class SaveBuildRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    perk_ids: list[str]
    theme: Optional[str] = None
    ai_explanation: Optional[str] = None
    generation_mode: str = "theme"


class SavedBuildResponse(BaseModel):
    id: UUID
    name: str
    perks: list[PerkResponse]
    theme: Optional[str]
    ai_explanation: Optional[str]
    generation_mode: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Shrine ────────────────────────────────────────────────────────────────────

class ShrineResponse(BaseModel):
    perk_names: list[str]
    perks: list[PerkResponse]
    scraped_at: datetime
    valid_until: Optional[datetime]

    class Config:
        from_attributes = True


# ── Stats ─────────────────────────────────────────────────────────────────────

class PerkStatsResponse(BaseModel):
    total_perks: int
    categorized_perks: int
    categories: dict[str, int]
    last_nightlight_sync: Optional[datetime]
    shrine_perks: list[str]
