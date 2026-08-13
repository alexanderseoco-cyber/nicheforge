"""Add customer metadata and durable batch policy state."""
from alembic import op
import sqlalchemy as sa
revision = "c6batchcurrency"
down_revision = "c5keywordorchestration"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("provider_customer_metadata", sa.Column("id", sa.String(), primary_key=True), sa.Column("provider", sa.String(80), nullable=False), sa.Column("customer_id", sa.String(40), nullable=False), sa.Column("currency_code", sa.String(3)), sa.Column("time_zone", sa.String(80)), sa.Column("fetched_at", sa.DateTime(), nullable=False), sa.Column("fresh_until", sa.DateTime()), sa.Column("provenance", sa.JSON(), nullable=False), sa.UniqueConstraint("provider", "customer_id", name="uq_provider_customer_metadata"))
    op.add_column("keyword_metric_batch_items", sa.Column("policy_status", sa.String(60)))
    op.add_column("keyword_metric_batch_items", sa.Column("policy_minimum_sv", sa.Integer()))
    op.add_column("keyword_metric_batch_items", sa.Column("policy_snapshot", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("keyword_metric_batch_items", sa.Column("evaluated_at", sa.DateTime()))
def downgrade():
    for name in ("evaluated_at", "policy_snapshot", "policy_minimum_sv", "policy_status"): op.drop_column("keyword_metric_batch_items", name)
    op.drop_table("provider_customer_metadata")
