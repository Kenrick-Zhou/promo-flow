---
applyTo: "frontend/src/**/*.tsx, frontend/src/**/*.css"
---
## Framework
- **Tailwind CSS v4** via `@tailwindcss/vite` plugin — no `tailwind.config.js` needed.
- Utility-first approach: style directly in JSX `className`.
- CSS utilities: `tailwind-merge`, `clsx`, `class-variance-authority` (CVA) available.

## CSS Architecture
```
src/
├── index.css     → Tailwind import + CSS custom properties (design tokens, dark mode)
└── App.css       → Legacy/global component styles (minimize usage)
```

### Design Tokens (`index.css`)
Custom properties define the color palette and typography with automatic dark mode:
```css
:root {
  --text: #6b6375;          /* Body text */
  --text-h: #08060d;        /* Headings */
  --bg: #fff;               /* Page background */
  --border: #e5e4e7;        /* Borders */
  --accent: #aa3bff;        /* Brand purple */
  --accent-bg: rgba(170, 59, 255, 0.1);
  --sans: system-ui, 'Segoe UI', Roboto, sans-serif;
}

@media (prefers-color-scheme: dark) {
  :root { /* dark overrides */ }
}
```
- Use CSS vars for theming when Tailwind classes are insufficient.
- Prefer Tailwind color classes (`text-gray-900`, `bg-purple-600`) over raw CSS vars in components.

## Styling Conventions

### Tailwind First
- Apply styles via Tailwind utilities in `className`. Avoid inline `style={{}}`.
- Use responsive prefixes: `sm:`, `md:`, `lg:` for breakpoints.
- Use state prefixes: `hover:`, `disabled:`, `focus:` for interactions.

### Common Patterns
```tsx
// Responsive grid
<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">

// Card container
<div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">

// Form input
<input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />

// Primary button
<button className="bg-purple-600 text-white py-2 px-5 rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50">

// Status badge
<span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
```

### Brand Colors
| Usage | Class |
|-------|-------|
| Primary action | `bg-purple-600 hover:bg-purple-700` |
| Primary text accent | `text-purple-600`, `text-purple-700` |
| Active nav item | `bg-purple-50 text-purple-700` |
| Feishu login button | `bg-blue-500 hover:bg-blue-600` |
| Approve action | `bg-green-500 hover:bg-green-600` |
| Reject action | `bg-red-500 hover:bg-red-600` |
| Pending badge | `bg-yellow-100 text-yellow-700` |

### Dynamic Classes
Use `clsx` or template literals for conditional classes:
```tsx
import { clsx } from 'clsx'

<Link className={clsx(
  'flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors',
  isActive ? 'bg-purple-50 text-purple-700' : 'text-gray-700 hover:bg-gray-100',
)} />
```

For component variants, use `class-variance-authority` (CVA):
```tsx
import { cva } from 'class-variance-authority'

const badge = cva('text-xs px-2 py-0.5 rounded-full', {
  variants: {
    status: {
      pending: 'bg-yellow-100 text-yellow-700',
      approved: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
    },
  },
})
```

## UI Language
- All user-visible text in **中文** (Chinese).
- Use `zh-CN` locale for date formatting: `new Date(iso).toLocaleDateString('zh-CN')`.

## Layout Structure
- App shell: `flex min-h-screen bg-gray-50`.
- Sidebar: `w-56 shrink-0 border-r` — fixed width, sticky.
- Main content: `flex-1 p-6 overflow-auto`.

## What to Avoid
- No custom CSS files per component — use Tailwind classes.
- No `!important` — restructure class order or use `tailwind-merge` for conflicts.
- No hardcoded pixel values for spacing — use Tailwind spacing scale (e.g., `p-4` not `padding: 16px`).
- Don't mix Tailwind and `style={{}}` on the same element unless for truly dynamic values (e.g., computed widths).
