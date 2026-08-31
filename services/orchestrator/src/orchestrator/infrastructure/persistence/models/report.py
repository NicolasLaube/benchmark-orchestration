from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from orchestrator.infrastructure.persistence.models import Base
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from orchestrator.infrastructure.persistence.models.report import RunModel


class RunReportModel(Base):
    __tablename__ = "run_reports"

    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        primary_key=True,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    report: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    run: Mapped["RunModel"] = relationship(
        back_populates="report",
    )
