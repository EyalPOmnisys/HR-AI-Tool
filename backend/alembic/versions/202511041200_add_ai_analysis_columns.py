"""add AI analysis columns to jobs

Revision ID: 202511041200
Revises:
Create Date: 2025-11-04 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202511041200"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("jobs", sa.Column("analysis_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("jobs", sa.Column("analysis_model", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("analysis_version", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("ai_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("ai_finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("ai_error", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("jobs", "ai_error")
    op.drop_column("jobs", "ai_finished_at")
    op.drop_column("jobs", "ai_started_at")
    op.drop_column("jobs", "analysis_version")
    op.drop_column("jobs", "analysis_model")
    op.drop_column("jobs", "analysis_json")
