# Centralized Version Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository-root `VERSION` file the only manually edited application version source for frontend, backend, Android, and release automation.

**Architecture:** Keep `VERSION` as the canonical text file. Frontend Vite, backend startup code, and Android Gradle read it directly; npm metadata is synchronized by a small Node script. CI detects changes to `VERSION` so a version bump drives the release workflow.

**Tech Stack:** Vue/Vite, Node.js ES modules, FastAPI/Python, Android Gradle, GitHub Actions.

## Global Constraints

- The canonical version remains `1.8.2` during this change.
- Android `versionCode` remains `11`; only `versionName` comes from `VERSION`.
- Keep the existing sidebar version display and deployment workflow behavior.
- Read and write text files as UTF-8.

### Task 1: Add version synchronization and consistency checks

**Files:**
- Create: `scripts/sync-version.mjs`
- Create: `scripts/check-version.mjs`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

**Interfaces:**
- `sync-version.mjs` reads `VERSION` from the repository root and updates the root package metadata fields in `frontend/package.json` and `frontend/package-lock.json`.
- `check-version.mjs` exits non-zero if the canonical version or synchronized frontend metadata is invalid.

- [ ] **Step 1: Write the synchronization script**

  Read `VERSION` with UTF-8, require a semantic `x.y.z` value, update only the root package entries in both frontend package files, and write JSON with two-space indentation and a trailing newline.

- [ ] **Step 2: Write the consistency check**

  Read `VERSION`, parse both frontend package files, and assert their root `version` values equal the canonical value. Print the resolved version and exit with status 1 on mismatch.

- [ ] **Step 3: Wire synchronization into frontend metadata commands**

  Add a root-level npm script that invokes `node scripts/sync-version.mjs`; keep the existing package version at `1.8.2` after synchronization.

- [ ] **Step 4: Run the check**

  Run `node scripts/check-version.mjs` from the repository root. Expected output includes `1.8.2` and exit code 0.

### Task 2: Make backend and Android consume VERSION

**Files:**
- Modify: `backend/app/main.py`
- Modify: `frontend/android/app/build.gradle`
- Modify: `.github/workflows/android-release.yml`
- Test: `frontend/src/views/ui-regressions.test.mjs`

**Interfaces:**
- Backend exposes `app.version` from the root `VERSION` file.
- Android exposes `defaultConfig.versionName` from the root `VERSION` file while retaining `versionCode 11`.

- [ ] **Step 1: Add source-contract regression assertions**

  Assert the backend reads the root `VERSION`, Gradle reads the root `VERSION`, and Android release detection references `VERSION`.

- [ ] **Step 2: Run the new assertions and verify they fail**

  Run `node --test frontend/src/views/ui-regressions.test.mjs`. Expected: the new contract assertions fail against the current hardcoded backend/Android/CI configuration.

- [ ] **Step 3: Update backend version loading**

  Resolve the repository root relative to `backend/app/main.py`, read `VERSION` as UTF-8, strip whitespace, and pass the value to `FastAPI(..., version=...)`.

- [ ] **Step 4: Update Android version loading**

  In `frontend/android/app/build.gradle`, resolve `../../VERSION` from the Android project directory, read and trim it, and use it as `versionName`.

- [ ] **Step 5: Update Android release detection**

  Change the workflow diff check to compare `VERSION` and the Android workflow, so a canonical version change triggers the Android release job.

- [ ] **Step 6: Run the frontend contract tests**

  Run `node --test frontend/src/views/ui-regressions.test.mjs`. Expected: all tests pass.

### Task 3: Verify builds and hand off

**Files:**
- No additional source files.

- [ ] **Step 1: Run synchronization and consistency checks**

  Run `node scripts/sync-version.mjs` followed by `node scripts/check-version.mjs`; expect version `1.8.2`.

- [ ] **Step 2: Run frontend regression tests and build**

  Run the existing frontend regression test command from `.github/workflows/deploy.yml`, then run `npm run build` in `frontend`.

- [ ] **Step 3: Run backend tests**

  Run `pytest` in `backend`; expect the existing suite to pass.

- [ ] **Step 4: Review the diff**

  Run `git diff --check` and confirm only the centralized-version files changed, excluding pre-existing user documentation changes.

- [ ] **Step 5: Commit and push**

  Commit with `chore: centralize application version source`, then push the current branch to its configured remote.
