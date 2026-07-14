# Expense Tracker Frontend — Design

## Goal
Add a React (Vite) frontend for the existing Flask Expense Tracker API, styled in a minimalist editorial visual language.

## Backend additions (small, precede frontend work)
- `PATCH /categories/<id>`: rename. 404 if not found/not owned. 409 if the new name collides with another of the caller's categories (same rule as create).
- `DELETE /categories/<id>`: 404 if not found/not owned. `RecurringRule.category_id` is `ON DELETE RESTRICT`, so deleting a category still referenced by a recurring rule raises an `IntegrityError` — catch it and return 409 with `{"error": "category is used by a recurring rule"}` instead of a raw 500.
- Add `flask-cors`, configured to allow the Vite dev origin, so the browser can call the Flask API directly in dev (no proxy).
- Tests for both new endpoints, following the existing test patterns in `tests/test_categories.py`.

## Frontend stack
- React + Vite, JavaScript (no TS, to match project's lack of existing type tooling).
- React Router for the 5 pages.
- Plain `fetch` wrapped in a single `apiFetch(path, opts)` helper: attaches `Authorization: Bearer <token>`, parses JSON error bodies into thrown errors, and redirects to `/login` on 401. No React Query / SWR / global store — the data volume and page count don't warrant one.
- Auth: `useAuth` hook stores the JWT in `localStorage`, exposes `login`, `register`, `logout`, `token`.
- Per-page data hooks (`useTransactions`, `useCategories`, `useRecurringRules`) each wrap `apiFetch` calls for their resource; each page refetches on mount and after mutations. No cross-page cache.
- Styling: minimalist editorial (warm monochrome, typographic hierarchy, flat cards, no gradients/shadows), per the `minimalist-ui` skill. Dashboard chart follows the `dataviz` skill's palette/form guidance.

## Pages
1. **Login / Register** — single route, toggles between the two modes; posts to `/auth/login` or `/auth/register`, stores the returned token, redirects to Dashboard.
2. **Dashboard** — current-month view: total spend, a spend-by-category chart sourced from `GET /transactions/summary?month=YYYY-MM`, and a short recent-transactions list (reuses the transactions hook with `limit=5`).
3. **Transactions** — paginated list (`GET /transactions`) with month/category filters; add via form; edit/delete inline per row.
4. **Categories** — list (`GET /categories`); add via form; rename via inline `<input>` that PATCHes on blur; delete with inline error message on 409 (used-by-recurring-rule case) rather than a modal/toast.
5. **Recurring Rules** — list (`GET /recurring-rules`); add/edit/delete form (category, amount, frequency, start/end date).

## Error handling
- Centralized in `apiFetch`: non-2xx responses throw an `ApiError` carrying the parsed `{error}` message and status; 401 clears the stored token and redirects to `/login`.
- Each page/form catches `ApiError` locally and renders the message inline near the relevant control (no global toast system).

## Out of scope for v1
- Historical trend charts (the summary endpoint has no time-series shape today — would need a new endpoint).
- Real-time updates / websockets.
- Multi-user admin views.
