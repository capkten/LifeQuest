# LifeQuest stability, workbench, and habits verification

Date: 2026-09-12 UTC
Implementation head before Task 7: `d61b9c47ba5346ca2d5d953783f0e61d3c4d2336`
Candidate version during this report's initial write: `1.13.0`
Durable evidence root: `/home/capkin/apps/LifeQuest/.superpowers/sdd/2026-09-12-lifequest-stability-workbench-habits/evidence-2026-09-12`

## Result before release metadata changes

The Tasks 1-6 implementation, FEAT-01 browser matrix, FEAT-02 browser matrix, China-midnight matrix, four required viewports, focus behavior, no-resubmission behavior, conflict handling, stale-history handling, and overflow checks passed locally. The midnight check exposed one real habit-history initialization defect; `HabitHistoryDialog` now initializes leave and backfill models when it mounts already visible, and a focused frontend regression test protects that lifecycle.

The report was written before changing roadmap or Harness completion states, as required. The version synchronization and final post-edit gate are recorded in the release addendum after they run.

## Automated gates

Initial pre-version gate:

```text
cd backend && venv/bin/pytest
404 passed, 952 warnings in 119.31s

cd frontend && npm test
154 passed, 0 failed

cd frontend && npm run build
2031 modules transformed; build succeeded
index: 1,050.71 kB (gzip 360.84 kB)
element-plus: 1,069.31 kB (gzip 335.40 kB)
Rollup emitted the existing >500 kB chunk warning.

git diff --check
exit 0; no output
```

Candidate gate after the browser-discovered lifecycle fix:

```text
cd backend && venv/bin/pytest
404 passed, 952 warnings in 119.73s

cd frontend && npm test
155 passed, 0 failed in 883 ms

cd frontend && npm run build
2031 modules transformed; built in 10.87s
index: 1,050.71 kB (gzip 360.84 kB)
element-plus: 1,069.31 kB (gzip 335.40 kB)

git diff --check
exit 0; no output
```

The warnings consist primarily of FastAPI/Starlette/python-jose deprecations, two Pydantic alias warnings in a finance test, Rollup's dependency annotation notice, and the existing bundle-size warning. No test or build failed.

## Isolation and account

- Core frontend: `http://127.0.0.1:5173`
- Core backend API: `http://127.0.0.1:18000/api`
- Isolated runtime root: `/tmp/lifequest-task7-ohFk1z`
- Isolated SQLite database: `/tmp/lifequest-task7-ohFk1z/browser.sqlite`
- The backend ran from `/tmp/lifequest-task7-ohFk1z/backend`, which isolated the hard-coded notes and uploads paths.
- Existing unrelated services on ports 8000, 8001, and 3002 were not modified.
- Real registration and login used unique username `t7_235904811` and email `t7_235904811@example.com`; credentials are omitted. A prior `example.test` registration was actually observed as HTTP 422, while `example.com` registered with HTTP 200.
- The core run used Chromium with browser timezone `America/Los_Angeles`; China date behavior came from application code and server responses.
- The weekly-target habit's `created_at` was adjusted only in the isolated SQLite fixture to `2026-09-07 00:00:00.000000`, making three historical dates in that week eligible for the requested backfill/capacity matrix.

## FEAT-01 browser evidence

The core browser harness is `core-browser-verification.cjs`; structured results and requests are `core-browser-results.json` and `core-request-log.json`. The run observed 155 logged responses: 146 HTTP 200, seven logged HTTP 409 entries representing four logical conflicts, and two deliberately injected HTTP 503 responses.

| Action | Observed result | Durable artifact |
| --- | --- | --- |
| Register, login, render first workbench viewport | register 200; login 200 | `01-registration-login-home.png` |
| Create today, unscheduled, and specified-date tasks; render today/overdue/unscheduled/upcoming groups | four 200 responses; specified date `2026-09-16` | `02-workbench-three-schedules-and-groups.png` |
| Select and reorder three focus tasks | PUT 200; visible order unscheduled, today, upcoming | `03-focus-three-selection-order.png` |
| Complete a focused task with reward refresh forced to 503 | one completion POST/200; task stayed completed; coin balance stabilized; visible warning said the action was saved and must not be resubmitted | `04-completed-focus-no-resubmission-warning.png` |
| Complete tasks from each of four groups | today/overdue/unscheduled/upcoming each 200 | `core-request-log.json` |
| Reuse a request ID with changed content | 409, visible/server detail requires a new creation request | `core-request-log.json` |
| Save a stale focus revision | external PUT 200, stale UI PUT 409, draft retained with visible conflict text | `05-focus-stale-revision-conflict.png` |
| Force workbench refresh failure | forced 503 retained prior task; retry 200 recovered | `06-workbench-refresh-failure-preserves-data.png` |
| Force initial workbench load failure | forced 503 showed retry state; retry 200 rendered data | `07-workbench-initial-load-failure.png` |

Viewport observations were made at China date `2026-09-13`, during `2026-09-12T17:58:35Z` through `2026-09-12T17:58:37Z` (`2026-09-13 01:58:35` through `01:58:37` China time):

| Viewport | scroll/client width | Focus | Heading | Artifact |
| --- | --- | --- | --- | --- |
| 1440x900 desktop wide | 1440/1440 | title input, 2px solid outline | first viewport | `12-desktop-wide-workbench-focus.png` |
| 1024x768 desktop narrow | 1024/1024 | title input, 2px solid outline | first viewport | `12-desktop-narrow-workbench-focus.png` |
| 390x844 mobile | 390/390 | title input, 2px solid outline | first viewport | `12-mobile-390-workbench-focus.png` |
| 375x812 project reference | 375/375 | title input, 2px solid outline | first viewport | `12-reference-375-workbench-focus.png` |

For page-level peer overlap checks, the scope is every visible `button`, `input`, `select`, `textarea`, and link except descendants of the intentional fixed `.bottom-nav`. The nav exclusion prevents the fixed navigation overlay from being compared with partially offscreen page controls; content controls remain fully checked. Every viewport had zero content-peer overlaps and zero horizontal overflow.

## FEAT-02 browser evidence

| Action | Observed result | Durable artifact |
| --- | --- | --- |
| Create daily, specified-weekday, and weekly-target habits | three POST/200 responses; weekday badge visibly used the UI contract `指定日期`; weekly target showed `本周 0/3` | `08-habit-daily-weekday-weekly-target.png` |
| Pause and resume | 200 then 200 | `core-request-log.json` |
| Create and revoke leave `[2026-09-13, 2026-09-14)` | 200 then 200 | `core-request-log.json` |
| Complete with note and inspect heatmap | completion 200; exact note present in day title; one factual completed day | `09-habit-note-history-heatmap.png` |
| Fill weekly target using three backfills | three 200 responses; Todos `本周 3/3`; History `3/3 个计划槽位` | `10-weekly-target-3-of-3-capacity.png` |
| Attempt fourth normal completion | 409; completion count stayed 3; no coin or experience increase | `core-request-log.json` |
| Attempt fourth backfill | 409; completion count stayed 3; no coin or experience increase | `core-request-log.json` |
| Open habit B while habit A history is delayed 900 ms | habit B remained visible after A completed | `11-stale-history-second-habit-wins.png` |
| Mobile history focus and overflow | 390/390 width; focused backfill date had solid outline; dialog left/right 8/382 | `13-mobile-390-history-overflow-focus.png` |

## China-midnight browser evidence

SQLite's backup API copied the completed core fixture to `/tmp/lifequest-task7-ohFk1z/before.sqlite` and `/tmp/lifequest-task7-ohFk1z/after.sqlite`. `fixed-clock-backend.py` patched only the imported clock globals used by daily workbench, finance, and Todo services. `midnight-browser-verification.cjs` fixed browser `Date`, kept browser timezone `America/Los_Angeles`, logged every API response, and ran the real Vue UI.

Services and instants:

| UTC instant | China-local instant | Frontend | Backend API |
| --- | --- | --- | --- |
| `2026-09-11T15:59:59Z` | `2026-09-11 23:59:59 +08:00` | `http://127.0.0.1:5174` | `http://127.0.0.1:18001/api` |
| `2026-09-11T16:00:00Z` | `2026-09-12 00:00:00 +08:00` | `http://127.0.0.1:5175` | `http://127.0.0.1:18002/api` |

The final run passed 24/24 assertions. `midnight-request-log.json` contains 148 responses, all HTTP 200.

| Check | 23:59:59 observation | 00:00:00 observation | Artifacts |
| --- | --- | --- | --- |
| Server-authoritative workbench | response/UI date `2026-09-11` | response/UI date `2026-09-12` | `14-before-workbench-date.png`, `14-after-workbench-date.png` |
| Finance new-transaction default | `2026-09-11` | `2026-09-12` | `15-before-finance-default-date.png`, `15-after-finance-default-date.png` |
| Transaction grouping | 9/11=`今天`, 9/12=`9月12日周六` | 9/12=`今天`, 9/11=`昨天` | `16-before-finance-grouping.png`, `16-after-finance-grouping.png` |
| Debt payment default | `2026-09-11` | `2026-09-12` | `17-before-debt-payment-date.png`, `17-after-debt-payment-date.png` |
| Calendar month/today | `2026年9月`, marker 11 | `2026年9月`, marker 12 | `18-before-calendar-today.png`, `18-after-calendar-today.png` |
| Leave defaults | start 9/11, return 9/12 | start 9/12, return 9/13 | `19-before-habit-history-defaults.png`, `19-after-habit-history-defaults.png` |
| Backfill defaults/max | 9/10 | 9/11 | same history artifacts |

At each fixed instant, workbench geometry also passed at 1440x900, 1024x768, 390x844, and 375x812; screenshots are `20-{before|after}-{desktop-wide|desktop-narrow|mobile-390|reference-375}-workbench.png`. Each had `scrollWidth == clientWidth`, zero content-control overlaps, a visible 2px focus outline, and the heading inside the first viewport.

Mobile history passed at both instants with viewport 390x844, page width 390/390, focused `habit-backfill-date` with a 2px solid outline, dialog bounds left 8/right 382, and zero in-dialog control overlaps. Artifacts are `21-before-mobile-history.png` and `21-after-mobile-history.png`. While a modal is active, overlap peers are scoped to visible controls inside `.history-dialog`; background controls covered by the modal overlay are intentionally not peers. Document width, focus, dialog bounds, and every in-dialog control remain asserted.

## Failed attempts retained

- `midnight-attempt-1.log`: old token rejected because the first fixed services used new signing secrets.
- `midnight-attempt-2.log`: current ignored `.env` still differed from the original isolated runtime secret.
- `midnight-attempt-3.log` plus result/request JSON: six pre-midnight flows passed; a future-created daily fixture produced history 422 and the date model was read before initialization.
- `midnight-attempt-4.log` plus result/request JSON: deterministic diagnostics proved the visible-mounted dialog left all model values empty despite correct China date/min/max values; this exposed the real lifecycle bug.
- `midnight-attempt-5.log` plus result/request JSON: the application fix passed; overlap logic incorrectly compared covered background controls with modal controls. The final scope correction is described above.

## Residual and external checks

- The two approximately 1 MB minified JavaScript chunks remain a performance risk and continue to emit the existing build warning.
- The fixed-clock mechanism patches process-local Python imports and browser `Date`; it is a deterministic local acceptance harness, not an operating-system clock test.
- The isolated fixture's weekly habit creation date was deliberately aged and is not production data.
- Android real-device installation is pending.
- Production Android signing is pending.
- GitHub Actions `Test and Deploy` final success is pending.
- GitHub Actions `Build Android Release` final success is pending.
- GitHub Release tag/name and `app-release.apk`, `app-release.aab`, and `latest.json` artifacts are pending.
- Live deployment health verification is pending.
- FEAT-03 through FEAT-10 and excluded engineering enhancements remain outside this closure.

## Durable structured artifacts

- Core: `core-browser-results.json`, `core-request-log.json`, `core-browser-verification.cjs`, `auth-storage-state.json`, `midnight-fixture.json`.
- Midnight: `midnight-browser-results.json`, `midnight-request-log.json`, `midnight-browser-verification.cjs`, `fixed-clock-backend.py`.
- Screenshots: `01-*.png` through `21-*.png` under the evidence root.
- Durable request and auth JSON preserves field structure but redacts password, access-token, and refresh-token values.

## Release addendum

After all local code and browser checks passed, the release metadata was changed through the required source-of-truth flow:

```text
VERSION: 1.13.0 -> 1.14.0

cd frontend && npm run sync:version
Synchronized frontend metadata to 1.14.0

cd frontend && npm run check:version
Version check passed: 1.14.0

cd frontend && npm run build
2031 modules transformed; built successfully in 11.22s
Existing warning remained: index 1,050.71 kB and element-plus 1,069.31 kB.
```

The first exact final gate after version, roadmap, and ledger updates produced:

```text
cd backend && venv/bin/pytest
404 passed, 952 warnings in 118.27s

cd frontend && npm test
155 passed, 0 failed in 677 ms

cd frontend && npm run check:version
Version check passed: 1.14.0

cd frontend && npm run build
2031 modules transformed; built successfully in 11.01s
Existing >500 kB warning remained.

git diff --check
exit 0; no output

git status --short
Task 1-7 implementation/report/version paths and preserved pre-existing dirty/untracked user paths were present. No unrelated file was reverted or cleaned.
```

The final post-report repetition, staging list, and commit are recorded in the Task 7 report.
