"""allow unknown ProviderCall monetary currency"""
from alembic import op
import sqlalchemy as sa

revision = "faprovidercallcurrency"
down_revision = "f9serpcoveragepolicy"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("provider_calls") as batch:
        batch.alter_column(
            "currency",
            existing_type=sa.String(length=3),
            nullable=True,
            server_default=None,
        )


def downgrade():
    with op.batch_alter_table("provider_calls") as batch:
        batch.alter_column(
            "currency",
            existing_type=sa.String(length=3),
            nullable=False,
            server_default="USD",
        )
