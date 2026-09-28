# Contributing to DroppedNeedle
INFO:     172.18.0.3:43916 - "GET /api/v1/downloads/activity-summary HTTP/1.1" 200 OK
2026-09-27 23:24:32,211 - services.version_service - WARNING - Invalid version comparison: v2.15.0 vs dev-6227b7a
INFO:     172.18.0.3:43954 - "GET /api/v1/requests/pending-approvals/count HTTP/1.1" 200 OK
INFO:     172.18.0.3:43850 - "GET /api/v1/version/check-update HTTP/1.1" 200 OK
INFO:     172.18.0.3:43876 - "GET /api/v1/version/releases HTTP/1.1" 200 OK
INFO:     172.18.0.3:43910 - "GET /api/v1/playlists/f07c3dea-82a9-4d60-8010-1b4e4f37a089 HTTP/1.1" 200 OK
INFO:     172.18.0.3:43818 - "POST /api/v1/playlists/f07c3dea-82a9-4d60-8010-1b4e4f37a089/resolve-sources HTTP/1.1" 200 OK
INFO:     172.18.0.3:43984 - "GET /api/v1/me/scrobble-preferences HTTP/1.1" 200 OK
INFO:     172.18.0.3:43780 - "GET /api/v1/library/activity/stream HTTP/1.1" 200 OK
INFO:     172.18.0.3:43794 - "GET /api/v1/library/operations/stream HTTP/1.1" 200 OK
2026-09-27 23:24:33,972 - middleware - WARNING - Slow request: POST /api/v1/playlists/f07c3dea-82a9-4d60-8010-1b4e4f37a089/match-library took 2.31s
INFO:     172.18.0.3:43832 - "POST /api/v1/playlists/f07c3dea-82a9-4d60-8010-1b4e4f37a089/match-library HTTP/1.1" 200 OK
INFO:     172.18.0.3:44004 - "POST /api/v1/playlists/f07c3dea-82a9-4d60-8010-1b4e4f37a089/request-missing HTTP/1.1" 202 Accepted
2026-09-27 23:24:34,021 - middleware - WARNING - Slow request: GET /api/v1/me/section-prefs took 2.14s
INFO:     172.18.0.3:43940 - "GET /api/v1/me/section-prefs HTTP/1.1" 200 OK
2026-09-27 23:24:34,052 - middleware - WARNING - Slow request: GET /api/v1/library/activity took 2.24s
INFO:     172.18.0.3:43988 - "GET /api/v1/library/activity HTTP/1.1" 200 OK
Thanks for your interest. Bug reports, feature requests, and pull requests are all welcome.

## Reporting bugs

Use the [bug report template](https://github.com/DroppedNeedle/DroppedNeedle/issues/new?template=bug.yml). Include your DroppedNeedle version, steps to reproduce, and relevant logs from `docker compose logs droppedneedle`. The more detail you give, the faster things get fixed.

## Requesting features

Use the [feature request template](https://github.com/DroppedNeedle/DroppedNeedle/issues/new?template=feature.yml). Check existing issues first to avoid duplicates.

## Development setup

The backend is Python 3.13 with FastAPI. The frontend is SvelteKit with Svelte 5, Tailwind CSS, and daisyUI.

### Prerequisites

- Python 3.13+
- Node.js 22+
- Docker (for building the full image)

### Running locally

Backend:

```bash
cd backend
pip install -r requirements-dev.txt
cp env.dev.example .env
uvicorn target_main:app --reload --port 8688
```

Frontend:

```bash
cd frontend
cp env.development.example .env.development
pnpm install
pnpm run dev
```

### Running tests

```bash
make backend-test          # backend suite
make frontend-test         # frontend server and browser suites
make frontend-test-server  # frontend server suite only
make frontend-test-client  # frontend browser suite only
make test                  # backend and frontend server suites; excludes browser tests
```

Frontend browser tests use Playwright. Install the browser first:

```bash
make frontend-browser-install
```

## Pull requests

1. Fork the repo and create a branch from `main`.
2. Give your branch a descriptive name: `fix-scrobble-timing`, `feature-playlist-export`, etc.
3. If you're fixing a bug, mention the issue number in the PR description.
4. Make sure tests pass before submitting.
5. Keep changes focused. One PR per fix or feature.

## Code style

- Backend: strong typing, async/await, no blocking I/O in async contexts.
- Frontend: strict TypeScript, no `any`. Named exports. Async/await only.
- Use existing design tokens (`primary`, `secondary`, etc.) for colours, not hardcoded values.
- Run `pnpm run lint` and `pnpm run check` in the frontend before submitting.

## AI-assisted contributions

If you used AI tools (Copilot, ChatGPT, Claude, etc.) to write code in your PR, please mention it. This isn't a problem and won't get your PR rejected, but it helps reviewers calibrate how much scrutiny to apply. A quick note like "Claude helped with the caching logic" is enough.

You're still responsible for understanding and testing the code you submit.

## Questions?

Open a thread in [Discord](https://discord.gg/B5suDg7gu2) or start a [GitHub Discussion](https://github.com/DroppedNeedle/DroppedNeedle/discussions).
