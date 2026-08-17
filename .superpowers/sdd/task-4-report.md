# Task 4 Report

## Status

Implemented Task 4 within the requested frontend scope. Added the cultivation API service, Pinia store, eight shared cultivation components, shared cultivation styles, and static regression/accessibility contract tests. No routes, pages, Home, or Todos files were modified.

## Commit

`9621012 feat(frontend): add cultivation state and shared ui`

## Tests

Command:

```text
cd frontend
node --test src/views/cultivation-regressions.test.mjs
```

Exact output:

```text
✔ cultivation service keeps endpoint paths in one module (6.1613ms)
✔ cultivation shared states expose accessible stable contracts (3.5153ms)
ℹ tests 2
ℹ suites 0
ℹ pass 2
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 137.9897
```

Build command:

```text
cd frontend
npm run build
```

Result: exit code 0; Vite reported `1936 modules transformed` and `built in 16.16s`.

## Concerns

- The build prints an existing npm `always-auth` configuration warning, two Rollup `#__PURE__` annotation warnings from `@vueuse/core`, and a chunk-size warning for the main bundle; none failed the build.
- No browser/manual rendering test was added because Task 4 explicitly limits work to shared components and static contract tests.
- The requested `gpt-5.6-luna` model was not exposed by the available workspace tool interface.

## Review Fixes

- Changed every cultivation service request to use `/cultivation/...` relative to the axios `/api` base URL, preventing `/api/api/...` requests while preserving `/api/cultivation/...` server endpoints.
- Updated `applySettlement` for the backend `RewardSettlement` delta shape. It immediately merges `cultivation`, `spirit_stones`, and `merit` into the visible overview, then awaits `refresh()` to replace the local values with the authoritative overview and current `next_stage`/realm data.
- Replaced the nonexistent `StageProgress.percent` dependency with a clamped percentage derived from `current_threshold`, `next_threshold`, and `cultivation`; the progressbar now consistently uses a 0-100 ARIA range.
- Added tribulation `attempting`/`submitting` operation state with `aria-busy`, disabled repeated attempts, and visible attempting text. Added MapNode locked prop/data handling with disabled interaction and `Locked` text. Added TechniqueSlotGrid busy, error/retry, empty, and disabled interaction states.
- Normalized NPC and generic event dictionaries with available labels/details, namespaced stable keys, and deterministic index fallbacks.
- Replaced the reward dismissal glyph with the existing Element Plus `Close` icon while retaining an accessible button label.
- Expanded static regressions for doubled API prefixes, settlement delta/refresh behavior, threshold-based progress, icon usage, locked/empty/error states, and repeated-operation disabled semantics.

## Review Fix Verification

Focused command:

```text
cd frontend
node --test src/views/cultivation-regressions.test.mjs
```

Exact output:

```text
✔ cultivation service keeps endpoint paths in one module (7.5622ms)
✔ settlements update visible deltas and obtain an authoritative overview (1.7417ms)
✔ realm progress derives its percentage from StageProgress thresholds (1.6658ms)
✔ cultivation shared states expose accessible stable contracts (5.5522ms)
ℹ tests 4
ℹ suites 0
ℹ pass 4
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 213.2868
```

Build command:

```text
cd frontend
npm run build
```

Exact result: exit code `0`; Vite reported `1936 modules transformed` and `built in 13.28s`. The existing npm `always-auth`, two `@vueuse/core` Rollup annotation, and main chunk-size warnings remained non-fatal.
## Remaining Review Fixes

- Updated `NpcTimeline` to accept the backend `NpcRelationshipResponse` object through its `npcs` prop, including `fixed_core`, `recently_met`, and `events`. Array input remains supported. Each record now receives a deterministic source/index key, and unlabeled event dictionaries receive nonblank fallback labels.
- Updated `TribulationProbability` so `aria-busy` includes `loading`, `attempting`, and `submitting`. Retry is disabled while loading or busy, and attempt is disabled during loading and every busy state.
- Strengthened `cultivation-regressions.test.mjs` to check the service import/baseURL contract and relative cultivation paths, the NPC response fields and array guard, and explicit loading-aware retry/attempt bindings.

## Remaining Review Fix Verification

Focused command:

```text
cd frontend
node --test src/views/cultivation-regressions.test.mjs
```

Exact output:

```text
✔ cultivation service keeps endpoint paths in one module (6.7028ms)
✔ settlements update visible deltas and obtain an authoritative overview (1.2426ms)
✔ realm progress derives its percentage from StageProgress thresholds (1.5992ms)
✔ cultivation shared states expose accessible stable contracts (4.3056ms)
ℹ tests 4
ℹ suites 0
ℹ pass 4
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 159.9865
```

Build command:

```text
cd frontend
npm run build
```

Exact result: exit code `0`; Vite reported `1936 modules transformed` and `built in 12.60s`. The existing npm `always-auth`, two `@vueuse/core` Rollup annotation, and main chunk-size warnings remained non-fatal.
