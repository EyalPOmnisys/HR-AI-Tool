"""merge heads: resumes + jobs chunks

Revision ID: 9c8d6928f5e2
Revises: 4ac46007d4f3, d3fa49a801ac
Create Date: 2025-11-10 16:26:06.931323

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c8d6928f5e2'
down_revision = ('4ac46007d4f3', 'd3fa49a801ac')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
