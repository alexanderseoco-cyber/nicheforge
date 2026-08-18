"""add persistent provider location identities"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "f7providerlocationids"
down_revision = "f6providercalltelemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if inspect(op.get_bind()).has_table("provider_location_identities"):
        return
    op.create_table(
        "provider_location_identities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("city_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("location_code", sa.Integer(), nullable=False),
        sa.Column("provider_location_name", sa.String(length=240), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("state_code", sa.String(length=16), nullable=False),
        sa.Column("city_name", sa.String(length=120), nullable=False),
        sa.Column("location_type", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "city_id", name="uq_provider_location_city"),
        sa.UniqueConstraint("provider", "country_code", "location_code", name="uq_provider_location_code"),
    )
    op.create_index("ix_provider_location_identities_city_id", "provider_location_identities", ["city_id"])
    op.create_index("ix_provider_location_identities_provider", "provider_location_identities", ["provider"])
    op.create_index("ix_provider_location_identities_verified", "provider_location_identities", ["verified"])


def downgrade() -> None:
    if not inspect(op.get_bind()).has_table("provider_location_identities"):
        return
    op.drop_index("ix_provider_location_identities_verified", table_name="provider_location_identities")
    op.drop_index("ix_provider_location_identities_provider", table_name="provider_location_identities")
    op.drop_index("ix_provider_location_identities_city_id", table_name="provider_location_identities")
    op.drop_table("provider_location_identities")
