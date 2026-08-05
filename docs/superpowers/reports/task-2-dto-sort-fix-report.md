# Task 2 DTO and sort fix status

## Status

Stopped at the user's request before running the test suite. No commit was created and no frontend files were modified by this task.

## Reviewed implementation

- `backend/app/api/notes.py`: `GET /api/notes/recent` currently maps each `NoteNode` through the explicit `node_to_response` constructor, including the related notebook's actual name while retaining the user-scoped service query and response fields.
- `backend/app/repositories/note.py`: `discover` currently applies `nullslast()` to both `created` and `updated` descending sort expressions.

## Test change

- `backend/tests/test_notes.py`: strengthened the recent-notes regression test to create notes in two notebooks and assert each returned note has its actual `notebook_name`.
- The working tree already contained a NULL timestamp sorting regression test covering both `created` and `updated` sorts.

## Verification

No related tests, full `backend` pytest, or `git diff --check` were run after the latest test edit because the user requested that long-running testing stop.
