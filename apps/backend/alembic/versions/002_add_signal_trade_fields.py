"""add close_reason to trades and sl_pips/liquidity_sweep/model_version to signals

Revision ID: 002
Revises: 001
Create Date: 2026-03-04
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # trades: add close_reason
    op.add_column("trades", sa.Column("close_reason", sa.String(30), nullable=True))

    # ai_signals: add sl_pips, liquidity_sweep, model_version
    op.add_column("ai_signals", sa.Column("sl_pips", sa.Numeric(8, 2), nullable=True))
    op.add_column("ai_signals", sa.Column("liquidity_sweep", sa.Boolean, server_default="false", nullable=False))
    op.add_column("ai_signals", sa.Column("model_version", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("trades", "close_reason")
    op.drop_column("ai_signals", "sl_pips")
    op.drop_column("ai_signals", "liquidity_sweep")
    op.drop_column("ai_signals", "model_version")
