---
applyTo: "frontend/src/store/*.ts, frontend/src/services/*.ts, frontend/src/hooks/*.ts"
---
## Architecture Overview
```
store/    → Zustand global state (auth, persisted data)
services/ → Axios API client (single instance, interceptors)
hooks/    → Custom React hooks (bridge between components and store/services)
```

Components consume data exclusively through **hooks**; hooks call **services** and **stores** internally.

## Zustand Stores (`store/`)

### Design Rules
- One store per domain: `auth.ts` (auth state), add `content.ts`, `ui.ts` etc. as needed.
- Export the hook directly: `export const useAuthStore = create<AuthState>()(...)`.
- Use `persist` middleware for state that survives page reload (e.g., auth token).
- Keep store state minimal — only truly global state. Prefer local `useState` for page-scoped state.

### Store Pattern
```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types'

interface AuthState {
  token: string | null
  user: User | null
  setAuth: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => {
        localStorage.setItem('access_token', token)
        set({ token, user })
      },
      logout: () => {
        localStorage.removeItem('access_token')
        set({ token: null, user: null })
      },
    }),
    { name: 'auth-storage' },
  ),
)
```

### Token Storage
- JWT stored in both Zustand (for reactivity) and `localStorage` (for interceptor access).
- `setAuth()` writes to both; `logout()` clears both.
- The axios interceptor reads `access_token` from `localStorage` directly (not from React state).

## API Service (`services/api.ts`)

### Singleton Axios Instance
- **Base URL**: `/api/v1` (Vite proxy forwards to backend in dev).
- **Timeout**: 30 seconds.
- All API calls go through this single instance — never create separate axios instances.

### Interceptors
- **Request**: Injects `Authorization: Bearer <token>` from `localStorage`.
- **Response (error)**: On `401`, clears token and redirects to `/login`.

### API Call Conventions
- Use typed generics: `api.get<ContentListOut>(...)`, `api.post<Content>(...)`.
- Return `data` from responses in hooks — don't return raw AxiosResponse to components.
- All API types come from `@/types` — keep them in sync with backend `schemas/`.

### Error Handling
- Interceptor handles 401 globally.
- Other errors propagate to hooks via `Promise.reject()`.
- Hooks catch errors and expose `error` state; components display error UI.

## Custom Hooks (`hooks/`)

### Naming
- Prefix with `use`: `useAuth`, `useContent`, `useSearch`, etc.
- One hook per domain file.

### Hook Structure Pattern
```typescript
import { useCallback, useState } from 'react'
import api from '@/services/api'
import type { Content, ContentListOut } from '@/types'

export function useContent() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const listContents = useCallback(async (params?: ListParams): Promise<ContentListOut> => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<ContentListOut>('/contents', { params })
      return data
    } catch (e: any) {
      setError(e.message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  return { loading, error, listContents, /* other methods */ }
}
```

### Hook Design Rules
- **Return loading/error state** for data-fetching hooks.
- **Wrap methods in `useCallback`** to provide stable references for `useEffect` deps.
- **Delegate to api service** — hooks never use `fetch()` or construct URLs manually.
  - Exception: `useAuth.loginWithCode()` uses `fetch()` for the OAuth callback (runs before axios interceptor is configured). Migrate to `api` when feasible.
- **Don't manage UI state** (modals, selections) — that belongs in components with `useState`.
- **One hook = one domain**: `useContent` for content CRUD, `useAuth` for authentication.

### Store vs Hook
| Concern | Store (`store/`) | Hook (`hooks/`) |
|---------|------------------|-----------------|
| Scope | Global, persisted | Per-component lifecycle |
| Examples | Auth token, user profile | API loading/error, fetch functions |
| Reactivity | Zustand selectors | React state/effects |
| Side effects | Minimal (set/clear) | API calls, navigation |

## Dependency Direction
```
components/pages → hooks → store + services
                           ↓
                         types
```
- **Components** import from `hooks/` (and possibly `store/` for simple selectors).
- **Hooks** import from `store/`, `services/api`, and `types/`.
- **Services** import from `types/` only (no React dependency).
- **Stores** import from `types/` only (no React dependency beyond zustand).
