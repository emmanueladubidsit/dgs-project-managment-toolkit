# ADR 0003 — Client-rendered pages with TanStack Query on Next.js 16

- **Status:** Accepted · 21 November 2026

## Context

Next.js 16.4 ships with Cache Components and Partial Prefetching enabled. All data comes from the
local FastAPI service, and almost every page depends on “today”.

## Decision

- Pages are Client Components that fetch through TanStack Query. Every mutation invalidates all
  queries — trivially consistent for a single-user app with small data.
- The page area renders browser-only through React 19.3 `use(browser())` inside a Suspense
  boundary, as the bundled Next.js SPA guide recommends, so prerendered HTML never contains a
  build-time date.
- Components that call `usePathname` sit inside Suspense because `/projects/[id]` has a dynamic
  param (otherwise the build fails under Cache Components).

## Consequences

- No server-side data fetching or caching to reason about; the backend remains the single source
  of truth. Initial HTML is a loading skeleton (acceptable for a local tool; SEO irrelevant).
- If the app is later hosted, Server Components can be introduced per page without changing the API.
