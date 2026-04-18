---
applyTo: "backend/app/workers/*.py"
---
## Role
- Handle background and long-running jobs (AI analysis, notifications, cleanup).
- Decoupled from web routes; accept primitives or `domains/` types only.

## Background Tasks
- Use FastAPI `BackgroundTasks` for lightweight async jobs (AI content analysis, embedding generation).
- Background task functions are defined in the router module that enqueues them or in dedicated `workers/` modules.
- Tasks must not import `schemas/` or route-layer objects directly; accept primitive IDs/values and create their own DB sessions via `AsyncSessionLocal()`.
- Infrastructure calls (LLM, OSS) use `app.services.infrastructure.*` adapters.

## Guidelines
- Keep tasks idempotent: re-running with the same input should produce the same result.
- Handle failures gracefully; log errors with context (content_id, task type).
- Worker logs must go through the configured application logger hierarchy (`app.*` / `promoflow.api`) so scheduled jobs keep `INFO`-level visibility outside request scope.
- For CPU-bound or long-blocking operations, wrap with `run_in_threadpool()`.
- If the project scales beyond what BackgroundTasks supports, consider migrating to Celery or ARQ with Redis.
