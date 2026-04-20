from sqlalchemy import Column, String, Text, ARRAY, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
import uuid


class SavedBuild(Base):
    __tablename__ = "saved_builds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    perk_ids = Column(ARRAY(String), nullable=False)  # list of perk UUIDs as strings
    theme = Column(String(300), nullable=True)
    ai_explanation = Column(Text, nullable=True)
    generation_mode = Column(String(50), default="theme")  # "theme" or "category"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
