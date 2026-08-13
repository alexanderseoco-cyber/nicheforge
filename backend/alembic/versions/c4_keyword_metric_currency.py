"""Add provider currency and derived USD fields to keyword metrics."""
from alembic import op
import sqlalchemy as sa

revision = "c4keywordcurrency"
down_revision = "c3keywordhandoff"
branch_labels = None
depends_on = None

def upgrade():
    for name, typ in [("provider_currency_code", sa.String(3)), ("usd_cpc", sa.Float()), ("usd_low_bid", sa.Float()), ("usd_high_bid", sa.Float()), ("fx_rate", sa.Float()), ("fx_rate_date", sa.String(32)), ("fx_source", sa.String(120))]:
        op.add_column("keyword_metric_evidence", sa.Column(name, typ, nullable=True))

def downgrade():
    for name in ["fx_source", "fx_rate_date", "fx_rate", "usd_high_bid", "usd_low_bid", "usd_cpc", "provider_currency_code"]:
        op.drop_column("keyword_metric_evidence", name)
