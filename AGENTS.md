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
