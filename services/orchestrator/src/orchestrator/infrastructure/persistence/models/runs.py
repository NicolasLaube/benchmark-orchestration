from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from orchestrator.infrastructure.persistence.models.base import Base
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from orchestrator.infrastructure.persistence.models.report import RunReportModel


class RunModel(Base):
    __tablename__ = "runs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    completed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    report: Mapped["RunReportModel | None"] = relationship(
        back_populates="run",
        uselist=False,
        cascade="all, delete-orphan",
    )
