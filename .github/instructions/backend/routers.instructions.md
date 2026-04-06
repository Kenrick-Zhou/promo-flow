---
applyTo: "backend/app/routers/*.py"
---
## Role
- Handle routing, parameter validation, dependency injection, and service orchestration only. No business logic, no direct DB access.
- **Type conversion boundary**: Convert `schemas/` <--> `domains/` types at router layer.

## Structure
- Use `APIRouter`; set appropriate `prefix`, `tags`, `summary`, `description`, `response_model`.
- HTTP input/output use `schemas/` models; services accept/return `domains/` types.
- Dependencies are imported from `core/deps.py` (DB session via `get_db`, auth via `get_current_user`, role check via `require_role`).
- Testing: New routes require integration tests using TestClient. See [testing rule](testing.instructions.md) for detailed conventions.

## Schema <--> Domain Conversion Pattern

Use `command` as the parameter name for business input when calling services:

```python
@router.get("/callback", response_model=TokenOut)
async def feishu_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> TokenOut:
    try:
        session = await login_with_code(
            db,
            command=FeishuLoginCommand(code=code),
        )
    except FeishuOAuthError as exc:
        raise_auth_error(exc)
    return TokenOut.from_domain(session)
```

### to_domain Conversion Rules

| Category | Where to pass | Example |
|----------|---------------|---------|
| **Business params** | Inject into Command via `to_domain()` | `data.to_domain(uploaded_by=current_user.id)` |
| **current_user fields** | Inject via `to_domain()` params | `to_domain(uploaded_by=current_user.id)` |
| **Infrastructure deps** | Pass as separate params to service | `db=db` |
| **Simple queries** | Pass directly, no Command needed | `get_content(db, content_id)` |

### Example with current_user Injection

```python
@router.post("", response_model=ContentOut, status_code=status.HTTP_201_CREATED)
async def create_content_route(
    data: ContentCreateIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ContentOut:
    try:
        content = await create_content(
            db, command=data.to_domain(uploaded_by=current_user.id),
        )
    except Exception as exc:
        raise_content_error(exc)
    return ContentOut.from_domain(content)
```

## API Design Principles
- This project **generally follows RESTful conventions** for consistency and predictability, but **pragmatism over dogma**.
- **Action-style endpoints are permitted** when they improve clarity or better match the domain model (e.g., authentication flows, specialized operations).
- Don't force REST where it doesn't fit—choose the pattern that best serves the API contract.

### Resource-Oriented Design (Preferred for CRUD)
- Use **nouns (plural form)** for resource names: `/contents`, `/users`, `/audits`.
- Let HTTP methods convey actions:
  - ✅ `POST /contents` (create)
  - ✅ `PATCH /contents/{id}` (update)
  - ❌ `POST /contents/create` (redundant verb)
- For sub-resources, use hierarchical paths: `/contents/{id}/audit`.
- Use kebab-case for multi-word resources: `/presigned-upload`.

### HTTP Method Semantics
- **GET**: Retrieve resource(s); idempotent, no side effects, cacheable.
- **POST**: Create new resource or trigger operations (including action-style endpoints).
- **PUT**: Replace entire resource (rarely used; prefer PATCH).
- **PATCH**: Partial update of resource fields.
- **DELETE**: Remove resource; idempotent.

### Query Parameters
- Use for filtering, sorting, pagination: `GET /contents?status=pending&limit=20&offset=0`.
- Keep consistent naming: `limit`/`offset` or `page`/`per_page`.
- Prefer query params over path segments for optional filters.

### Action-Style Endpoints (Allowed When Appropriate)
- **Authentication domain**: OAuth flows are naturally action-oriented:
  - ✅ `GET /auth/login` (return Feishu authorization URL)
  - ✅ `GET /auth/callback` (handle Feishu OAuth callback)
- **Specialized operations**: When an operation doesn't map cleanly to CRUD:
  - ✅ `GET /contents/presigned-upload` (generate OSS upload URL)
  - ✅ `POST /search` (semantic search with embeddings)
- **When to use**: Operations that are transient, stateless, or represent business processes rather than resource state changes.
- **Documentation**: Clearly describe the action semantics in route `description`.

## Authentication Pattern

`get_current_user` dependency returns the `User` ORM model directly. Use `require_role()` factory for role-based access control:

```python
# Standard authenticated endpoint
@router.get("/{content_id}", response_model=ContentOut)
async def get_content_route(
    content_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ContentOut:
    content = await get_content(db, content_id)
    return ContentOut.from_domain(content)

# Role-restricted endpoint
@router.patch("/{user_id}/role", dependencies=[Depends(require_role(UserRole.admin))])
async def update_user_role(...):
    ...
```

**Critical rules:**
- `get_current_user` returns `User` ORM object (not just user_id).
- Access `current_user.id`, `current_user.role`, etc. directly.
- Use `require_role(UserRole.admin)` or `require_role(UserRole.reviewer, UserRole.admin)` in `dependencies` for restricted endpoints.
- No rate limiting infrastructure exists; do not add rate limiting dependencies.
- For public endpoints, use `limit_by_tier("default_public", scope="ip")`.
- Import schemas from the appropriate module:
  - Auth router: import from `app.schemas.user`
  - Content router: import from `app.schemas.content`

## Errors and Responses
- **Domain error mapping**: Use domain-specific `raise_<domain>_error()` functions from service façade:
  ```python
  from app.services.auth import FeishuOAuthError, raise_auth_error

  @router.get("/callback")
  async def feishu_callback(...):
      try:
          session = await login_with_code(db, command=FeishuLoginCommand(code=code))
      except FeishuOAuthError as exc:
          raise_auth_error(exc)
      return TokenOut.from_domain(session)
  ```
- When raising `HTTPException` directly, set `detail` to `{ "error_code": string, "message": string }` so the final body conforms to the unified error contract.
- Document every non-2xx/3xx outcome that the service can emit (per `raise_<domain>_error` or manual `HTTPException`). For each status, provide `example` (single) or `examples` (multiple) shaped with `error_code`, `message`.
- See [domain-errors](domain-errors.instructions.md) for exception definition and mapping conventions.

## Performance and Security
- Prefer validation in `schemas`; keep route-level checks minimal.
- Use dependencies for auth and auditing; never leak sensitive information.

## Documentation
- Maintain clear `summary/description`; add `example` when necessary to guide clients.
  - Summary principles
    - Concise verb-object phrasing
    - Highlight the primary function
  - Description principles
    - Explain the endpoint purpose and usage
    - List critical business rules
    - Note special parameter requirements
    - Describe possible return results
    - Use Markdown to improve readability
