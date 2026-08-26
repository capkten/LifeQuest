# Centralized Application Version Source

## Goal

Use the repository-root `VERSION` file as the only manually edited application version source. The current value remains `1.8.2`.

## Design

- Frontend Vite continues to inject the root `VERSION` value into `__APP_VERSION__`, which is displayed beside the LifeQuest brand in the sidebar.
- Backend FastAPI reads the same root file at startup and uses it for the OpenAPI application version.
- Android Gradle reads the same root file for `versionName`; `versionCode` remains a separate Android-only numeric release counter.
- Frontend npm metadata is synchronized from `VERSION` by a repository script, so `package.json` and `package-lock.json` are generated metadata rather than independent version sources.
- Android release detection watches `VERSION`, because changing it is what should trigger a release build.

## Verification

- A version consistency check asserts that backend, frontend build metadata, Android configuration, and the root file resolve to the same semantic version.
- Existing frontend regression tests, backend tests, and production builds remain required.

## Scope

No changes to release numbering policy, Android `versionCode` policy, deployment secrets, or the displayed sidebar layout.
