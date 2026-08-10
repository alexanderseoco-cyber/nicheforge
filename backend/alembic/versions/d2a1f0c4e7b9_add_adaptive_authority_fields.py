"""add persisted adaptive authority configuration and audit fields"""
from alembic import op
import sqlalchemy as sa

revision = "d2a1f0c4e7b9"
down_revision = ("5c45b58975e9", "6f66991da474")
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runs") as batch:
        batch.add_column(sa.Column("minimum_weak_domains", sa.Integer(), nullable=False, server_default="4"))
        batch.add_column(sa.Column("ideal_weak_domains", sa.Integer(), nullable=False, server_default="5"))
        batch.add_column(sa.Column("authority_evaluation_mode", sa.String(20), nullable=False, server_default="ADAPTIVE"))
        batch.add_column(sa.Column("authority_batch_size", sa.Integer(), nullable=False, server_default="5"))
        batch.add_column(sa.Column("adaptive_seek_ideal", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("run_candidates") as batch:
        batch.add_column(sa.Column("minimum_weak_domains_used", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("ideal_weak_domains_used", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("authority_evaluation_mode_used", sa.String(20), nullable=True))
        batch.add_column(sa.Column("authority_targets_evaluated", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("authority_targets_cached", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("authority_targets_fetched", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("authority_targets_unchecked", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("confirmed_weak_count", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("opportunity_classification", sa.String(30), nullable=True))
        batch.add_column(sa.Column("adaptive_seek_ideal_used", sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("run_candidates") as batch:
        for name in ("adaptive_seek_ideal_used", "opportunity_classification", "confirmed_weak_count", "authority_targets_unchecked", "authority_targets_fetched", "authority_targets_cached", "authority_targets_evaluated", "authority_evaluation_mode_used", "ideal_weak_domains_used", "minimum_weak_domains_used"):
            batch.drop_column(name)
    with op.batch_alter_table("runs") as batch:
        for name in ("adaptive_seek_ideal", "authority_batch_size", "authority_evaluation_mode", "ideal_weak_domains", "minimum_weak_domains"):
            batch.drop_column(name)
