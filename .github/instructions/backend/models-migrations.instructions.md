---
applyTo: "backend/app/models/*.py, backend/migrations/**"
---
## Role
- `models/` define ORM tables/relations/indexes only; no business logic or I/O.
- Data access is performed via `services/`; `routers/` must not operate on models directly.

## Dependency Rules
- **MUST NOT** import business types (dataclasses, commands, outputs) from `app.domains.*`.
- **MAY** import **enumerations only** (`str, Enum` types) from `app.domains.*` for use as column types. This avoids duplicating enum definitions while keeping models storage-oriented.

## SQLAlchemy Conventions
- Use SQLAlchemy 2.0 style with `DeclarativeBase` and `Mapped` type annotations.
- Explicitly declare column types, indexes, unique constraints, and FK behaviors.
- Timestamps: `created_at`, `updated_at`; keep them consistent via service-layer updates or DB defaults.
- Use `pgvector` `Vector` column type for embedding storage.
- Never expose sensitive model fields to `schemas/`; filter in `schemas` when needed.

## Alembic Migrations
- Any model change requires a migration: `alembic revision --autogenerate -m "..."`.
- Before commit, run `alembic upgrade head` locally; production follows canary/rollbackable strategies.
- Do not rewrite published migration history; add patch migrations for fixes.
- Testing: Model changes affecting business logic should include corresponding tests to verify data integrity.

## Data Compatibility
- Follow forward-compat and smooth rollout; avoid breaking changes. Use two-step releases when needed (add column → dual write → remove old column).
