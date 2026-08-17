"""add canonical keyword-metrics lineage to run candidates"""
from alembic import op
import sqlalchemy as sa

revision = "f3runcandidatekmevidence"
down_revision = "f2twopipelinescope"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("run_candidates", recreate="always") as batch:
        batch.add_column(sa.Column("keyword_metric_evidence_id", sa.String(), nullable=True))
        batch.create_foreign_key("fk_run_candidates_keyword_metric_evidence_id", "keyword_metric_evidence", ["keyword_metric_evidence_id"], ["id"])
        batch.create_index("ix_run_candidates_keyword_metric_evidence_id", ["keyword_metric_evidence_id"])


def downgrade():
    with op.batch_alter_table("run_candidates", recreate="always") as batch:
        batch.drop_index("ix_run_candidates_keyword_metric_evidence_id")
        batch.drop_constraint("fk_run_candidates_keyword_metric_evidence_id", type_="foreignkey")
        batch.drop_column("keyword_metric_evidence_id")
