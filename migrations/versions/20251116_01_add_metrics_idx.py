"""add composite index metrics(miner_ip, timestamp)

Revision ID: 20251116_01
Revises: add_firmware_version
Create Date: 2025-11-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251116_01'
down_revision = 'add_firmware_version'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite supports CREATE INDEX IF NOT EXISTS from 3.8.0+
    try:
        op.execute("CREATE INDEX IF NOT EXISTS idx_metrics_miner_ip_timestamp ON metrics (miner_ip, timestamp)")
    except Exception:
        # Fallback: try to create via SQLAlchemy if needed
        try:
            op.create_index('idx_metrics_miner_ip_timestamp', 'metrics', ['miner_ip', 'timestamp'], unique=False)
        except Exception:
            pass


def downgrade() -> None:
    try:
        op.drop_index('idx_metrics_miner_ip_timestamp', table_name='metrics')
    except Exception:
        # Some SQLite versions may not support drop_index through Alembic
        pass
