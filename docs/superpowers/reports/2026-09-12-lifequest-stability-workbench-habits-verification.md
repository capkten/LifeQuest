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

## Post-audit corrective gate (2026-09-13 UTC)

The uncommitted implementation was reviewed against its regression surface. The audit found and corrected database lock detection that depended on affected-row counts, negative coin debits, legacy habit-completion duplicates, weekly history range leakage, nested backpack transaction rollback, explicit project unbinding, schedule-change streak history, long pause traversal, the missing weekly-target label, historical finance rewards using the current date, and stale project-detail mutations. The two miswired fixture references in the new regression tests and a misplaced assertion were corrected as test defects.

```text
cd backend && venv/bin/pytest
439 passed, 965 warnings in 126.98s

cd frontend && npm test
170 passed, 0 failed in 1008 ms

cd frontend && npm run check:version
Version check passed: 1.14.1

cd frontend && npm run build
2031 modules transformed; built successfully in 13.21s
index: 1,050.83 kB (gzip 360.89 kB)
element-plus: 1,069.31 kB (gzip 335.40 kB)
The existing >500 kB chunk warning remained.

git diff --check
exit 0; no output
```

This gate covers the current working tree before commit. Android real-device, production-signing, CI final conclusions, release artifacts, and live deployment health remain external checks.

## Isolation and account

- Core frontend: `http://127.0.0.1:5173`
- Core backend API: `http://127.0.0.1:18000/api`
- Corrective core-run runtime root: `/tmp/lifequest-task7-fix1-nPuDva`
- Corrective core-run SQLite database: `/tmp/lifequest-task7-fix1-nPuDva/browser.sqlite`
- The corrective backend ran from `/tmp/lifequest-task7-fix1-nPuDva/backend`, which isolated the hard-coded notes and uploads paths.
- Existing unrelated services on ports 8000, 8001, and 3002 were not modified.
- The accepted corrective run used unique username `t7_240412925` and email `t7_240412925@example.com`; credentials are omitted. A prior `example.test` registration was actually observed as HTTP 422, while `example.com` registered with HTTP 200.
- The core run used Chromium with browser timezone `America/Los_Angeles`; China date behavior came from application code and server responses.
- The weekly-target habit's `created_at` was adjusted only in the isolated SQLite fixture to `2026-09-07 00:00:00.000000`, making three historical dates in that week eligible for the requested backfill/capacity matrix.

## FEAT-01 browser evidence

The corrective core browser harness is `core-browser-verification.cjs`; structured results and requests are `core-browser-results.json` and `core-request-log.json`. It recorded 30 passed flow assertions and 164 response entries: 154 HTTP 200, seven HTTP 409 entries, and three deliberately injected HTTP 503 responses. Every row below repeats the frontend/backend URL, viewport, China-local instant, observed status, result flow ID, exact artifact, and request-log reference. The request IDs resolve to entries in `core-request-log.json`; the fourth-focus flow intentionally has no request reference because the disabled control must not send one.

| Flow ID | Logical flow | Frontend / backend URL | Viewport | China-local instant | Observed status | Exact result/artifact/request reference |
| --- | --- | --- | --- | --- | --- | --- |
| auth.registration-login | real registration and login | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:34.688 +08:00` | register=200; login=200; workbench=200 | `01-registration-login-home.png`; result=`auth.registration-login`; requests=`request-0001..request-0010` |
| feat01.quick-create.today | FEAT-01 quick-create today task | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:34.828 +08:00` | status=200 | `core-request-log.json`; result=`feat01.quick-create.today`; requests=`request-0011` |
| feat01.quick-create.unscheduled | FEAT-01 quick-create unscheduled task | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:34.969 +08:00` | status=200 | `core-request-log.json`; result=`feat01.quick-create.unscheduled`; requests=`request-0012..request-0015` |
| feat01.quick-create.upcoming | FEAT-01 quick-create specified-date task | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:35.129 +08:00` | status=200 | `core-request-log.json`; result=`feat01.quick-create.upcoming`; requests=`request-0016..request-0019` |
| feat01.create.overdue-group-task | FEAT-01 create overdue group task | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:35.166 +08:00` | status=200 | `core-request-log.json`; result=`feat01.create.overdue-group-task`; requests=`request-0020..request-0024` |
| feat01.render.task-groups | FEAT-01 render today, overdue, unscheduled, and upcoming groups | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:35.524 +08:00` | refresh=200 | `02-workbench-three-schedules-and-groups.png`; result=`feat01.render.task-groups`; requests=`request-0025` |
| feat01.focus.fourth-candidate | FEAT-01 fourth focus candidate disabled and not sent | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:36.250 +08:00` | request=not sent | `03a-focus-fourth-disabled-not-sent.png`; result=`feat01.focus.fourth-candidate`; requests=none (expected) |
| feat01.focus.save-order | FEAT-01 three-item focus selection and ordering | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:36.550 +08:00` | status=200 | `03-focus-three-selection-order.png`; result=`feat01.focus.save-order`; requests=`request-0026` |
| feat01.complete.today-settlement | FEAT-01 completion settles once, retains completed focus, and warns without resubmission | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:36.929 +08:00` | completion=200; reward refresh=503 | `04-completed-focus-no-resubmission-warning.png`; result=`feat01.complete.today-settlement`; requests=`request-0027..request-0038` |
| feat01.complete.overdue | FEAT-01 complete overdue task | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:37.024 +08:00` | status=200 | `core-request-log.json`; result=`feat01.complete.overdue`; requests=`request-0039` |
| feat01.complete.unscheduled | FEAT-01 complete unscheduled task | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:37.148 +08:00` | status=200 | `core-request-log.json`; result=`feat01.complete.unscheduled`; requests=`request-0040..request-0045` |
| feat01.complete.upcoming | FEAT-01 complete upcoming task | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:37.280 +08:00` | status=200 | `core-request-log.json`; result=`feat01.complete.upcoming`; requests=`request-0046..request-0051` |
| feat01.quick-create.changed-request-id | FEAT-01 changed request-ID payload conflict | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:37.341 +08:00` | status=409 | `core-request-log.json`; result=`feat01.quick-create.changed-request-id`; requests=`request-0052..request-0058` |
| feat01.focus.stale-revision | FEAT-01 stale focus revision conflict | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:37.658 +08:00` | external=200; stale save=409 | `05-focus-stale-revision-conflict.png`; result=`feat01.focus.stale-revision`; requests=`request-0059..request-0063` |
| feat01.refresh.failure-recovery | FEAT-01 refresh failure preserves data and retry recovers | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:37.934 +08:00` | forced=503; retry=200 | `06-workbench-refresh-failure-preserves-data.png`; result=`feat01.refresh.failure-recovery`; requests=`request-0064..request-0065` |
| feat01.initial-load.failure-recovery | FEAT-01 initial load failure recovery | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:38.889 +08:00` | forced=503; retry=200 | `07-workbench-initial-load-failure.png`; result=`feat01.initial-load.failure-recovery`; requests=`request-0066..request-0074` |
| feat01.viewport.desktop-wide | FEAT-01 viewport desktop-wide | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:45.123 +08:00` | workbench=200 | `12-desktop-wide-workbench-focus.png`; result=`feat01.viewport.desktop-wide`; requests=`request-0118..request-0125` |
| feat01.viewport.desktop-narrow | FEAT-01 viewport desktop-narrow | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1024x768 | `2026-09-13 03:13:45.812 +08:00` | workbench=200 | `12-desktop-narrow-workbench-focus.png`; result=`feat01.viewport.desktop-narrow`; requests=`request-0126..request-0133` |
| feat01.viewport.mobile-390 | FEAT-01 viewport mobile-390 | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 390x844 | `2026-09-13 03:13:46.451 +08:00` | workbench=200 | `12-mobile-390-workbench-focus.png`; result=`feat01.viewport.mobile-390`; requests=`request-0134..request-0141` |
| feat01.viewport.reference-375 | FEAT-01 viewport reference-375 | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 375x812 | `2026-09-13 03:13:47.053 +08:00` | workbench=200 | `12-reference-375-workbench-focus.png`; result=`feat01.viewport.reference-375`; requests=`request-0142..request-0149` |

For page-level peer overlap checks, the scope is every visible `button`, `input`, `select`, `textarea`, and link except descendants of the intentional fixed `.bottom-nav`. The nav exclusion prevents the fixed navigation overlay from being compared with partially offscreen page controls; content controls remain fully checked. Every viewport had zero content-peer overlaps and zero horizontal overflow.

## FEAT-02 browser evidence

| Flow ID | Logical flow | Frontend / backend URL | Viewport | China-local instant | Observed status | Exact result/artifact/request reference |
| --- | --- | --- | --- | --- | --- |
| feat02.create.daily | FEAT-02 create daily habit | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:40.419 +08:00` | status=200 | `08-habit-daily-weekday-weekly-target.png`; result=`feat02.create.daily`; requests=`request-0076..request-0081` |
| feat02.create.weekday | FEAT-02 create specified-weekday habit | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:40.419 +08:00` | status=200 | `08-habit-daily-weekday-weekly-target.png`; result=`feat02.create.weekday`; requests=`request-0082` |
| feat02.create.weekly-target | FEAT-02 create weekly-target habit (target 3) | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:40.419 +08:00` | status=200 | `08-habit-daily-weekday-weekly-target.png`; result=`feat02.create.weekly-target`; requests=`request-0083` |
| feat02.pause-resume | FEAT-02 pause and resume daily habit | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:40.802 +08:00` | pause=200; resume=200 | `core-request-log.json`; result=`feat02.pause-resume`; requests=`request-0084..request-0085` |
| feat02.leave-revoke | FEAT-02 save and revoke leave `[2026-09-13, 2026-09-14)` | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:41.169 +08:00` | leave=200; revoke=200 | `core-request-log.json`; result=`feat02.leave-revoke`; requests=`request-0086..request-0089` |
| feat02.note-completion-history | FEAT-02 complete with note and inspect factual heatmap | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:41.486 +08:00` | completion=200 | `09-habit-note-history-heatmap.png`; result=`feat02.note-completion-history`; requests=`request-0090..request-0094` |
| feat02.weekly-capacity | FEAT-02 weekly target capacity shared by normal completion and backfill | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:42.231 +08:00` | backfills=200,200,200; fourth normal=409; fourth backfill=409 | `10-weekly-target-3-of-3-capacity.png`; result=`feat02.weekly-capacity`; requests=`request-0095..request-0114` |
| feat02.history.stale-response | FEAT-02 delay habit A history then open habit B | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 1440x900 | `2026-09-13 03:13:44.447 +08:00` | first=200; second=200 | `11-stale-history-second-habit-wins.png`; result=`feat02.history.stale-response`; requests=`request-0115..request-0117` |
| feat02.mobile-history-overflow-focus | FEAT-02 mobile history overflow and focus | `http://127.0.0.1:5173` / `http://127.0.0.1:18000/api` | 390x844 | `2026-09-13 03:13:47.719 +08:00` | history=200 | `13-mobile-390-history-overflow-focus.png`; result=`feat02.mobile-history-overflow-focus`; requests=`request-0150..request-0156` |

## China-midnight browser evidence

The completed core fixture at `/tmp/lifequest-task7-fix1-nPuDva/browser.sqlite` was copied to `/tmp/lifequest-task7-fix1-nPuDva/before.sqlite` and `/tmp/lifequest-task7-fix1-nPuDva/after.sqlite` for the corrective rerun. The two isolated backends ran from `/tmp/lifequest-task7-fix1-nPuDva/backend` with an explicit `PYTHONPATH`, one fixed at each instant. `fixed-clock-backend.py` patched only the imported clock globals used by daily workbench, finance, and Todo services. `midnight-browser-verification.cjs` fixed browser `Date`, kept browser timezone `America/Los_Angeles`, logged every API response, and ran the real Vue UI.

Services and instants:

| UTC instant | China-local instant | Frontend | Backend API |
| --- | --- | --- | --- |
| `2026-09-11T15:59:59Z` | `2026-09-11 23:59:59 +08:00` | `http://127.0.0.1:5174` | `http://127.0.0.1:18001/api` |
| `2026-09-11T16:00:00Z` | `2026-09-12 00:00:00 +08:00` | `http://127.0.0.1:5175` | `http://127.0.0.1:18002/api` |

The corrective rerun is recorded in `midnight-fix1-rerun.log`. It passed 24/24 assertions, with 12 assertions at each fixed instant. `midnight-request-log.json` contains 148 response entries, all HTTP 200. This legacy midnight harness records complete response rows but does not assign request IDs; the core harness request-reference guarantees above do not apply to this older log format.

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

- Core: `core-browser-results.json`, `core-request-log.json`, `core-browser-verification.cjs`, `core-fix-round-1.log`, `auth-storage-state.json`, `midnight-fixture.json`.
- Midnight: `midnight-browser-results.json`, `midnight-request-log.json`, `midnight-fix1-rerun.log`, `midnight-browser-verification.cjs`, `fixed-clock-backend.py`.
- Screenshots: `01-*.png` through `21-*.png` under the evidence root.
- Durable request and auth JSON preserves field structure but redacts password, access-token, and refresh-token values.

## Release addendum

The Git ancestor before Task 7, `d61b9c4`, contains root `VERSION` `1.8.8`. At Task 7 entry, the assigned checkout already had user-owned, intentionally uncommitted Tasks 1-6 version increments and its root `VERSION` first line was `1.13.0`. Task 7 changed that working-tree value only from `1.13.0` to `1.14.0`, then synchronized both frontend package files from the root source of truth. Consequently, commit `8e223ea` displays `1.8.8` to `1.14.0` when diffed against its committed parent; that commit diff does not independently prove the intermediate `1.13.0` state.

After all local code and browser checks passed, the release metadata was synchronized through the required source-of-truth flow:

```text
Task 7 working-tree transition: VERSION 1.13.0 -> 1.14.0
Committed-parent comparison: VERSION 1.8.8 -> 1.14.0 (includes pre-existing uncommitted increments)

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
