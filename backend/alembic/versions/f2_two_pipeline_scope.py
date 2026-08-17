"""add explicit local/general validation scope fields"""
from alembic import op
import sqlalchemy as sa

revision = "f2twopipelinescope"
down_revision = "c15projectcandidatesvevidence"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("candidate_entities", recreate="always") as batch:
        batch.alter_column("city_id", existing_type=sa.String(), nullable=True)
        batch.add_column(sa.Column("validation_scope", sa.String(30), nullable=False, server_default="LOCAL_RANK_RENT"))
        batch.create_index("ix_candidate_entities_validation_scope", ["validation_scope"])
    with op.batch_alter_table("project_candidates", recreate="always") as batch:
        batch.add_column(sa.Column("validation_scope", sa.String(30), nullable=False, server_default="LOCAL_RANK_RENT"))
        batch.add_column(sa.Column("scope_reason", sa.String(500), nullable=True))
        batch.create_index("ix_project_candidates_validation_scope", ["validation_scope"])
    with op.batch_alter_table("run_candidates", recreate="always") as batch:
        batch.add_column(sa.Column("validation_scope", sa.String(30), nullable=False, server_default="LOCAL_RANK_RENT"))
        batch.add_column(sa.Column("authority_opportunity_reason", sa.String(1000), nullable=True))
        batch.create_index("ix_run_candidates_validation_scope", ["validation_scope"])


def downgrade():
    with op.batch_alter_table("run_candidates", recreate="always") as batch:
        batch.drop_index("ix_run_candidates_validation_scope")
        batch.drop_column("authority_opportunity_reason")
        batch.drop_column("validation_scope")
    with op.batch_alter_table("project_candidates", recreate="always") as batch:
        batch.drop_index("ix_project_candidates_validation_scope")
        batch.drop_column("scope_reason")
        batch.drop_column("validation_scope")
    with op.batch_alter_table("candidate_entities", recreate="always") as batch:
        batch.drop_index("ix_candidate_entities_validation_scope")
        batch.drop_column("validation_scope")
        batch.alter_column("city_id", existing_type=sa.String(), nullable=False)
