---
applyTo: "backend/app/services/**/*.py"
---
## Role
- Encapsulate business flows and external dependencies (LLM, httpx, OSS, etc.).
- Decoupled from FastAPI: do not import `Request`/`Response` or other framework types.
- **MUST NOT** import from `app.schemas.*`; use `app.domains.*` types instead.

## Directory Layout
- `app/services/shared/`: Side-effect free helpers. No dependencies on other service layers.
- `app/services/infrastructure/`: Adapters for external systems (storage, ai). May depend on `shared/` only.
  - `infrastructure/storage.py`: Aliyun OSS adapter (presigned URLs, delete, public URL).
  - `infrastructure/ai.py`: Qianwen multimodal analysis + OpenAI embeddings + RAG.
- `app/services/auth/`: Auth domain package (Feishu OAuth, user management).
- `app/services/content/`: Content domain package (CRUD, audit).
- `app/services/search/`: Search domain package (pgvector semantic search).

## Dependency Rules
- Allowed direction: `shared → (none)`, `infrastructure → shared`, `domain packages → shared|infrastructure`.
- Avoid circular imports between domain modules. Prefer explicit package exports in `__init__.py` when needed.

## Design Conventions
- Inputs/outputs use `domains/` types; never `schemas/` or ORM entities for public APIs.
  - Internal helper functions (e.g., `_content_to_output`) may read ORM objects for conversion to domain outputs.
- **Command pattern**: For write operations, accept `*Command` objects via parameter named `command`:
  ```python
  async def login_with_code(
      db: AsyncSession,
      *,
      command: FeishuLoginCommand,
  ) -> AuthSession:
  ```
- **Simple queries**: May accept direct params without Command wrapper:
  ```python
  async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
  ```
- Routers handle `schemas/` ↔ `domains/` conversion via `to_domain()`/`from_domain()`; services remain HTTP-agnostic.
- Propagate errors via domain exceptions or structured error results; router converts them to HTTP errors.
- **Infrastructure exception conversion**: Catch infrastructure exceptions (e.g., `httpx.HTTPError`, `OSSError`) within service functions and convert to domain exceptions. Domain `errors.py` must not import from infrastructure.
- Prefer stable, documented `error_code` values for domain errors to aid client handling and observability.
- External calls (e.g., httpx) must have timeouts; add retries as needed.
- Testing: Every new service method requires corresponding unit tests with positive and negative cases. Tests currently live as flat files under `tests/` (e.g., `tests/test_content.py`); new test files should follow this pattern until the layout is explicitly migrated to mirrored sub-packages.

## AI and Content Analysis
- Centralize AI logic in `services/infrastructure/ai.py`; keep it testable and swappable (models/providers).
- Build prompts and parse outputs in infrastructure adapter; keep routes unaware of LLM details.
- **LLM response parsing**: Pydantic types for LLM JSON parsing are allowed in the infrastructure adapter (not domain layer):
  ```python
  # Private to infrastructure, used for LLM response parsing only
  class _AnalysisResponse(BaseModel):
      summary: str = ""
      keywords: list[str] = Field(default_factory=list)
  ```

## Concurrency and Performance
- **DB Operations**: Use `AsyncSession` throughout. Query with SQLAlchemy 2.0 `select()` style:
  - Read: `result = await db.execute(select(Model).filter(...))`; `obj = result.scalars().first()`
  - Write: `db.add(obj)`, rely on session auto-commit or explicit `await db.flush()`
- **External SDKs**: For sync-only SDKs (OSS `oss2`, DashScope multimodal), wrap calls with `run_in_threadpool()`.
- Reuse clients (e.g., `httpx.AsyncClient`, `AsyncOpenAI`) centrally; avoid recreating per call.
