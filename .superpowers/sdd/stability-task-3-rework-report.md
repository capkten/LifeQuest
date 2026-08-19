# Task 3 Rework Report

Date: 2026-08-19
Base: `b022c32`
Commit: `fix(ui): close cross-action feedback gaps`

## TDD Evidence

Four focused regression assertions were added before production changes and run in the red phase.

- `35 passed, 4 failed`
- Failures covered cross-item in-flight feedback, backend cultivation detail mapping, tribulation cooldown ordering, and Home daily-summary error state.

## Changes

- Shared in-flight guards in `Todos.vue`, `Shop.vue`, `Backpack.vue`, and `ProjectDetail.vue` now use existing toast feedback and return without submitting another request. Backpack discard confirmation follows the same path.
- `errorMessage.js` maps parameterized technique/slot realm errors and the exact final-stage, completed, and cooldown detail strings emitted by the cultivation service.
- `Tribulations.vue` checks `cooldown_until` before `available`, making cooldown feedback reachable.
- `Home.vue` tracks daily-summary errors separately, renders an inline retry state, clears it on retry, and prevents failed requests from rendering the legitimate empty state.

## Verification

- Focused Node suites: `39 passed`
- Broader frontend Node suites: `65 passed`
- `npm run build`: passed; existing npm config, Rollup PURE annotation, and large-chunk warnings remain.
- `git diff --check`: passed.
- Harness Playwright: `52 checks`, `0` blank/overflow failures, `0` console errors, `0` request failures. Evidence: `.harness/iterations/2026-08-18T18-42-53.375Z/results.json`.
- Authenticated Playwright interaction: forcing `/api/todos/daily` to return 500 showed the retryable error and did not show `今天没有待办事项`. A cooldown preview dispatched through the visible Tribulations control showed `渡劫冷却中，请稍后再试。`, with no unexpected console errors or request failures.

The Harness route pass and supplemental interactions are evidence for this rework only. The broader dynamic contract items remain subject to their own authenticated business-flow evaluator and are not marked verified from static tests alone.
