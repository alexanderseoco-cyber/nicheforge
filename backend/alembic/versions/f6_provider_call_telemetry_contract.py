"""add nullable observational provider-call telemetry fields"""

from alembic import op
import sqlalchemy as sa


revision = "f6providercalltelemetry"
down_revision = "f5runbacklinklineage"
branch_labels = None
depends_on = None


def upgrade():
    columns = [
        ("logical_item_count", sa.Integer()),
        ("unique_target_count", sa.Integer()),
        ("cache_hit_count", sa.Integer()),
        ("cache_miss_count", sa.Integer()),
        ("stale_count", sa.Integer()),
        ("cache_outcome", sa.String(length=40)),
        ("cache_provider_dimension", sa.String(length=80)),
        ("actual_evidence_provider", sa.String(length=80)),
        ("evidence_reused_count", sa.Integer()),
        ("evidence_created_count", sa.Integer()),
        ("evidence_partial_count", sa.Integer()),
        ("evidence_missing_count", sa.Integer()),
        ("provider_item_count", sa.Integer()),
        ("items_returned_count", sa.Integer()),
        ("items_failed_count", sa.Integer()),
        ("batch_id", sa.String(length=120)),
        ("batch_size", sa.Integer()),
        ("batch_count", sa.Integer()),
        ("http_request_count", sa.Integer()),
        ("retry_count", sa.Integer()),
        ("http_request_sent", sa.Boolean()),
        ("paid_attempt", sa.Boolean()),
        ("reuse_scope", sa.String(length=30)),
        ("cost_confidence", sa.String(length=20)),
        ("metadata_json", sa.JSON()),
    ]
    for name, column in columns:
        op.add_column("provider_calls", sa.Column(name, column, nullable=True))


def downgrade():
    columns = [
        "metadata_json", "cost_confidence", "reuse_scope", "paid_attempt",
        "http_request_sent", "retry_count", "http_request_count", "batch_count",
        "batch_size", "batch_id", "items_failed_count", "items_returned_count",
        "provider_item_count", "evidence_missing_count", "evidence_partial_count",
        "evidence_created_count", "evidence_reused_count", "actual_evidence_provider",
        "cache_provider_dimension", "cache_outcome", "stale_count", "cache_miss_count",
        "cache_hit_count", "unique_target_count", "logical_item_count",
    ]
    for name in columns:
        op.drop_column("provider_calls", name)
