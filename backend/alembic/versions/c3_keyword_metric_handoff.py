from alembic import op
import sqlalchemy as sa

revision = "c3keywordhandoff"
down_revision = "c2keywordmetrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("keyword_metric_validation_handoffs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("evidence_id", sa.String(), sa.ForeignKey("keyword_metric_evidence.id"), nullable=False),
        sa.Column("submitted_keyword", sa.String(400), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("provider_keyword", sa.String(400)),
        sa.Column("location_target", sa.JSON(), nullable=False),
        sa.Column("language_code", sa.String(16), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("validation_profile_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False))


def downgrade() -> None:
    op.drop_table("keyword_metric_validation_handoffs")
