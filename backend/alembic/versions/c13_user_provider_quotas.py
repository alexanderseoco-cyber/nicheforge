"""Add per-user provider quotas, immutable bonuses, reservations and usage attribution."""
from alembic import op
import sqlalchemy as sa

revision = "c13userquotas"
down_revision = "c12authidentity"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("user_provider_quotas",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False), sa.Column("daily_allowance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("user_id", "provider", name="uq_user_provider_quota"))
    op.create_index("ix_user_provider_quotas_user_id", "user_provider_quotas", ["user_id"])
    op.create_index("ix_user_provider_quotas_provider", "user_provider_quotas", ["provider"])
    op.create_table("user_quota_bonuses",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False), sa.Column("operations", sa.Integer(), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True), sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_user_quota_bonuses_user_id", "user_quota_bonuses", ["user_id"])
    op.create_index("ix_user_quota_bonuses_provider", "user_quota_bonuses", ["provider"])
    op.create_index("ix_user_quota_bonuses_expires_at", "user_quota_bonuses", ["expires_at"])
    op.create_index("ix_user_quota_bonuses_created_by", "user_quota_bonuses", ["created_by"])
    op.create_table("run_reservations",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False), sa.Column("batch_id", sa.String(), nullable=True), sa.Column("reserved_operations", sa.Integer(), nullable=False),
        sa.Column("consumed_operations", sa.Integer(), nullable=False, server_default="0"), sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.create_index("ix_run_reservations_user_id", "run_reservations", ["user_id"])
    op.create_index("ix_run_reservations_provider", "run_reservations", ["provider"])
    op.create_index("ix_run_reservations_batch_id", "run_reservations", ["batch_id"])
    op.create_index("ix_run_reservations_status", "run_reservations", ["status"])
    op.create_table("user_provider_usage",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False), sa.Column("reservation_id", sa.String(), sa.ForeignKey("run_reservations.id"), nullable=True),
        sa.Column("provider_call_id", sa.String(), sa.ForeignKey("provider_calls.id"), nullable=True), sa.Column("operation_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("recorded_at", sa.DateTime(), nullable=False))
    for name, table, cols in [("ix_user_provider_usage_user_id","user_provider_usage",["user_id"]),("ix_user_provider_usage_provider","user_provider_usage",["provider"]),("ix_user_provider_usage_reservation_id","user_provider_usage",["reservation_id"]),("ix_user_provider_usage_provider_call_id","user_provider_usage",["provider_call_id"]),("ix_user_provider_usage_recorded_at","user_provider_usage",["recorded_at"])]: op.create_index(name, table, cols)

def downgrade():
    op.drop_table("user_provider_usage"); op.drop_table("run_reservations"); op.drop_table("user_quota_bonuses"); op.drop_table("user_provider_quotas")
