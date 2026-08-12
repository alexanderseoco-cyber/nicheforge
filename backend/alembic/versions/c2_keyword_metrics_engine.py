from alembic import op
import sqlalchemy as sa

revision = "c2keywordmetrics"
down_revision = "b1serpproxyeval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("keyword_metric_queries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("submitted_keyword", sa.String(400), nullable=False),
        sa.Column("normalized_keyword", sa.String(400), nullable=False),
        sa.Column("location_name", sa.String(240)),
        sa.Column("location_target", sa.JSON(), nullable=False),
        sa.Column("language_code", sa.String(16), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("keyword_metric_evidence",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("query_id", sa.String(), sa.ForeignKey("keyword_metric_queries.id"), nullable=False),
        sa.Column("submitted_keyword", sa.String(400), nullable=False),
        sa.Column("provider_keyword", sa.String(400)),
        sa.Column("normalized_keyword", sa.String(400), nullable=False),
        sa.Column("location_name", sa.String(240)),
        sa.Column("location_target", sa.JSON(), nullable=False),
        sa.Column("language_code", sa.String(16), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("avg_monthly_searches", sa.Integer()),
        sa.Column("competition", sa.Float()),
        sa.Column("competition_index", sa.Integer()),
        sa.Column("cpc", sa.Float()), sa.Column("low_bid", sa.Float()), sa.Column("high_bid", sa.Float()),
        sa.Column("monthly_history", sa.JSON(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False), sa.Column("fresh_until", sa.DateTime()),
        sa.Column("cost", sa.Float()), sa.Column("mapping_status", sa.String(30), nullable=False))
    op.create_table("keyword_metric_batches",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("submitted_count", sa.Integer(), nullable=False), sa.Column("deduplicated_count", sa.Integer(), nullable=False),
        sa.Column("returned_count", sa.Integer(), nullable=False), sa.Column("mapped_count", sa.Integer(), nullable=False),
        sa.Column("unmapped_count", sa.Integer(), nullable=False), sa.Column("status", sa.String(30), nullable=False),
        sa.Column("cost", sa.Float()), sa.Column("created_at", sa.DateTime(), nullable=False))


def downgrade() -> None:
    op.drop_table("keyword_metric_batches")
    op.drop_table("keyword_metric_evidence")
    op.drop_table("keyword_metric_queries")
