"""link Ahrefs DR evidence to run candidates and SERP rows"""
from alembic import op
import sqlalchemy as sa

revision = "f4runproxylineage"
down_revision = "f3runcandidatekmevidence"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "run_candidate_proxy_authority_evidence",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_candidate_id", sa.String(), sa.ForeignKey("run_candidates.id"), nullable=False),
        sa.Column("serp_result_row_id", sa.String(), sa.ForeignKey("serp_results.id"), nullable=False),
        sa.Column("proxy_authority_evidence_id", sa.String(), sa.ForeignKey("proxy_authority_evidence.id"), nullable=False),
        sa.Column("ranking_position", sa.Integer(), nullable=True),
        sa.Column("dr_value_used", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("run_candidate_id", "serp_result_row_id", name="uq_run_candidate_serp_proxy_authority"),
    )
    op.create_index("ix_run_candidate_proxy_authority_evidence_run_candidate_id", "run_candidate_proxy_authority_evidence", ["run_candidate_id"])
    op.create_index("ix_run_candidate_proxy_authority_evidence_serp_result_row_id", "run_candidate_proxy_authority_evidence", ["serp_result_row_id"])
    op.create_index("ix_run_candidate_proxy_authority_evidence_proxy_authority_evidence_id", "run_candidate_proxy_authority_evidence", ["proxy_authority_evidence_id"])

def downgrade():
    op.drop_table("run_candidate_proxy_authority_evidence")
