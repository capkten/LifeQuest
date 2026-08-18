# LifeQuest Content Localization and UI Layout Verification

Date: 2026-08-18
Frontend: `http://127.0.0.1:5173`
Real Chrome headless screenshots: `%TEMP%\\LifeQuest-ui-check-20260818`

## Layout Fix

The only source changes are CSS rules in `Login.vue` and `Register.vue`. Both auth cards now explicitly use `min-width: 0` and `box-sizing: border-box`. This keeps the flex items shrinkable and keeps the existing `width: 100%` inside the mobile container padding without changing copy, keys, API calls, or component behavior.

## Browser Verification

Real Chrome headless was used at viewport sizes `375x900`, `768x900`, `1024x900`, and `1440x900`. Each check captured a PNG and evaluated `document.documentElement.scrollWidth`, `document.documentElement.clientWidth`, and the final URL.

Public pages: 8 checks total. Login and Register both rendered at all four viewports with no horizontal overflow. At 375px, each card was `343px` wide from `x=16` to `right=359`; at 768px, 1024px, and 1440px, each card remained `420px` wide.

Protected routes: 52 route/viewport checks total. Every unauthenticated check redirected to the Login page while preserving the requested route in the `redirect` query parameter. Every check had `scrollWidth === clientWidth`:

| Route | 375px | 768px | 1024px | 1440px |
| --- | --- | --- | --- | --- |
| `/` | `/login?redirect=/`, 375/375 | `/login?redirect=/`, 768/768 | `/login?redirect=/`, 1024/1024 | `/login?redirect=/`, 1440/1440 |
| `/todos` | `/login?redirect=/todos`, 375/375 | `/login?redirect=/todos`, 768/768 | `/login?redirect=/todos`, 1024/1024 | `/login?redirect=/todos`, 1440/1440 |
| `/cultivation` | `/login?redirect=/cultivation`, 375/375 | `/login?redirect=/cultivation`, 768/768 | `/login?redirect=/cultivation`, 1024/1024 | `/login?redirect=/cultivation`, 1440/1440 |
| `/world` | `/login?redirect=/world`, 375/375 | `/login?redirect=/world`, 768/768 | `/login?redirect=/world`, 1024/1024 | `/login?redirect=/world`, 1440/1440 |
| `/sects` | `/login?redirect=/sects`, 375/375 | `/login?redirect=/sects`, 768/768 | `/login?redirect=/sects`, 1024/1024 | `/login?redirect=/sects`, 1440/1440 |
| `/techniques` | `/login?redirect=/techniques`, 375/375 | `/login?redirect=/techniques`, 768/768 | `/login?redirect=/techniques`, 1024/1024 | `/login?redirect=/techniques`, 1440/1440 |
| `/npcs` | `/login?redirect=/npcs`, 375/375 | `/login?redirect=/npcs`, 768/768 | `/login?redirect=/npcs`, 1024/1024 | `/login?redirect=/npcs`, 1440/1440 |
| `/tribulations` | `/login?redirect=/tribulations`, 375/375 | `/login?redirect=/tribulations`, 768/768 | `/login?redirect=/tribulations`, 1024/1024 | `/login?redirect=/tribulations`, 1440/1440 |
| `/notes` | `/login?redirect=/notes`, 375/375 | `/login?redirect=/notes`, 768/768 | `/login?redirect=/notes`, 1024/1024 | `/login?redirect=/notes`, 1440/1440 |
| `/shop` | `/login?redirect=/shop`, 375/375 | `/login?redirect=/shop`, 768/768 | `/login?redirect=/shop`, 1024/1024 | `/login?redirect=/shop`, 1440/1440 |
| `/backpack` | `/login?redirect=/backpack`, 375/375 | `/login?redirect=/backpack`, 768/768 | `/login?redirect=/backpack`, 1024/1024 | `/login?redirect=/backpack`, 1440/1440 |
| `/finance` | `/login?redirect=/finance`, 375/375 | `/login?redirect=/finance`, 768/768 | `/login?redirect=/finance`, 1024/1024 | `/login?redirect=/finance`, 1440/1440 |
| `/profile` | `/login?redirect=/profile`, 375/375 | `/login?redirect=/profile`, 768/768 | `/login?redirect=/profile`, 1024/1024 | `/login?redirect=/profile`, 1440/1440 |

The protected-route screenshots therefore show the public Login state, not the requested authenticated content. No authenticated browser session was available, so authenticated content states, API-backed data, and post-login layouts were not visually checked and are not claimed as checked in this report.

## Automated Verification

- `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q`
  - `215 passed`, `1 failed`, `419 warnings` in 140.81s.
  - Failure: `tests/test_cultivation.py::test_npc_cultivation_updates_once_per_natural_day`; the test expects fixed date `2026-08-17`, while the service returned the current date `2026-08-18`. No backend file was changed because this task is scoped to auth-page CSS and this report.
  - Warnings are existing Starlette/httpx, FastAPI `on_event`, and `datetime.utcnow()` deprecations.
- `cd frontend; node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/cultivation-regressions.test.mjs src/views/localization-regressions.test.mjs`
  - `52 passed`, `0 failed`, `0 warnings`.
- `cd frontend; npm run build`
  - Vite build succeeded with exit code 0.
  - Warnings: npm `always-auth` config warning, 2 Rollup PURE-annotation warnings, and 1 chunk-size warning for the minified main chunk over 500 kB.
- `git diff --check`
  - No whitespace errors.

## Scope and Concerns

- The source scope is limited to the required CSS rules in `frontend/src/views/Login.vue` and `frontend/src/views/Register.vue`.
- The 52 protected-route checks are authentication-gated redirects; they must not be interpreted as authenticated content checks.
- The backend suite has one pre-existing/time-sensitive date assertion failure unrelated to this CSS change and remains unchanged.
