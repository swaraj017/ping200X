
from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    DateTime,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))


class MonitorCheck(Base):
    # Stores the result of each health check.
    __tablename__ = "monitor_checks"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Links the check result to its monitor.
    monitor_id: Mapped[int] = mapped_column(
        ForeignKey("monitors.id", ondelete="CASCADE"),
        index=True,
    )

    # Whether the monitored website was reachable.
    status: Mapped[str] = mapped_column(String(10))

    # HTTP status code, or None if no response was received.
    status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # How long the HTTP request took, in milliseconds.
    response_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Details of timeouts, DNS failures, or connection errors.
    error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # PostgreSQL sets this timestamp when the row is inserted.
    checked_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )