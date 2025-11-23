"""shrink_embeddings_to_768

Revision ID: da8c1b3b2aed
Revises: 0f6a5c2169b1
Create Date: 2025-11-23 12:56:08.352277

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector 


# revision identifiers, used by Alembic.
revision = 'da8c1b3b2aed'
down_revision = '0f6a5c2169b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Jobs Table - Coarse embedding
    # אנחנו משתמשים ב-USING NULL כדי למחוק את הוקטורים הישנים כי הגודל לא תואם
    op.alter_column('jobs', 'embedding',
               existing_type=Vector(3072),
               type_=Vector(768),
               postgresql_using='NULL::vector(768)')

    # 2. Job Embeddings Table - Chunks
    op.alter_column('job_embeddings', 'embedding',
               existing_type=Vector(3072),
               type_=Vector(768),
               postgresql_using='NULL::vector(768)')

    # 3. Resumes Table
    op.alter_column('resumes', 'embedding',
               existing_type=Vector(3072),
               type_=Vector(768),
               postgresql_using='NULL::vector(768)')

    # 4. Resume Embeddings Table - Chunks
    op.alter_column('resume_embeddings', 'embedding',
               existing_type=Vector(3072),
               type_=Vector(768),
               postgresql_using='NULL::vector(768)')


def downgrade() -> None:
    op.alter_column('resume_embeddings', 'embedding',
               existing_type=Vector(768),
               type_=Vector(1536),
               postgresql_using='NULL::vector(3072)')

    op.alter_column('resumes', 'embedding',
               existing_type=Vector(768),
               type_=Vector(1536),
               postgresql_using='NULL::vector(3072)')

    op.alter_column('job_embeddings', 'embedding',
               existing_type=Vector(768),
               type_=Vector(1536),
               postgresql_using='NULL::vector(3072)')

    op.alter_column('jobs', 'embedding',
               existing_type=Vector(768),
               type_=Vector(1536),
               postgresql_using='NULL::vector(3072)')