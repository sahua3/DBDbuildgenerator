from sqlalchemy import Column, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
import uuid


class PerkEdge(Base):
    """
    Weighted graph edge: how often perk_a and perk_b appear together in top builds.
    Weight is normalized 0.0 - 1.0.
    """
    __tablename__ = "perk_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    perk_a_id = Column(UUID(as_uuid=True), ForeignKey("perks.id"), nullable=False)
    perk_b_id = Column(UUID(as_uuid=True), ForeignKey("perks.id"), nullable=False)
    weight = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("perk_a_id", "perk_b_id", name="unique_perk_pair"),
    )
