"""add_match_scores_and_notes_to_job_candidates

Revision ID: 095316958b8a
Revises: 1b82b8dbfcff
Create Date: 2025-12-03 10:20:06.035239

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '095316958b8a'
down_revision = '1b82b8dbfcff'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('job_candidates', sa.Column('match_score', sa.Integer(), nullable=True))
    op.add_column('job_candidates', sa.Column('rag_score', sa.Integer(), nullable=True))
    op.add_column('job_candidates', sa.Column('llm_score', sa.Integer(), nullable=True))
    op.add_column('job_candidates', sa.Column('analysis_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('job_candidates', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('job_candidates', 'notes')
    op.drop_column('job_candidates', 'analysis_json')
    op.drop_column('job_candidates', 'llm_score')
    op.drop_column('job_candidates', 'rag_score')
    op.drop_column('job_candidates', 'match_score')