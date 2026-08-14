"""Persist validated provider country geo mappings."""
from alembic import op
import sqlalchemy as sa

revision = "c8countrygeomappings"
down_revision = "c7geodiagnostics"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "provider_country_geo_mappings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("criterion_id", sa.String(80), nullable=False),
        sa.Column("resource_name", sa.String(200), nullable=False),
        sa.Column("provider_name", sa.String(240)),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("provider_status", sa.String(40)),
        sa.Column("mapping_status", sa.String(40), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.UniqueConstraint("country_code", "provider", name="uq_provider_country_geo_identity"),
    )
    op.create_index("ix_provider_country_geo_mappings_country_code", "provider_country_geo_mappings", ["country_code"])

def downgrade():
    op.drop_table("provider_country_geo_mappings")
