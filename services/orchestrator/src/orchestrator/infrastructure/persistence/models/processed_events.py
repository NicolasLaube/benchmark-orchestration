from datetime import datetime

from orchestrator.infrastructure.persistence.models.base import Base
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class ProcessedEventModel(Base):
    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
