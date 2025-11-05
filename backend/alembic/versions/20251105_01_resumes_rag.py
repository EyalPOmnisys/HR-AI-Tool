"""resumes + resume_chunks + resume_embeddings for RAG

Revision ID: 20251105_01_resumes_rag
Revises: 202511041200
Create Date: 2025-11-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "20251105_01_resumes_rag"
down_revision = "202511041200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ingested"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("parsed_text", sa.Text(), nullable=True),
        sa.Column("extraction_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_resumes_status", "resumes", ["status"])
    op.create_index("ix_resumes_created_at", "resumes", ["created_at"])

    op.create_table(
        "resume_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section", sa.String(64), nullable=True),
        sa.Column("ord", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_resume_chunks_resume_id", "resume_chunks", ["resume_id"])
    op.create_index("ix_resume_chunks_section", "resume_chunks", ["section"])
    op.create_index("ix_resume_chunks_ord", "resume_chunks", ["ord"])

    op.create_table(
        "resume_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("embedding_model", sa.String(64), nullable=True),
        sa.Column("embedding_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["resume_chunks.id"], ondelete="CASCADE"),
    )

    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_resume_embeddings_embedding_l2
    ON resume_embeddings
    USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_resumes_embedding_l2
    ON resumes
    USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS TRIGGER AS $$
    BEGIN
      NEW.updated_at = now();
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trg_resumes_updated_at
    BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_resumes_updated_at ON resumes;")
    op.execute("DROP FUNCTION IF EXISTS touch_updated_at;")
    op.drop_index("ix_resumes_embedding_l2", table_name="resumes")
    op.drop_index("ix_resume_embeddings_embedding_l2", table_name="resume_embeddings")
    op.drop_table("resume_embeddings")
    op.drop_index("ix_resume_chunks_ord", table_name="resume_chunks")
    op.drop_index("ix_resume_chunks_section", table_name="resume_chunks")
    op.drop_index("ix_resume_chunks_resume_id", table_name="resume_chunks")
    op.drop_table("resume_chunks")
    op.drop_index("ix_resumes_created_at", table_name="resumes")
    op.drop_index("ix_resumes_status", table_name="resumes")
    op.drop_table("resumes")
