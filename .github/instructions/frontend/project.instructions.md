---
applyTo: "frontend/src/**/*.ts, frontend/src/**/*.tsx, frontend/vite.config.ts, frontend/eslint.config.js, frontend/tsconfig*.json, frontend/package.json"
---
## Tech Stack
- **Runtime**: React 19 + TypeScript 5.9
- **Build**: Vite 8 with `@vitejs/plugin-react`
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite` plugin)
- **State**: Zustand 5 with `persist` middleware
- **HTTP**: Axios (single instance with interceptors)
- **Routing**: React Router v7
- **Icons**: `lucide-react` (available, use as needed)
- **UI Patterns**: [HyperUI](https://www.hyperui.dev/) — free Tailwind CSS component reference. Copy and adapt patterns; no npm package needed.
- **Lint**: ESLint 9 flat config + TypeScript ESLint + React Hooks/Refresh

## Scripts
| Command | Purpose |
|---------|---------|
| `npm run dev` | Start Vite dev server (port 5173, proxies `/api` → `localhost:8000`) |
| `npm run build` | TypeScript check + Vite production build → `dist/` |
| `npm run lint` | ESLint check |
| `npm run preview` | Preview production build locally |

## Project Structure
```
frontend/src/
├── assets/           # Static assets (images, SVGs)
├── components/       # Reusable UI components (grouped by domain/role)
│   ├── content/      #   ContentCard, ContentGrid, UploadForm
│   └── layout/       #   Layout, Sidebar
├── hooks/            # Custom React hooks (useAuth, useContent)
├── pages/            # Route entry points (one per route)
├── services/         # API client (axios instance)
├── store/            # Zustand stores (global state)
├── types/            # Shared TypeScript interfaces
├── App.tsx           # Router + route definitions
├── main.tsx          # React DOM entry point
├── index.css         # Tailwind import + CSS design tokens
└── App.css           # Legacy global styles
```

## Path Aliases
- `@/` → `src/` (configured in both `vite.config.ts` and `tsconfig.app.json`)
- Always use `@/` for project imports: `import { useAuth } from '@/hooks/useAuth'`

## TypeScript Settings
- **Strict mode** enabled
- `noUnusedLocals` and `noUnusedParameters` enabled
- Target: ES2023, Module: ESNext, JSX: react-jsx (automatic)
- No `any` in production code — define proper types

## Dev Proxy
Vite dev server proxies:
- `/api` → `http://localhost:8000` (backend API)
- `/bot` → `http://localhost:8000` (Feishu bot webhook)

No CORS handling needed in frontend — the proxy handles it.

## Import Order Convention
1. React / React DOM
2. Third-party libraries (react-router-dom, zustand, axios, etc.)
3. `@/` project imports (components, hooks, services, store, types)
4. Relative imports (siblings)
5. CSS imports

Type-only imports use `import type { ... }`.

## File Naming
| Category | Convention | Example |
|----------|-----------|---------|
| Components | PascalCase `.tsx` | `ContentCard.tsx` |
| Pages | PascalCase `.tsx` | `Dashboard.tsx` |
| Hooks | camelCase with `use` prefix `.ts` | `useAuth.ts` |
| Stores | camelCase `.ts` | `auth.ts` |
| Services | camelCase `.ts` | `api.ts` |
| Types | camelCase `.ts` | `index.ts` |

## Adding a New Feature Checklist
1. Define TypeScript types in `types/index.ts` (mirroring backend schemas)
2. Add API methods in a new hook (`hooks/useXxx.ts`) or extend existing hook
3. Create components in `components/<domain>/`
4. Create page in `pages/` composing components + hooks
5. Add route in `App.tsx` with appropriate auth guard
6. Add sidebar nav item in `Sidebar.tsx` (conditionally by role if needed)
7. Verify: `npm run build` passes with zero errors
