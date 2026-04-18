---
applyTo: "backend/app/core/*.py, backend/app/routers/auth.py, backend/app/routers/admin.py"
---
## Configuration
- Use `pydantic-settings` to load environment variables; provide minimal template via `.env.example`.
- Centralize config in `core/config.py`; other modules receive configuration via DI or explicit parameters.
- Config groups: Database (`DATABASE_URL`), Feishu OAuth (`FEISHU_APP_ID`, `FEISHU_APP_SECRET`, etc.), Aliyun OSS (`OSS_*`), AI (`DASHSCOPE_API_KEY`, `OPENAI_API_KEY`), CORS, JWT.

## Security
- JWT with `python-jose` (HS256); secrets from environment; set sane expiration.
- Authentication via Feishu OAuth 2.0 only — no password-based auth, no argon2/bcrypt.
- Authorization with DI at router layer via `get_current_user` and `require_role(*roles)`.
- Services accept only authorized subject identifiers (user_id, role); never receive raw tokens.

## Logging
- Use structured JSON logging; avoid sensitive output (tokens, keys, credentials).
- Centralize handler/formatter installation in `backend/app/core/logging.py`; initialize it during app startup. Never rely on the root logger or Python's default `lastResort` handler for application `INFO` logs.
- Application modules must log through the `app.*` hierarchy (prefer `logging.getLogger(__name__)`) or the shared `promoflow.api` logger so configured handlers always apply.
- Log payload fields include: `timestamp`, `level`, `logger`, `message`, plus contextual fields when present: `request_id`, `status_code`, `method`, `path`, `duration_ms`, `error_code`, and `exc_info` for exceptions.
- Prefer centralized sanitization/masking helpers for IDs and free-form user input. Log fingerprints, lengths, counts, or masked identifiers instead of raw OAuth codes, user queries, chat IDs, URLs, file keys, or other sensitive values.
- Severity: record `4xx` as warnings; record `5xx` and unexpected errors as exceptions (stack traces included).
- For external calls (Feishu API, OSS, LLM), log request ID, latency, and status; include exception types and context on errors.
