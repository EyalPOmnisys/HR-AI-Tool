"""drop RAG vector tables and columns

The matching engine scores all candidates deterministically (ensemble + LLM judge)
and no code reads the chunk tables or the document-level embedding columns anymore.
This migration removes them. The pgvector extension itself is kept installed.

WARNING: upgrade() is destructive - all stored chunks and embeddings are deleted.
downgrade() restores the schema (768-dim vectors) but NOT the data; embeddings
would need to be recomputed.

Revision ID: f4b7d0c8e21a
Revises: 095316958b8a
Create Date: 2026-07-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "f4b7d0c8e21a"
down_revision = "095316958b8a"
branch_labels = None
depends_on = None

EMBED_DIM = 768


def upgrade() -> None:
    # --- Drop vector/btree indexes first (names accumulated across past migrations) ---
    op.execute("DROP INDEX IF EXISTS ix_resume_embeddings_embedding_l2;")
    op.execute("DROP INDEX IF EXISTS ix_resumes_embedding_l2;")
    op.execute("DROP INDEX IF EXISTS idx_resume_emb_ivf;")
    op.execute("DROP INDEX IF EXISTS idx_job_emb_ivf;")
    op.execute("DROP INDEX IF EXISTS idx_jobs_doc_ivf;")
    op.execute("DROP INDEX IF EXISTS idx_resumes_doc_ivf;")
    op.execute("DROP INDEX IF EXISTS idx_resume_chunks_resume_id;")
    op.execute("DROP INDEX IF EXISTS idx_resume_chunks_section;")
    op.execute("DROP INDEX IF EXISTS idx_job_chunks_job_id;")
    op.execute("DROP INDEX IF EXISTS idx_job_chunks_section;")

    # --- Drop chunk/embedding tables (children before parents) ---
    op.execute("DROP TABLE IF EXISTS resume_embeddings CASCADE;")
    op.execute("DROP TABLE IF EXISTS resume_chunks CASCADE;")
    op.execute("DROP TABLE IF EXISTS job_embeddings CASCADE;")
    op.execute("DROP TABLE IF EXISTS job_chunks CASCADE;")

    # --- Drop document-level embedding columns ---
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS embedding;")
    op.execute("ALTER TABLE resumes DROP COLUMN IF EXISTS embedding;")

    # NOTE: the vector extension is intentionally NOT dropped.


def downgrade() -> None:
    # Restores schema only - embeddings must be recomputed by re-running ingestion.
    op.add_column("jobs", sa.Column("embedding", Vector(EMBED_DIM), nullable=True))
    op.add_column("resumes", sa.Column("embedding", Vector(EMBED_DIM), nullable=True))

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
        sa.Column("embedding", Vector(EMBED_DIM), nullable=True),
        sa.Column("embedding_model", sa.String(64), nullable=True),
        sa.Column("embedding_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["resume_chunks.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "job_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section", sa.String(64), nullable=True),
        sa.Column("ord", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("lang", sa.String(8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_job_chunks_job_id", "job_chunks", ["job_id"])
    op.create_index("ix_job_chunks_job_section_ord", "job_chunks", ["job_id", "section", "ord"])

    op.create_table(
        "job_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_chunks.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("embedding", Vector(EMBED_DIM), nullable=True),
        sa.Column("embedding_model", sa.String(64), nullable=True),
        sa.Column("embedding_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ANN indexes (as created by 0f6a5c2169b1, adjusted to 768 dims)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_resume_emb_ivf
        ON resume_embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 200);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_job_emb_ivf
        ON job_embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 200);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_doc_ivf
        ON jobs USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_resumes_doc_ivf
        ON resumes USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)
