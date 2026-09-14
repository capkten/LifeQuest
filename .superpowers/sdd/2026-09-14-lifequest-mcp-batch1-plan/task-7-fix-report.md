# Task 7 Fix Report

Status: DONE

## Changed paths

- `docs/API.md`
- `deploy/install.sh`
- `deploy/nginx.conf`
- `backend/tests/test_mcp_auth.py`
- `.superpowers/sdd/2026-09-14-lifequest-mcp-batch1-plan/task-7-fix-report.md`

## Changes

- Documented the visible `Profile` page together with its `/profile` route.
- Updated revocation guidance to state that new or re-authenticated requests using the revoked token are rejected, and that clients with existing sessions must disconnect and reconnect after revocation.
- Added the installer-generated `/mcp/` Nginx proxy before the SPA fallback, targeting port 3001 with a trailing slash, streaming enabled via `proxy_buffering off`, and Authorization forwarding.
- Updated the tracked Nginx template to use the same trailing-slash prefix stripping and Authorization forwarding.
- Extended the documentation regression test with UTF-8, repository-root-resolved checks for the documentation and both deployment configurations.

## Tests run/results

- `cd backend && venv/bin/pytest tests/test_mcp_auth.py -k test_mcp_documentation_describes_token_configuration` before documentation/configuration changes: failed as expected on the missing `/profile` assertion (`1 failed, 14 deselected`).
- `cd backend && venv/bin/pytest tests/test_mcp_auth.py -k test_mcp_documentation_describes_token_configuration` after changes: `1 passed, 14 deselected`.
- `cd backend && venv/bin/pytest tests/test_mcp_auth.py tests/test_mcp_security.py tests/test_mcp_crud.py`: `36 passed`.
- `git diff --check`: passed.

## Concerns

No material implementation concerns. The backend test runs emit existing Python deprecation warnings from FastAPI, Starlette, and `jose`.
