"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(50), server_default="user"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.Text, unique=True, nullable=False),
        sa.Column("name", sa.String(100)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_api_keys_user", "api_keys", ["user_id"])
    op.create_index("idx_api_keys_key", "api_keys", ["key"])

    # mt5_accounts
    op.create_table(
        "mt5_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("broker_name", sa.String(255)),
        sa.Column("account_number", sa.String(100)),
        sa.Column("server_name", sa.String(255)),
        sa.Column("leverage", sa.Integer),
        sa.Column("account_balance", sa.Numeric(12, 2)),
        sa.Column("account_equity", sa.Numeric(12, 2)),
        sa.Column("risk_profile", sa.String(50), server_default="balanced"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_mt5_user", "mt5_accounts", ["user_id"])

    # ai_signals
    op.create_table(
        "ai_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("probability", sa.Numeric(5, 4), nullable=False),
        sa.Column("expected_move_pips", sa.Numeric(6, 2)),
        sa.Column("regime", sa.String(50)),
        sa.Column("spread", sa.Numeric(6, 2)),
        sa.Column("atr", sa.Numeric(6, 5)),
        sa.Column("session", sa.String(50)),
        sa.Column("entry_price", sa.Numeric(12, 6)),
        sa.Column("stop_loss", sa.Numeric(12, 6)),
        sa.Column("take_profit", sa.Numeric(12, 6)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_signals_symbol", "ai_signals", ["symbol"])
    op.create_index("idx_signals_created", "ai_signals", ["created_at"])

    # trades
    op.create_table(
        "trades",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("mt5_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signal_id", UUID(as_uuid=True), sa.ForeignKey("ai_signals.id", ondelete="SET NULL")),
        sa.Column("mt5_ticket", sa.BigInteger),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("lot_size", sa.Numeric(10, 4), nullable=False),
        sa.Column("entry_price", sa.Numeric(12, 6)),
        sa.Column("stop_loss", sa.Numeric(12, 6)),
        sa.Column("take_profit", sa.Numeric(12, 6)),
        sa.Column("exit_price", sa.Numeric(12, 6)),
        sa.Column("profit_loss", sa.Numeric(12, 2)),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_trades_account", "trades", ["account_id"])
    op.create_index("idx_trades_opened", "trades", ["opened_at"])
    op.create_index("idx_trades_status", "trades", ["status"])

    # risk_events
    op.create_table(
        "risk_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("mt5_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_risk_account", "risk_events", ["account_id"])

    # daily_performance
    op.create_table(
        "daily_performance",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("mt5_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("starting_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("ending_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("daily_return_percent", sa.Numeric(6, 3), server_default="0"),
        sa.Column("max_drawdown_percent", sa.Numeric(6, 3), server_default="0"),
        sa.Column("total_trades", sa.Integer, server_default="0"),
    )
    op.create_index("idx_perf_account", "daily_performance", ["account_id"])
    op.create_unique_constraint("uq_account_date", "daily_performance", ["account_id", "date"])

    # subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_name", sa.String(100), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("billing_cycle", sa.String(20), server_default="monthly"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_subs_user", "subscriptions", ["user_id"])
    op.create_index("idx_subs_status", "subscriptions", ["status"])

    # payments
    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_provider", sa.String(50), server_default="paystack"),
        sa.Column("provider_transaction_id", sa.String(255), unique=True),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("plan_name", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_payments_user", "payments", ["user_id"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("subscriptions")
    op.drop_table("daily_performance")
    op.drop_table("risk_events")
    op.drop_table("trades")
    op.drop_table("ai_signals")
    op.drop_table("mt5_accounts")
    op.drop_table("api_keys")
    op.drop_table("users")
