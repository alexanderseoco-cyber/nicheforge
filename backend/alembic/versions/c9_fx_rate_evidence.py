"""Persist restart-safe FX rate evidence."""
from alembic import op
import sqlalchemy as sa

revision = "c9fxrateevidence"
down_revision = "c8countrygeomappings"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "fx_rate_evidence",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source_currency", sa.String(3), nullable=False),
        sa.Column("target_currency", sa.String(3), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("requested_as_of_date", sa.Date(), nullable=True),
        sa.Column("provider_effective_date", sa.Date(), nullable=True),
        sa.Column("rate", sa.Numeric(24, 12), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("fresh_until", sa.DateTime(), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.UniqueConstraint("source_currency", "target_currency", "mode", "requested_as_of_date", "provider", name="uq_fx_rate_identity"),
    )
    op.create_index("ix_fx_rate_evidence_source_currency", "fx_rate_evidence", ["source_currency"])
    op.create_index("ix_fx_rate_evidence_target_currency", "fx_rate_evidence", ["target_currency"])

def downgrade():
    op.drop_table("fx_rate_evidence")
