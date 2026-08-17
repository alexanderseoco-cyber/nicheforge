"""link DataForSEO backlink evidence to run candidates and SERP rows"""
from alembic import op
import sqlalchemy as sa

revision = "f5runbacklinklineage"
down_revision = "f4runproxylineage"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("run_candidate_backlink_evidence",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_candidate_id", sa.String(), sa.ForeignKey("run_candidates.id"), nullable=False),
        sa.Column("serp_result_row_id", sa.String(), sa.ForeignKey("serp_results.id"), nullable=False),
        sa.Column("proxy_backlink_evidence_id", sa.String(), sa.ForeignKey("proxy_backlink_feature_evidence.id"), nullable=False),
        sa.Column("ranking_position", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("run_candidate_id", "serp_result_row_id", name="uq_run_candidate_serp_backlink"))
    for name, column in (("run_candidate_backlink_evidence_run_candidate_id", "run_candidate_id"), ("run_candidate_backlink_evidence_serp_result_row_id", "serp_result_row_id"), ("run_candidate_backlink_evidence_proxy_backlink_evidence_id", "proxy_backlink_evidence_id")):
        op.create_index("ix_" + name, "run_candidate_backlink_evidence", [column])

def downgrade():
    op.drop_table("run_candidate_backlink_evidence")
