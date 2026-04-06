---
applyTo: "backend/tests/**"
---
## Golden Rules
- Unit tests cover `services` and pure functions; routes use `TestClient` or async client for integration tests.
- Use `pytest-asyncio` for async tests; avoid blocking I/O in the event loop.
- Service tests for async functions must use `@pytest.mark.asyncio` and `db` fixture (returns `AsyncSession`).
- Use SQLAlchemy 2.0 `select()` for test assertions: `result = await db.execute(select(Model))`; `obj = result.scalars().first()`.
- Fixtures live in `tests/conftest.py` for reuse and isolation.

## Minimum Verifiability
- For each new public API or service logic, provide at least one positive and one negative case.
- Negative tests for routes should assert unified error contract:
  - Body contains `error_code`, `message`.
  - Header contains `X-Request-ID`.
  - For `422` validation failures, expect `error_code == "validation_error"` and `message == "Validation failed"`.
- Mock external calls via `respx`/`pytest-mock`; avoid real network requests.
- Mock AI services (DashScope, OpenAI) and OSS storage in tests.

## Test Organization
- Mirror the app package structure under `tests/`:
  - `tests/services/auth/` for `app/services/auth/` tests
  - `tests/services/content/` for `app/services/content/` tests
  - `tests/routers/` for route integration tests
- Each test file corresponds to an implementation module.

## Auth Helpers for Tests
- When testing authenticated endpoints, create helper fixtures that provide a valid JWT token and test user.
- Use `get_current_user` override in `app.dependency_overrides` to inject test users without real Feishu OAuth.
