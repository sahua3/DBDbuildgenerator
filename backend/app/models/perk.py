from sqlalchemy import Column, String, Float, Text, ARRAY, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID


class Perk(Base):
    __tablename__ = "perks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    owner = Column(String(100), nullable=True)  # survivor name or None for base perks

    # Categories — a perk can belong to multiple categories
    categories = Column(ARRAY(String), nullable=False, default=[])

    # Popularity weight from Nightlight (0.0 - 1.0)
    pick_rate = Column(Float, default=0.0)
    # Normalized weight within its category (0.0 - 1.0)
    category_weight = Column(Float, default=0.0)

    # Whether this perk is currently in the Shrine of Secrets
    in_shrine = Column(Boolean, default=False)

    # Perk icon URL (scraped from nightlight or static)
    icon_url = Column(String(500), nullable=True)

    # Raw Nightlight rank (lower = more popular)
    nightlight_rank = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Perk {self.name}>"
