"""Add versioned derived keyword commercial metrics."""
from alembic import op
import sqlalchemy as sa
revision = "c10derivedmetrics"
down_revision = "c9fxrateevidence"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("keyword_opportunity_metrics",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("keyword_metric_evidence_id", sa.String(), sa.ForeignKey("keyword_metric_evidence.id"), nullable=False),
        sa.Column("commercial_search_value", sa.Float()),
        sa.Column("projected_metrics", sa.JSON(), nullable=False),
        sa.Column("ctr_model_version", sa.String(40), nullable=False),
        sa.Column("calculation_version", sa.String(80), nullable=False),
        sa.Column("calculated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("keyword_metric_evidence_id", "ctr_model_version", "calculation_version", name="uq_keyword_opportunity_calculation"))
def downgrade():
    op.drop_table("keyword_opportunity_metrics")
