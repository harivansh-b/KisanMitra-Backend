import os
from typing import Generator
from sqlalchemy import create_engine, types
from sqlalchemy.orm import declarative_base, sessionmaker
from geoalchemy2 import Geography

from app.core.config import settings


# Dialect-aware Point geography type that uses PostGIS Geography in PostgreSQL
# and standard VARCHAR in SQLite for seamless local unit testing.
class PointGeography(types.TypeDecorator):
    impl = types.String
    cache_ok = True
    spatial_index = False

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Geography(geometry_type="POINT", srid=4326, spatial_index=False))
        else:
            return dialect.type_descriptor(types.String())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name != "postgresql":
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        return value


# Database engine setup
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
