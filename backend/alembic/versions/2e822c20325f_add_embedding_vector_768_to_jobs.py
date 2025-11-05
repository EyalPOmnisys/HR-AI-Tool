"""add embedding vector (768) to jobs"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  


# revision identifiers, used by Alembic.
revision = '2e822c20325f'
down_revision = '202511041200'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.add_column("jobs", sa.Column("embedding", Vector(768)))


def downgrade():
    op.drop_column("jobs", "embedding")
