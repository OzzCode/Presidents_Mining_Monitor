"""Add firmware_version to Miner

Revision ID: add_firmware_version
Revises: 
Create Date: 2025-10-21 16:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_firmware_version'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add the firmware_version column to the miners table
    op.add_column('miners', sa.Column('firmware_version', sa.String(50), nullable=True))
    
    # For existing records, try to extract firmware version from model name
    conn = op.get_bind()
    miners = conn.execute("SELECT id, model FROM miners WHERE model LIKE '%(%'")
    
    for miner_id, model in miners:
        # Extract firmware version from model name (e.g., "Antminer S19 Pro (Vnish 1.2.6)")
        import re
        match = re.search(r'\((.+?)\)', model)
        if match:
            firmware = match.group(1).strip()
            # Update the firmware_version column
            conn.execute(
                "UPDATE miners SET firmware_version = %s, model = %s WHERE id = %s",
                (firmware, re.sub(r'\s*\(.+\)', '', model).strip(), miner_id)
            )

def downgrade():
    # Before dropping the column, move firmware version back to model name
    conn = op.get_bind()
    miners = conn.execute("SELECT id, model, firmware_version FROM miners WHERE firmware_version IS NOT NULL")
    
    for miner_id, model, firmware in miners:
        # Append firmware version to model name
        conn.execute(
            "UPDATE miners SET model = %s WHERE id = %s",
            (f"{model} ({firmware})", miner_id)
        )
    
    # Now drop the column
    op.drop_column('miners', 'firmware_version')
