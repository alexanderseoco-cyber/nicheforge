"""add isolated Ahrefs DR proxy evidence and calibration"""
from alembic import op
import sqlalchemy as sa

revision = "a8ahrefsproxy"
down_revision = "f1trialmode"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("runs", sa.Column("proxy_provider", sa.String(80), nullable=True))
    op.add_column("runs", sa.Column("proxy_metric", sa.String(80), nullable=True))
    op.add_column("runs", sa.Column("proxy_calibration_version", sa.String(80), nullable=True))
    op.add_column("runs", sa.Column("proxy_configuration_snapshot", sa.JSON(), nullable=True))
    op.add_column("run_candidates", sa.Column("proxy_classification", sa.String(40), nullable=True))
    op.add_column("run_candidates", sa.Column("proxy_result", sa.JSON(), nullable=True))
    op.create_table("proxy_authority_evidence",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("target_url", sa.String(2000), nullable=False),
        sa.Column("root_domain", sa.String(500), nullable=False), sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("metric", sa.String(80), nullable=False), sa.Column("domain_rating", sa.Float(), nullable=True),
        sa.Column("source_kind", sa.String(40), nullable=False), sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("request_metadata", sa.JSON(), nullable=True), sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("fresh_until", sa.DateTime(), nullable=True))
    op.create_index("ix_proxy_authority_evidence_root_domain", "proxy_authority_evidence", ["root_domain"])
    op.create_table("proxy_calibration_observations",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("normalized_domain", sa.String(500), nullable=False),
        sa.Column("ahrefs_dr", sa.Float(), nullable=True), sa.Column("moz_da", sa.Float(), nullable=True),
        sa.Column("provenance", sa.String(40), nullable=False), sa.Column("calibration_version", sa.String(80), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False), sa.Column("source_metadata", sa.JSON(), nullable=True))
    op.create_table("manual_moz_observations",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("normalized_domain", sa.String(500), nullable=False),
        sa.Column("moz_da", sa.Float(), nullable=True), sa.Column("moz_pa", sa.Float(), nullable=True),
        sa.Column("spam_score", sa.Float(), nullable=True), sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=True), sa.Column("observed_at", sa.DateTime(), nullable=False))


def downgrade():
    op.drop_table("manual_moz_observations")
    op.drop_table("proxy_calibration_observations")
    op.drop_index("ix_proxy_authority_evidence_root_domain", table_name="proxy_authority_evidence")
    op.drop_table("proxy_authority_evidence")
    for table, column in (("run_candidates", "proxy_result"), ("run_candidates", "proxy_classification"), ("runs", "proxy_configuration_snapshot"), ("runs", "proxy_calibration_version"), ("runs", "proxy_metric"), ("runs", "proxy_provider")):
        op.drop_column(table, column)
