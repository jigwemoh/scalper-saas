import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Integer, Numeric, ForeignKey, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mt5_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # daily_stop | weekly_stop | drawdown_pause | consecutive_loss | manual_pause
    description: Mapped[str | None] = mapped_column(Text)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account = relationship("MT5Account", back_populates="risk_events")


class DailyPerformance(Base):
    __tablename__ = "daily_performance"
    __table_args__ = (UniqueConstraint("account_id", "date", name="uq_account_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mt5_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    starting_balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    ending_balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    daily_return_percent: Mapped[float] = mapped_column(Numeric(6, 3), default=0.0)
    max_drawdown_percent: Mapped[float] = mapped_column(Numeric(6, 3), default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)

    account = relationship("MT5Account", back_populates="daily_performance")
