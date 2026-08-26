# Repository Guidelines

## Project Structure & Module Organization
This repository is split into two main apps:

- `backend/`: FastAPI application code in `backend/app/`, tests in `backend/tests/`, and runtime data such as `backend/uploads/` and `backend/notes_data/`.
- `frontend/`: Vue 3 app in `frontend/src/`, with views in `frontend/src/views/`, shared UI in `frontend/src/components/`, routes in `frontend/src/router/`, and API wrappers in `frontend/src/services/`.
- `docs/`: planning and design notes, including `docs/superpowers/`.

Keep new code close to the feature it serves. Prefer small, focused modules over cross-cutting files.

## Build, Test, and Development Commands
Run commands from the relevant subdirectory:

- `cd backend && pip install -r requirements.txt`: install Python dependencies.
- `cd backend && pytest`: run the backend test suite.
- `cd backend && uvicorn app.main:app --reload`: start the API locally.
- `cd frontend && npm install`: install frontend dependencies.
- `cd frontend && npm run dev`: start the Vite dev server.
- `cd frontend && npm run build`: create a production frontend build.

## Coding Style & Naming Conventions
Use the existing style in each stack:

- Python: 4-space indentation, `snake_case` for functions and modules, `PascalCase` for classes and Pydantic models.
- Vue/JavaScript: `PascalCase.vue` for components when appropriate, `camelCase` for variables and composables, and feature-based filenames such as `note.js` or `useUserStats.js`.
- Keep files readable and narrowly scoped. Add brief comments only when logic is not obvious.

No formatter or linter is configured in the repo, so match the surrounding code and avoid unrelated reformatting.
Read and write text files with UTF-8 encoding only. When creating or editing files, keep the encoding explicit to avoid mojibake, especially for Markdown, Python, and Vue source files.

## Testing Guidelines
Backend tests use `pytest` and live in `backend/tests/` with names like `test_auth.py` and `test_todos.py`. Add new tests alongside the feature they cover and keep fixtures in `backend/tests/conftest.py` when shared setup is needed. The frontend currently has no automated test runner configured; verify UI changes with `npm run build` and manual browser checks.

## Commit & Pull Request Guidelines
Git history uses short conventional prefixes such as `feat:`, `feat(profile):`, `chore(frontend):`, and `fix(config):`. Keep commit subjects imperative and scoped when useful.

Pull requests should include:

- a short summary of the change and affected area
- linked issue or task, if available
- screenshots or short recordings for visible UI changes
- notes about any new environment variables or database changes

## Security & Configuration Tips
Do not commit secrets. Use `.env.example` as the template for local configuration, and keep generated databases, uploads, and other runtime artifacts out of version control.

## LifeQuest Project Rules

- The project version has one source of truth: the repository-root `VERSION` file. Do not hardcode the application version in backend, frontend, UI, Android metadata, or CI release metadata.
- When a release or user-visible application change requires a version increment, update `VERSION` first. The version is semantic and should be incremented from the current version (currently `1.8.3`); then run `cd frontend && npm run sync:version` so `frontend/package.json` and `frontend/package-lock.json` stay synchronized.
- Before committing a version change, run `cd frontend && npm run check:version` and `npm run build`. The backend reads the same root `VERSION`, and the frontend UI reads the injected build version from that source.
- Android `versionName` must read the root `VERSION`. Android `versionCode` is a separate monotonically increasing integer used by Android and must be incremented for each Android package release; it must not replace or override the project version.
- A push to `main` that changes `VERSION`, `frontend/**`, or the relevant workflow files is expected to trigger both GitHub Actions workflows: `Test and Deploy` and `Build Android Release`. Do not treat a merely triggered workflow as complete; verify the final conclusion is `success`.
- A successful Android release must create a GitHub Release with the project version in its name/tag and include `app-release.apk`, `app-release.aab`, and `latest.json`. A successful deployment must be confirmed by the deployment workflow and, when practical, an HTTP health check against the live site.
- Daily habits are completed at most once per China calendar day (`Asia/Shanghai`). Completion checks and persistence must use the same China-local date boundary, so repeated clicks on the same day cannot create repeated completions.
- Keep existing user changes in the working tree, especially unrelated files under `docs/superpowers/`; stage only files belonging to the requested change.
