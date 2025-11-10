from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "4ac46007d4f3"
down_revision = "614053cb01e3"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE resumes ALTER COLUMN embedding TYPE vector(3072)")
    op.alter_column(
        "resumes",
        "embedding",
        existing_type=Vector(3072),
        nullable=True,          # הרפיית NOT NULL
        existing_nullable=False # היה NOT NULL קודם
    )

def downgrade():
    op.alter_column(
        "resumes",
        "embedding",
        existing_type=Vector(3072),
        nullable=False,
        existing_nullable=True
    )
