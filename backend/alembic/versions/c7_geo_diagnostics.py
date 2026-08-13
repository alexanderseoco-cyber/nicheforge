"""Persist safe geo resolver diagnostics on batch items."""
from alembic import op
import sqlalchemy as sa

revision = "c7geodiagnostics"
down_revision = "c6batchcurrency"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("keyword_metric_batch_items", sa.Column("geo_diagnostic", sa.JSON(), nullable=True))

def downgrade():
    op.drop_column("keyword_metric_batch_items", "geo_diagnostic")
