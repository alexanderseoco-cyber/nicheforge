from alembic import op
import sqlalchemy as sa

revision = "b1serpproxyeval"
down_revision = "a9proxymapping"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("serp_proxy_evaluations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("serp_snapshot_id", sa.String(), sa.ForeignKey("serp_snapshots.id"), unique=True, nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=True), sa.Column("evaluation_version", sa.String(80), nullable=False),
        sa.Column("calibration_version", sa.String(80), nullable=False), sa.Column("organic_positions_available", sa.Integer(), nullable=False),
        sa.Column("likely_weak_count", sa.Integer(), nullable=False), sa.Column("possible_weak_count", sa.Integer(), nullable=False),
        sa.Column("unlikely_weak_count", sa.Integer(), nullable=False), sa.Column("unknown_missing_count", sa.Integer(), nullable=False),
        sa.Column("minimum_possible_weak", sa.Integer(), nullable=False), sa.Column("maximum_plausible_weak", sa.Integer(), nullable=False),
        sa.Column("required_weak_count", sa.Integer(), nullable=False), sa.Column("classification", sa.String(50), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False), sa.Column("uncertainty", sa.String(100), nullable=False),
        sa.Column("recommended_action", sa.String(100), nullable=False), sa.Column("position_evidence", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False))
    op.create_table("serp_manual_moz_validations",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("serp_snapshot_id", sa.String(), sa.ForeignKey("serp_snapshots.id"), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=True), sa.Column("positions_checked", sa.Integer(), nullable=False),
        sa.Column("moz_da_by_position", sa.JSON(), nullable=False), sa.Column("actual_da_below_10_count", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(30), nullable=False), sa.Column("validation_status", sa.String(30), nullable=False), sa.Column("unavailable_positions", sa.JSON(), nullable=False), sa.Column("mismatched_domains", sa.JSON(), nullable=False), sa.Column("provenance", sa.String(40), nullable=False), sa.Column("validated_at", sa.DateTime(), nullable=False))

def downgrade():
    op.drop_table("serp_manual_moz_validations")
    op.drop_table("serp_proxy_evaluations")
