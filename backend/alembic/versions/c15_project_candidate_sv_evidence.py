"""link project candidates to immutable search-volume evidence"""
from alembic import op
import sqlalchemy as sa

revision = "c15projectcandidatesvevidence"
down_revision = "c13userquotas"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_candidates", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("search_volume_evidence_id", sa.String(), nullable=True))
        batch_op.create_index("ix_project_candidates_search_volume_evidence_id", ["search_volume_evidence_id"])
        batch_op.create_foreign_key("fk_project_candidates_search_volume_evidence", "keyword_metric_evidence", ["search_volume_evidence_id"], ["id"])


def downgrade():
    with op.batch_alter_table("project_candidates", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_project_candidates_search_volume_evidence", type_="foreignkey")
        batch_op.drop_index("ix_project_candidates_search_volume_evidence_id")
        batch_op.drop_column("search_volume_evidence_id")
