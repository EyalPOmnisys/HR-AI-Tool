"""jobs: chunks + embeddings + helper fields"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector  # keep for schema clarity

# ---------------------------
# Alembic revision identifiers
# ---------------------------
revision = "d3fa49a801ac"
down_revision = "614053cb01e3"
branch_labels = None
depends_on = None

EMBED_DIM = 3072


def upgrade():
    # Ensure required extensions exist (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # --- Add helper columns to jobs ---
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("normalized_text", sa.Text(), nullable=True))
        batch.add_column(sa.Column("lang", sa.String(length=8), nullable=True))
        batch.add_column(sa.Column("tokens", sa.Integer(), nullable=True))
        # If your jobs.embedding column is missing or wrong dim, uncomment:
        # batch.add_column(sa.Column("embedding", Vector(EMBED_DIM), nullable=True))

    # --- job_chunks table ---
    op.create_table(
        "job_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section", sa.String(length=64), nullable=True),
        sa.Column("ord", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("lang", sa.String(length=8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_job_chunks_job_id", "job_chunks", ["job_id"])
    op.create_index(
        "ix_job_chunks_job_section_ord", "job_chunks", ["job_id", "section", "ord"]
    )

    # --- job_embeddings table (1:1 with chunk) ---
    op.create_table(
        "job_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_chunks.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("embedding", Vector(EMBED_DIM), nullable=True),
        sa.Column("embedding_model", sa.String(length=64), nullable=True),
        sa.Column("embedding_version", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # NOTE: Skipping ANN indexes (IVFFLAT/HNSW) because pgvector limits them to <= 2000 dimensions.
    # Once you switch to 1536D (or halfvec on newer pgvector), add the indexes with:
    #   CREATE INDEX ... USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);


def downgrade():
    # Drop tables & indexes created above
    # (no ANN indexes were created)
    op.drop_table("job_embeddings")
    op.drop_index("ix_job_chunks_job_section_ord", table_name="job_chunks")
    op.drop_index("ix_job_chunks_job_id", table_name="job_chunks")
    op.drop_table("job_chunks")

    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("tokens")
        batch.drop_column("lang")
        batch.drop_column("normalized_text")
