"""persist SERP coverage policy"""
from alembic import op
import sqlalchemy as sa

revision = "f9serpcoveragepolicy"
down_revision = "f8recalculationlineage"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("runs") as batch:
        batch.add_column(sa.Column("minimum_organic_rows", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("minimum_organic_coverage", sa.Float(), nullable=True))

def downgrade():
    with op.batch_alter_table("runs") as batch:
        batch.drop_column("minimum_organic_coverage")
        batch.drop_column("minimum_organic_rows")
