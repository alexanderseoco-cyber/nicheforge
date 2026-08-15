"""Add actual keyword-provider chunk telemetry to ProviderCall."""
from alembic import op
import sqlalchemy as sa

revision = "c11providercalltelemetry"
down_revision = "c10derivedmetrics"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("provider_calls", sa.Column("customer_id", sa.String(80), nullable=True))
    op.add_column("provider_calls", sa.Column("target_identity", sa.String(240), nullable=True))
    op.add_column("provider_calls", sa.Column("geo_target_resource", sa.String(240), nullable=True))
    op.add_column("provider_calls", sa.Column("language_code", sa.String(40), nullable=True))
    op.add_column("provider_calls", sa.Column("chunk_index", sa.Integer(), nullable=True))
    op.add_column("provider_calls", sa.Column("chunk_count", sa.Integer(), nullable=True))
    op.add_column("provider_calls", sa.Column("submitted_keyword_count", sa.Integer(), nullable=True))
    op.add_column("provider_calls", sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("provider_calls", sa.Column("duration_ms", sa.Float(), nullable=True))
    op.add_column("provider_calls", sa.Column("provider_reached", sa.Boolean(), nullable=True))
    op.add_column("provider_calls", sa.Column("operation_count", sa.Integer(), nullable=True))
    op.create_index("ix_provider_calls_customer_id", "provider_calls", ["customer_id"])
    op.create_index("ix_provider_calls_target_identity", "provider_calls", ["target_identity"])


def downgrade():
    op.drop_index("ix_provider_calls_target_identity", table_name="provider_calls")
    op.drop_index("ix_provider_calls_customer_id", table_name="provider_calls")
    for name in (
        "operation_count", "provider_reached", "duration_ms", "attempt_number",
        "submitted_keyword_count", "chunk_count", "chunk_index",
        "language_code", "geo_target_resource", "target_identity", "customer_id",
    ):
        op.drop_column("provider_calls", name)
