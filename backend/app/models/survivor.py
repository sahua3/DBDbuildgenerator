from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
import uuid


class Survivor(Base):
    __tablename__ = "survivors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    is_base = Column(Boolean, default=False)  # Base game survivors (always unlocked)
    icon_url = Column(String(500), nullable=True)
    owned = Column(Boolean, default=False)  # User-set ownership flag
