# Task 1 Report

## Scope

Implemented only the Task 1 cultivation domain model and registration work:

- Added `CultivationProfile`, `CultivationLog`, and `TribulationAttempt` in `backend/app/models/cultivation.py`.
- Added `WorldNode`, `Sect`, `SectMembership`, `Npc`, and `NpcEvent` in `backend/app/models/world.py`.
- Added `Technique`, `TechniqueSlot`, and `LearnedTechnique` in `backend/app/models/technique.py`.
- Registered the new model modules in `backend/app/models/__init__.py`.
- Explicitly imported `app.models` in `backend/app/main.py` before `Base.metadata.create_all` so startup table creation sees every model.
- Added the focused registration test in `backend/tests/test_cultivation.py`.

No API routes, frontend code, schemas, repositories, services, or later-task behavior were added.

## TDD Evidence

The registration test was run before implementation:

```text
FAILED tests/test_cultivation.py::test_cultivation_tables_are_registered
ModuleNotFoundError: No module named 'app.models.cultivation'
```

After implementing the models and registration, the focused test passed:

```text
1 passed, 7 warnings
```

## Verification

Commands run from `backend`:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_cultivation_tables_are_registered -q
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

The complete backend suite passed:

```text
108 passed, 354 warnings in 74.00s
```

`git diff --check` completed without whitespace errors.

## Notes

The suite emits existing FastAPI/Starlette and `datetime.utcnow()` deprecation warnings. They are unrelated to Task 1 and did not cause test failures.

`CultivationService.ensure_profile` is a later-task service interface from the plan; it was intentionally not implemented because this task is restricted to domain models, model registration, and focused tests.

## Review Fix: NPC Ownership

The review finding at `backend/app/models/world.py:51` was fixed by making `Npc.user_id` non-nullable. NPC records are user-scoped/generated records for this implementation, so every NPC now requires a user foreign key. No services, APIs, schemas, or unrelated model behavior were added.

### Regression Test Evidence

The new regression test was run before the model change:

```text
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_npc_user_id_is_non_nullable -q
F                                                                        [100%]
E       AssertionError: assert True is False
E        +  where True = Column('user_id', Uuid(), ForeignKey('users.id'), table=<npcs>).nullable
1 failed, 7 warnings in 0.58s
```

After changing `Npc.user_id` to `nullable=False`, the same focused regression test passed:

```text
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py::test_npc_user_id_is_non_nullable -q
.                                                                        [100%]
1 passed, 7 warnings in 0.03s
```

### Final Test Evidence

```text
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_cultivation.py -q --disable-warnings
..                                                                       [100%]
2 passed, 7 warnings in 0.02s
```

```text
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q --disable-warnings
..............................
.......................................... [ 66%]
....................
.................                                    [100%]
109 passed, 354 warnings in 74.13s (0:01:14)
```
