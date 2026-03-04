import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mt5_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_signals.id", ondelete="SET NULL"), nullable=True
    )
    mt5_ticket: Mapped[int | None] = mapped_column()  # MT5 order ticket
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY | SELL
    lot_size: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Numeric(12, 6))
    stop_loss: Mapped[float | None] = mapped_column(Numeric(12, 6))
    take_profit: Mapped[float | None] = mapped_column(Numeric(12, 6))
    exit_price: Mapped[float | None] = mapped_column(Numeric(12, 6))
    profit_loss: Mapped[float | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)  # open | closed | cancelled
    close_reason: Mapped[str | None] = mapped_column(String(30))  # take_profit | stop_loss | manual | kill_switch | expired
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account = relationship("MT5Account", back_populates="trades")
    signal = relationship("AISignal", back_populates="trades")
