import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class MT5Account(Base):
    __tablename__ = "mt5_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    broker_name: Mapped[str | None] = mapped_column(String(255))
    account_number: Mapped[str | None] = mapped_column(String(100))
    server_name: Mapped[str | None] = mapped_column(String(255))
    leverage: Mapped[int | None] = mapped_column(Integer)
    account_balance: Mapped[float | None] = mapped_column(Numeric(12, 2))
    account_equity: Mapped[float | None] = mapped_column(Numeric(12, 2))
    risk_profile: Mapped[str] = mapped_column(String(50), default="balanced")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="mt5_accounts")
    trades = relationship("Trade", back_populates="account", cascade="all, delete-orphan")
    risk_events = relationship("RiskEvent", back_populates="account", cascade="all, delete-orphan")
    daily_performance = relationship("DailyPerformance", back_populates="account", cascade="all, delete-orphan")
