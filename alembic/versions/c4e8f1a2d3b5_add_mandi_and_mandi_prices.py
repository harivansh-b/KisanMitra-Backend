"""add_mandi_and_mandi_prices

Revision ID: c4e8f1a2d3b5
Revises: ba3d2216f7a5
Create Date: 2026-09-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8f1a2d3b5'
down_revision: Union[str, Sequence[str], None] = 'ba3d2216f7a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create mandis and mandi_prices tables.

    Uses raw SQL for the PostGIS geography column — SQLAlchemy autogenerate
    does not reliably handle Geography types, so we use op.execute() instead.
    """
    conn = op.get_bind()
    is_postgresql = conn.dialect.name == "postgresql"

    if is_postgresql:
        # Ensure PostGIS is available (also done in env.py but safe to repeat)
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

        op.execute("""
            CREATE TABLE IF NOT EXISTS mandis (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                market_code VARCHAR(50),
                state VARCHAR(100) NOT NULL DEFAULT 'Maharashtra',
                district VARCHAR(100) NOT NULL,
                taluk VARCHAR(100),
                address TEXT,
                latitude FLOAT,
                longitude FLOAT,
                location geography(Point, 4326),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                source VARCHAR(100),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)

        # Indexes for mandis
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandis_name ON mandis(name);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandis_district ON mandis(district);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandis_state ON mandis(state);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandis_market_code ON mandis(market_code);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandis_is_active ON mandis(is_active);")
        op.execute("CREATE INDEX IF NOT EXISTS idx_mandis_location ON mandis USING GIST(location);")

        op.execute("""
            CREATE TABLE IF NOT EXISTS mandi_prices (
                id VARCHAR(36) PRIMARY KEY,
                mandi_id VARCHAR(36) NOT NULL REFERENCES mandis(id) ON DELETE CASCADE,
                commodity_id VARCHAR(36) REFERENCES crops(id) ON DELETE SET NULL,
                commodity_name VARCHAR(150) NOT NULL,
                variety VARCHAR(100),
                grade VARCHAR(50),
                arrival_date DATE NOT NULL,
                arrival_quantity FLOAT,
                arrival_unit VARCHAR(20) DEFAULT 'Quintal',
                min_price FLOAT NOT NULL,
                max_price FLOAT NOT NULL,
                modal_price FLOAT NOT NULL,
                price_unit VARCHAR(30) NOT NULL DEFAULT 'INR/Quintal',
                source VARCHAR(100) NOT NULL DEFAULT 'AGMARKNET',
                source_record_id VARCHAR(200),
                fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_mandi_price_record
                    UNIQUE(mandi_id, commodity_name, variety, grade, arrival_date, source),
                CONSTRAINT ck_mandi_price_min_positive CHECK (min_price >= 0),
                CONSTRAINT ck_mandi_price_max_positive CHECK (max_price >= 0),
                CONSTRAINT ck_mandi_price_modal_positive CHECK (modal_price >= 0),
                CONSTRAINT ck_mandi_arrival_qty_positive
                    CHECK (arrival_quantity IS NULL OR arrival_quantity >= 0),
                CONSTRAINT ck_mandi_price_min_le_modal CHECK (min_price <= modal_price),
                CONSTRAINT ck_mandi_price_modal_le_max CHECK (modal_price <= max_price)
            );
        """)

        # Indexes for mandi_prices
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandi_prices_mandi_id ON mandi_prices(mandi_id);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandi_prices_commodity_name ON mandi_prices(commodity_name);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandi_prices_arrival_date ON mandi_prices(arrival_date);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandi_prices_variety ON mandi_prices(variety);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_mandi_prices_commodity_id ON mandi_prices(commodity_id);")

    else:
        # SQLite fallback (for unit tests) — no PostGIS, simplified schema
        op.create_table(
            "mandis",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("market_code", sa.String(50), nullable=True),
            sa.Column("state", sa.String(100), nullable=False, server_default="Maharashtra"),
            sa.Column("district", sa.String(100), nullable=False),
            sa.Column("taluk", sa.String(100), nullable=True),
            sa.Column("address", sa.Text, nullable=True),
            sa.Column("latitude", sa.Float, nullable=True),
            sa.Column("longitude", sa.Float, nullable=True),
            sa.Column("location", sa.String, nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
            sa.Column("source", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_mandis_name", "mandis", ["name"])
        op.create_index("ix_mandis_district", "mandis", ["district"])
        op.create_index("ix_mandis_state", "mandis", ["state"])

        op.create_table(
            "mandi_prices",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("mandi_id", sa.String(36), sa.ForeignKey("mandis.id", ondelete="CASCADE"), nullable=False),
            sa.Column("commodity_id", sa.String(36), sa.ForeignKey("crops.id", ondelete="SET NULL"), nullable=True),
            sa.Column("commodity_name", sa.String(150), nullable=False),
            sa.Column("variety", sa.String(100), nullable=True),
            sa.Column("grade", sa.String(50), nullable=True),
            sa.Column("arrival_date", sa.Date, nullable=False),
            sa.Column("arrival_quantity", sa.Float, nullable=True),
            sa.Column("arrival_unit", sa.String(20), nullable=True, server_default="Quintal"),
            sa.Column("min_price", sa.Float, nullable=False),
            sa.Column("max_price", sa.Float, nullable=False),
            sa.Column("modal_price", sa.Float, nullable=False),
            sa.Column("price_unit", sa.String(30), nullable=False, server_default="INR/Quintal"),
            sa.Column("source", sa.String(100), nullable=False, server_default="AGMARKNET"),
            sa.Column("source_record_id", sa.String(200), nullable=True),
            sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("mandi_id", "commodity_name", "variety", "grade", "arrival_date", "source", name="uq_mandi_price_record"),
        )
        op.create_index("ix_mandi_prices_mandi_id", "mandi_prices", ["mandi_id"])
        op.create_index("ix_mandi_prices_commodity_name", "mandi_prices", ["commodity_name"])
        op.create_index("ix_mandi_prices_arrival_date", "mandi_prices", ["arrival_date"])


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("DROP TABLE IF EXISTS mandi_prices;")
        op.execute("DROP TABLE IF EXISTS mandis;")
    else:
        op.drop_table("mandi_prices")
        op.drop_table("mandis")
