from __future__ import annotations

from sqlalchemy import text

from app.db.session import engine

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS {schema};

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'profile_role'
          AND n.nspname = :schema
    ) THEN
        EXECUTE format('CREATE TYPE %I.profile_role AS ENUM (''client'', ''provider'')', :schema);
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS {schema}.profiles (
    id UUID PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    role {schema}.profile_role NOT NULL DEFAULT 'client',
    display_name VARCHAR(100) NOT NULL,
    bio VARCHAR(500),
    city VARCHAR(100),
    latitude FLOAT,
    longitude FLOAT,
    services JSON,
    photo_url VARCHAR(300),
    rating FLOAT,
    rating_count INTEGER NOT NULL DEFAULT 0,
    name VARCHAR(100),
    second_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    document_type VARCHAR(20),
    document VARCHAR(50) UNIQUE,
    department VARCHAR(100),
    postal_code VARCHAR(20),
    street VARCHAR(120),
    number VARCHAR(20),
    apartment VARCHAR(20),
    birth_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS {schema}.profile_history (
    history_id UUID PRIMARY KEY,
    profile_id UUID NOT NULL,
    change_type VARCHAR(32) NOT NULL,
    changed_by VARCHAR(100),
    change_origin VARCHAR(50) DEFAULT 'api',
    change_reason VARCHAR(255),
    snapshot JSON,
    previous_snapshot JSON,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_profiles_city
    ON {schema}.profiles (city);

CREATE INDEX IF NOT EXISTS ix_profile_history_profile_id
    ON {schema}.profile_history (profile_id);
"""


async def ensure_schema(schema: str) -> None:
    if engine.url.get_backend_name() != "postgresql":
        return

    sql = SCHEMA_SQL.format(schema=schema)
    async with engine.begin() as conn:
        await conn.execute(text(sql), {"schema": schema})
