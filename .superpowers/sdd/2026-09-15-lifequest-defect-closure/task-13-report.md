# Task 13 Report: Serialize Note Attachment Uploads and Deletion

## Result

Attachment storage and database persistence now happen inside the existing per-notebook lock. The service obtains the notebook id only to select that lock, then re-reads the node and write permission after acquiring it. If deletion acquired the lock first, the upload returns 404 without creating an attachment row or file. If upload acquired it first, deletion waits and then removes the committed row and file. Storage and database exceptions roll back and remove any partial upload file.

No foreign key or migration was added.

## RED: Existing Implementation

Commands ran from `backend/` using `/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest`.

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_notes.py::test_notebook_deletion_winning_attachment_upload_returns_404_without_artifacts -s
```

Observed failure against the old implementation:

```text
E AssertionError: assert ('ok', '3c299...8a069a4bbbff') == ('http_error', 404, 'Note not found')
1 failed, 349 warnings in 0.38s
```

The uploader passed its access check while deletion held the notebook lock, then committed after deletion. It returned success instead of 404.

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_notes.py::test_attachment_upload_winning_notebook_deletion_removes_row_and_file -s
```

Observed failure against the old implementation:

```text
E assert [<app.models....>] == []
E Left contains one more item: <app.models.note.Attachment object at ...>
1 failed, 349 warnings in 0.30s
```

The post-deletion upload left an orphan attachment row (and its uploaded file).

The storage-obstruction and injected-commit-failure cleanup checks were also run against the old implementation. Both passed (`1 passed, 349 warnings in 0.22s` each), confirming that route-level file cleanup already covered those cases. They remain as process-level characterization checks; the new service now owns rollback and cleanup while holding the notebook lock.

## GREEN: Updated Implementation

Each race regression passed individually:

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_notes.py::test_notebook_deletion_winning_attachment_upload_returns_404_without_artifacts -s
1 passed, 349 warnings in 0.39s

/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_notes.py::test_attachment_upload_winning_notebook_deletion_removes_row_and_file -s
1 passed, 349 warnings in 0.91s
```

Storage and database cleanup checks passed together:

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_notes.py::test_attachment_storage_failure_does_not_create_a_database_row_or_file tests/test_notes.py::test_attachment_database_failure_removes_uploaded_file_and_row -s
2 passed, 349 warnings in 0.31s
```

Focused verification required by the brief:

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_notes.py tests/test_note_sharing.py
64 passed, 646 warnings in 38.64s
```

Full backend verification:

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q
602 passed, 1460 warnings in 181.60s (0:03:01)
```

`git diff --check` completed with exit status 0.

## Test Environment

The host provides Python 3.14. The repository-pinned SQLAlchemy 2.0.23 fails during import on this interpreter with `AssertionError` in `sqlalchemy.util.langhelpers.TypingOnly`. Tests ran in a temporary virtual environment populated from `backend/requirements.txt`, with SQLAlchemy upgraded only in that temporary environment to 2.0.54. No dependency or lockfile in the repository was changed. The test output contains pre-existing Python/FastAPI/Pydantic deprecation warnings.

The race tests use separate forked worker processes, independent SQLAlchemy sessions, a temporary file-backed SQLite database, and a real temporary filesystem. Workers execute the actual async upload endpoint function and `NoteService.delete_notebook`, coordinated at lock and authorization boundaries. Assertions query the database from a fresh session and inspect files on disk.

## Changed Files

- `backend/app/api/notes.py`
- `backend/app/services/note.py`
- `backend/tests/test_notes.py`
- `.superpowers/sdd/2026-09-15-lifequest-defect-closure/task-13-report.md`

## Self-Review

- Upload writes and attachment commit share the existing notebook lock used by tree and notebook deletion.
- Write access is re-evaluated after the lock is acquired; the pre-lock route check is retained only for its existing early response behavior.
- A deleted node/notebook is translated to HTTP 404, and denied write access remains HTTP 403.
- File-write and commit exceptions roll back the SQLAlchemy session and remove any partial upload file. Attachment ids are assigned before commit, so no post-commit refresh can fail after the row is durable.
- Both process orderings assert row and file state. Failure tests use real filesystem and database behavior, not mocked persistence.
- No schema, migration, foreign key, version, or unrelated application files changed.
- A separate edit to `.superpowers/sdd/2026-09-15-lifequest-defect-closure/final-fix-report.md` was present during review and was left untouched and unstaged.

## Concerns

The only environment caveat is the temporary SQLAlchemy override required to run the repository's pinned dependencies on Python 3.14. This does not affect repository files or the production lock behavior.
