from sqlalchemy import Column, String, ARRAY, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
import uuid


class Shrine(Base):
    __tablename__ = "shrine_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    perk_names = Column(ARRAY(String), nullable=False)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)
