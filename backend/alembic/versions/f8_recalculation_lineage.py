"""add explicit recalculation RunCandidate lineage"""
from alembic import op
import sqlalchemy as sa

revision = "f8recalculationlineage"
down_revision = "f7providerlocationids"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("run_candidates") as batch:
        batch.add_column(sa.Column("parent_run_candidate_id", sa.String(), nullable=True))
        batch.create_index("ix_run_candidates_parent_run_candidate_id", ["parent_run_candidate_id"])
        batch.create_foreign_key("fk_run_candidates_parent_run_candidate_id", "run_candidates", ["parent_run_candidate_id"], ["id"])

def downgrade():
    with op.batch_alter_table("run_candidates") as batch:
        batch.drop_constraint("fk_run_candidates_parent_run_candidate_id", type_="foreignkey")
        batch.drop_index("ix_run_candidates_parent_run_candidate_id")
        batch.drop_column("parent_run_candidate_id")
