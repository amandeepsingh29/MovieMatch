# Copilot / Agent Instructions — MovieMatch

Purpose: give an AI coding agent the minimal, actionable context to be productive here.

- Architecture (big picture):
  - Backend: FastAPI app defined in [backend/server.py](backend/server.py). API routes are mounted under `/api` (see `api_router`); WebSocket endpoint at `/api/ws/{room_code}`. Data is persisted in MongoDB via `motor` (env vars: `MONGO_URL`, `DB_NAME`). Collections used: `rooms`, `swipes`, `matches`.
  - Frontend: Create React App (CRACO) in [frontend](frontend). Entry: [frontend/src/index.js](frontend/src/index.js) and [frontend/src/App.js](frontend/src/App.js). Uses `axios`, `framer-motion`, `sonner`, `lucide-react`, Tailwind and `class-variance-authority` for component styling.
  - Dev tooling: frontend uses `craco` (do not call `react-scripts` directly); health endpoints for the dev server are implemented in [frontend/plugins/health-check/health-endpoints.js].

- Key runtime/config notes:
  - Backend expects a `.env` with `MONGO_URL` and `DB_NAME` (loadable by `dotenv` in [backend/server.py](backend/server.py)).
  - Frontend expects `REACT_APP_BACKEND_URL` to point at the backend (used to build `API` and `WS` URLs in [frontend/src/App.js](frontend/src/App.js)).
  - CORS origins are controlled by `CORS_ORIGINS` (backend defaults to `*` if unset).

- Important code patterns & conventions (project-specific):
  - UI components under [frontend/src/components/ui] use `cva` + `cn` patterns (see `button.jsx`) and Radix primitives. Follow existing variant patterns when adding components.
  - Visual/design rules are authoritative in [design_guidelines.json] — Dark mode only, use `Anton` for headings, `Manrope` for body, `sonner` for toasts, `lucide-react` for icons, and every interactive element should include `data-testid` attributes.
  - Local storage keys: `user_id` and `username` are written/read by the frontend; new features that rely on identity should use the same keys.
  - WebSocket usage: frontend constructs `WS_URL` by replacing http(s) with ws(s) then opens `/api/ws/{room}`; keep the `/api` prefix in mind when routing.
  - Backend uses Pydantic models (`Member`, `Room`, etc.) and async Motor calls; treat DB calls as async and prefer `await`.

- Testing & test protocol (required):
  - There is a strict testing protocol block at the top of [test_result.md](test_result.md). Main agent MUST update `test_result.md` before invoking any testing agent or running automated tests.
  - A sample tester is provided in `backend_test.py` (uses `requests`) — useful for integration tests against a running backend. Default base URL is set in that file; run with `python3 backend_test.py`.

- How to run locally (quick commands):
  - Backend (dev):
    - Ensure `backend/.env` exists with `MONGO_URL` and `DB_NAME`.
    - Start: `uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000 --env-file backend/.env`
  - Frontend (dev):
    - Install & run: `cd frontend && yarn install && REACT_APP_BACKEND_URL=http://localhost:8000 yarn start` (CRACO is used by the `start` script).
  - Run tests: update `test_result.md` per protocol, then run `python3 backend_test.py`.

- Integration & debugging tips:
  - If WebSocket fails, verify `REACT_APP_BACKEND_URL` scheme and that backend is reachable; frontend rewrites `http(s)` → `ws(s)` in code.
  - Check health endpoints in dev server at `/health` (see health plugin) for compile and webpack status when debugging frontend dev-server issues.
  - Inspect backend logs — `logging` is configured in [backend/server.py](backend/server.py).

- When editing code, follow these rules:
  - Keep design rules from [design_guidelines.json] consistent (fonts, color tokens, dark-only).
  - Add `data-testid` to any new interactive elements for tests and agent-driven QA.
  - Use the same storage keys (`user_id`, `username`) and API shape (room_code uppercase) to preserve interoperability.

If any of the above is unclear or you want me to expand examples (routes, tests, or a small runbook), tell me which area to expand. 
