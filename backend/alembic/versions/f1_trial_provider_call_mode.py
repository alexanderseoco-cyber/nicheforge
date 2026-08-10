"""add provider execution mode audit field"""
from alembic import op
import sqlalchemy as sa
revision = "f1trialmode"
down_revision = "d2a1f0c4e7b9"
branch_labels = None
depends_on = None
def upgrade():
    op.add_column("provider_calls", sa.Column("execution_mode", sa.String(20), nullable=True))
def downgrade():
    op.drop_column("provider_calls", "execution_mode")
