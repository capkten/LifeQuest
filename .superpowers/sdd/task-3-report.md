# Task 3 Report

## Status

Implemented Task 3 cultivation API routes, request/response DTOs, startup registration, idempotent world/sect/technique seed integration, per-user fixed core NPC materialization, and focused API tests.

The implementation uses the existing FastAPI dependency pattern (`get_current_user`, `get_db`) and preserves the existing startup migration and seed sequence. No frontend files were changed.

## Implemented

- Added `backend/app/api/cultivation.py` with overview, world, sect, technique, NPC, and tribulation endpoints.
- Added cultivation API DTOs and strict request validation to `backend/app/schemas/cultivation.py`.
- Extended `CultivationService` with route-facing read/write operations and idempotent seed behavior.
- Registered the cultivation router and world seed in `backend/app/main.py`.
- Seeded 9 world nodes, 90 sects (9 stars x 6 normal, 3 special, 1 hidden), and three fixed core NPCs per user and sect on first NPC access.
- Added authenticated API, authorization, locking, idempotency, ownership, UUID resource, and request validation tests in `backend/tests/test_cultivation.py`.

## TDD Evidence

Initial focused run after adding the API tests, before implementation:

```text
7 failed, 7 passed
```

The failures were the expected missing-route `404` responses.

After the first implementation pass, the focused run reported four integration failures: test-session seed visibility, realm-lock ordering, and request extra-field validation. Those were corrected with request-session idempotent seeding, early realm locking, and strict DTO configuration.

## Verification

Focused cultivation suite:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q
```

Output:

```text
16 passed, 17 warnings in 6.90s
```

Full backend suite:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Output:

```text
124 passed, 367 warnings in 86.75s (0:01:26)
```

Warnings are pre-existing FastAPI lifecycle, Starlette/httpx, and jose datetime deprecations.

## Concerns

- The current ORM schema requires `Npc.user_id`, so fixed NPC records are materialized per user on first `/npcs` access rather than inserted as global startup rows.
- The current domain models do not include an explicit ordinary-disciple population-rule table; Task 3 therefore seeds only the requested fixed core NPC records and leaves ordinary NPC generation for the later domain work.
- The existing project has no configured formatter or linter; verification used the focused and full pytest suites.

## Review Fixes

- Tribulation attempts now require the profile to be at the current realm's final minor stage and at least its final-stage threshold. A fresh `qi_refining` profile receives a stable `409` lock response, remains unchanged, and does not create a `TribulationAttempt`. Failure still deducts the existing 10% cultivation loss, bounded at zero. The random decision now stores the actual `random.random() * 100` roll in `TribulationAttempt.roll`.
- Loadout updates now require a `LearnedTechnique` owned by the requesting user. Techniques above the user's current realm are rejected before any slot mutation; foreign learned techniques and insufficient realms use stable API errors. Validation is performed before applying a batch of updates.
- Sect seed data now uses the world-rule entry mapping: stars 1-9 require `foundation`, `golden_core`, `nascent_soul`, `spirit_transformation`, `void_refining`, `body_combination`, `great_vehicle`, `tribulation`, and final-stage `tribulation`, respectively. Hidden sects remain seeded but are excluded from listings and reject joins until an explicit unlock mechanism exists. Lower realms receive stable `409` lock responses.
- Focused tests now verify the exact seeded distribution of 9 stars x (6 normal, 3 special, 1 hidden), the visible listing count of 81, hidden and lower-realm join locks, exact roll persistence, fresh-profile tribulation locking, and cross-user/realm-safe loadout updates.

## Review Verification

Focused cultivation suite:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q
```

Output:

```text
21 passed, 17 warnings in 6.23s
```

Full backend suite:

```powershell
cd D:\codes\LifeQuest\backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Output:

```text
129 passed, 367 warnings in 83.63s (0:01:23)
```
