-- Keep database bootstrap minimal and let Alembic own the schema.
-- This script runs only when the PostgreSQL volume is initialized for the first time.
CREATE EXTENSION IF NOT EXISTS vector;
