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
    op.add_column("runs", sa.Column("proxy_reject_audit_percent", sa.Float(), nullable=True))
    op.create_table("proxy_authority_evidence",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("target_url", sa.String(2000), nullable=False),
        sa.Column("root_domain", sa.String(500), nullable=False), sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("metric", sa.String(80), nullable=False), sa.Column("domain_rating", sa.Float(), nullable=True),
        sa.Column("source_kind", sa.String(40), nullable=False), sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("request_metadata", sa.JSON(), nullable=True), sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("fresh_until", sa.DateTime(), nullable=True))
    op.create_index("ix_proxy_authority_evidence_root_domain", "proxy_authority_evidence", ["root_domain"])
    op.create_table("proxy_backlink_feature_evidence",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("target_domain", sa.String(500), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False), sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True), sa.Column("backlinks", sa.Integer(), nullable=True),
        sa.Column("referring_domains", sa.Integer(), nullable=True), sa.Column("referring_main_domains", sa.Integer(), nullable=True),
        sa.Column("referring_ips", sa.Integer(), nullable=True), sa.Column("referring_subnets", sa.Integer(), nullable=True),
        sa.Column("referring_domains_nofollow", sa.Integer(), nullable=True), sa.Column("referring_main_domains_nofollow", sa.Integer(), nullable=True),
        sa.Column("backlinks_spam_score", sa.Float(), nullable=True), sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("request_metadata", sa.JSON(), nullable=True), sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("fresh_until", sa.DateTime(), nullable=True), sa.Column("actual_cost", sa.Float(), nullable=True),
        sa.Column("api_status_code", sa.Integer(), nullable=True), sa.Column("api_status_message", sa.String(500), nullable=True))
    op.create_index("ix_proxy_backlink_feature_evidence_target_domain", "proxy_backlink_feature_evidence", ["target_domain"])
    op.create_table("proxy_calibration_observations",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("normalized_domain", sa.String(500), nullable=False),
        sa.Column("ahrefs_dr", sa.Float(), nullable=True), sa.Column("moz_da", sa.Float(), nullable=True),
        sa.Column("provenance", sa.String(40), nullable=False), sa.Column("calibration_version", sa.String(80), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False), sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.Column("dataforseo_features", sa.JSON(), nullable=True), sa.Column("moz_da_below_10", sa.Boolean(), nullable=True),
        sa.Column("feature_set_version", sa.String(80), nullable=True))
    op.create_table("manual_moz_observations",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("normalized_domain", sa.String(500), nullable=False),
        sa.Column("moz_da", sa.Float(), nullable=True), sa.Column("moz_pa", sa.Float(), nullable=True),
        sa.Column("spam_score", sa.Float(), nullable=True), sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=True), sa.Column("observed_at", sa.DateTime(), nullable=False))


def downgrade():
    op.drop_column("proxy_calibration_observations", "feature_set_version")
    op.drop_column("proxy_calibration_observations", "moz_da_below_10")
    op.drop_column("proxy_calibration_observations", "dataforseo_features")
    op.drop_index("ix_proxy_backlink_feature_evidence_target_domain", table_name="proxy_backlink_feature_evidence")
    op.drop_table("proxy_backlink_feature_evidence")
    op.drop_table("manual_moz_observations")
    op.drop_table("proxy_calibration_observations")
    op.drop_index("ix_proxy_authority_evidence_root_domain", table_name="proxy_authority_evidence")
    op.drop_table("proxy_authority_evidence")
    for table, column in (("runs", "proxy_reject_audit_percent"), ("run_candidates", "proxy_result"), ("run_candidates", "proxy_classification"), ("runs", "proxy_configuration_snapshot"), ("runs", "proxy_calibration_version"), ("runs", "proxy_metric"), ("runs", "proxy_provider")):
        op.drop_column(table, column)
