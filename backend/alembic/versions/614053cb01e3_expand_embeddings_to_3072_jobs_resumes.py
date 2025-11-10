# Alembic revision identifiers
revision = "614053cb01e3"
down_revision = "22bf04a5c7c2"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def _ensure_pgvector():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def _drop_ivfflat_indexes(table: str, column: str):
    """
    Drop IVFFLAT indexes on a specific table+column using pg catalogs
    (no fragile LIKE patterns, works across schemas in search_path).
    """
    conn = op.get_bind()
    rows = conn.exec_driver_sql(
        """
        SELECT i.relname AS index_name
        FROM pg_index x
        JOIN pg_class i ON i.oid = x.indexrelid         -- index rel
        JOIN pg_class t ON t.oid = x.indrelid           -- table rel
        JOIN pg_namespace ns ON ns.oid = t.relnamespace
        JOIN pg_am am ON am.oid = i.relam                -- access method
        JOIN pg_attribute a ON a.attrelid = t.oid
                          AND a.attnum = ANY (x.indkey)  -- indexed columns
        WHERE am.amname = 'ivfflat'
          AND t.relname = %(table)s
          AND a.attname = %(column)s
          AND ns.nspname = ANY (current_schemas(true))
        GROUP BY i.relname
        """,
        {"table": table, "column": column},
    ).fetchall()

    for (idxname,) in rows:
        op.execute(f'DROP INDEX IF EXISTS "{idxname}";')


def _bump_vector_dim(table: str, column: str, new_dim: int, not_null: bool | None):
    # 1) אם העמודה NOT NULL, נשחרר זמנית
    if not_null is True:
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN {column} DROP NOT NULL;')

    # 2) לרוקן ערכים קיימים כדי למנוע בעיות מימד
    op.execute(f'UPDATE "{table}" SET {column} = NULL;')

    # 2.5) להסיר אינדקסי IVFFLAT שחוסמים מימד > 2000
    _drop_ivfflat_indexes(table, column)

    # 3) לשנות את הטיפוס
    op.execute(f'ALTER TABLE "{table}" ALTER COLUMN {column} TYPE vector({new_dim});')

    # 4) לשחזר NOT NULL אם נדרש
    if not_null is True:
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN {column} SET NOT NULL;')


def upgrade() -> None:
    _ensure_pgvector()
    new_dim = 3072

    _bump_vector_dim(table="resumes", column="embedding", new_dim=new_dim, not_null=True)
    _bump_vector_dim(table="resume_embeddings", column="embedding", new_dim=new_dim, not_null=False)
    _bump_vector_dim(table="jobs", column="embedding", new_dim=new_dim, not_null=False)


def downgrade() -> None:
    _ensure_pgvector()
    old_dim = 768

    _bump_vector_dim(table="resumes", column="embedding", new_dim=old_dim, not_null=True)
    _bump_vector_dim(table="resume_embeddings", column="embedding", new_dim=old_dim, not_null=False)
    _bump_vector_dim(table="jobs", column="embedding", new_dim=old_dim, not_null=False)
