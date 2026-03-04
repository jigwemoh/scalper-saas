import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class AISignal(Base):
    __tablename__ = "ai_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY | SELL
    probability: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    expected_move_pips: Mapped[float | None] = mapped_column(Numeric(6, 2))
    regime: Mapped[str | None] = mapped_column(String(50))   # trending | ranging | volatile
    spread: Mapped[float | None] = mapped_column(Numeric(6, 2))
    atr: Mapped[float | None] = mapped_column(Numeric(6, 5))
    session: Mapped[str | None] = mapped_column(String(50))  # london | new_york | asia
    entry_price: Mapped[float | None] = mapped_column(Numeric(12, 6))
    stop_loss: Mapped[float | None] = mapped_column(Numeric(12, 6))
    take_profit: Mapped[float | None] = mapped_column(Numeric(12, 6))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    trades = relationship("Trade", back_populates="signal")
