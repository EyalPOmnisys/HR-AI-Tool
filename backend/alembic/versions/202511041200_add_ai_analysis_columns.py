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

def _has_table(bind, name: str) -> bool:
    insp = sa.inspect(bind)
    return insp.has_table(name)

def _has_col(bind, table: str, col: str) -> bool:
    insp = sa.inspect(bind)
    try:
        return any(c["name"] == col for c in insp.get_columns(table))
    except Exception:
        return False

def upgrade():
    bind = op.get_bind()

    if not _has_table(bind, "jobs"):
        op.create_table(
            "jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("job_description", sa.Text(), nullable=False),
            sa.Column("free_text", sa.Text(), nullable=True),
            sa.Column("icon", sa.String(64), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
            sa.Column("analysis_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("analysis_model", sa.String(64), nullable=True),
            sa.Column("analysis_version", sa.Integer(), nullable=True),
            sa.Column("ai_started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ai_finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ai_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_jobs_status", "jobs", ["status"])
        op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    else:
        with op.batch_alter_table("jobs") as batch:
            if not _has_col(bind, "jobs", "analysis_json"):
                batch.add_column(sa.Column("analysis_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
            if not _has_col(bind, "jobs", "analysis_model"):
                batch.add_column(sa.Column("analysis_model", sa.String(64), nullable=True))
            if not _has_col(bind, "jobs", "analysis_version"):
                batch.add_column(sa.Column("analysis_version", sa.Integer(), nullable=True))
            if not _has_col(bind, "jobs", "ai_started_at"):
                batch.add_column(sa.Column("ai_started_at", sa.DateTime(timezone=True), nullable=True))
            if not _has_col(bind, "jobs", "ai_finished_at"):
                batch.add_column(sa.Column("ai_finished_at", sa.DateTime(timezone=True), nullable=True))
            if not _has_col(bind, "jobs", "ai_error"):
                batch.add_column(sa.Column("ai_error", sa.Text(), nullable=True))

def downgrade():
    # שמירה על בטיחות: רק הסרה של העמודות שהוספנו
    with op.batch_alter_table("jobs") as batch:
        for col in ("ai_error","ai_finished_at","ai_started_at","analysis_version","analysis_model","analysis_json"):
            try:
                batch.drop_column(col)
            except Exception:
                pass
