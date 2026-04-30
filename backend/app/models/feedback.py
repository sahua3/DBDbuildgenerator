from sqlalchemy import Column, String, Float, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
import uuid


class BuildEvent(Base):
    """
    Records every user interaction with a generated build.
    This is the raw signal for the feedback loop.
    """
    __tablename__ = "build_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # The 4 perk IDs in this build (stored as sorted CSV for easy grouping)
    perk_ids_key = Column(String(200), nullable=False, index=True)

    # Individual perk IDs
    perk_a = Column(String(36), nullable=False, index=True)
    perk_b = Column(String(36), nullable=False, index=True)
    perk_c = Column(String(36), nullable=False, index=True)
    perk_d = Column(String(36), nullable=False, index=True)

    # Event type: "generated", "saved", "rerolled", "ignored"
    # saved   = strong positive (+1.0)
    # rerolled = negative       (-0.5)
    # ignored  = weak negative  (-0.1)  (generated but never saved or rerolled)
    event_type = Column(String(20), nullable=False)

    # Generation mode: theme / category / random
    generation_mode = Column(String(20), nullable=True)

    # Theme string if theme mode
    theme = Column(String(300), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PerkAffinityScore(Base):
    """
    Precomputed user-behavior affinity between two perks.
    Separate from PerkEdge (which is Nightlight co-occurrence).
    Combined at query time: final_weight = nightlight_weight * α + affinity_weight * β
    """
    __tablename__ = "perk_affinity_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    perk_a_id = Column(String(36), nullable=False, index=True)
    perk_b_id = Column(String(36), nullable=False, index=True)

    # Raw co-occurrence count in saved builds
    save_cooccurrence = Column(Integer, default=0)
    # Raw co-occurrence count in rerolled builds
    reroll_cooccurrence = Column(Integer, default=0)

    # Final normalized affinity score (0.0 - 1.0)
    # Higher = users who save builds tend to have these two together
    affinity_score = Column(Float, default=0.0)

    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    from sqlalchemy import UniqueConstraint
    __table_args__ = (
        UniqueConstraint("perk_a_id", "perk_b_id", name="unique_affinity_pair"),
    )
