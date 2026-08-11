"""add backlink mapping observability fields"""
from alembic import op
import sqlalchemy as sa

revision = "a9proxymapping"
down_revision = "a8ahrefsproxy"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("proxy_backlink_feature_evidence", sa.Column("mapping_status", sa.String(40), nullable=True))
    op.add_column("proxy_backlink_feature_evidence", sa.Column("mapping_error", sa.String(1000), nullable=True))


def downgrade():
    op.drop_column("proxy_backlink_feature_evidence", "mapping_error")
    op.drop_column("proxy_backlink_feature_evidence", "mapping_status")
