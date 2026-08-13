"""Add persistent geo mappings and resumable keyword metric batch items."""
from alembic import op
import sqlalchemy as sa

revision = "c5keywordorchestration"
down_revision = "c4keywordcurrency"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("provider_geo_mappings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("city", sa.String(120), nullable=False), sa.Column("state_code", sa.String(8), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False), sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("criterion_id", sa.String(80), nullable=False), sa.Column("resource_name", sa.String(200), nullable=False),
        sa.Column("provider_name", sa.String(240)), sa.Column("canonical_name", sa.String(400)),
        sa.Column("target_type", sa.String(40)), sa.Column("provider_status", sa.String(40)),
        sa.Column("mapping_status", sa.String(40), nullable=False), sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("fresh_until", sa.DateTime()), sa.Column("provenance", sa.JSON(), nullable=False),
        sa.UniqueConstraint("city", "state_code", "country_code", "provider", name="uq_provider_geo_identity"))
    op.create_index("ix_provider_geo_mappings_city", "provider_geo_mappings", ["city"])
    op.create_index("ix_provider_geo_mappings_state_code", "provider_geo_mappings", ["state_code"])
    op.create_table("keyword_metric_batch_items",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("batch_id", sa.String(), sa.ForeignKey("keyword_metric_batches.id"), nullable=False),
        sa.Column("keyword", sa.String(400), nullable=False), sa.Column("city", sa.String(120), nullable=False),
        sa.Column("state_code", sa.String(8), nullable=False), sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("location_identity", sa.String(300), nullable=False), sa.Column("status", sa.String(40), nullable=False),
        sa.Column("geo_mapping_id", sa.String(), sa.ForeignKey("provider_geo_mappings.id")), sa.Column("evidence_id", sa.String(), sa.ForeignKey("keyword_metric_evidence.id")),
        sa.Column("error_code", sa.String(80)), sa.Column("error_message", sa.String(500)), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("batch_id", "keyword", "location_identity", name="uq_keyword_metric_batch_item"))
    op.create_index("ix_keyword_metric_batch_items_batch_id", "keyword_metric_batch_items", ["batch_id"])

def downgrade():
    op.drop_table("keyword_metric_batch_items")
    op.drop_table("provider_geo_mappings")
