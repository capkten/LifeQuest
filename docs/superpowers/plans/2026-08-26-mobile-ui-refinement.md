# Mobile UI Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve LifeQuest's mobile shell, touch behavior, viewport resilience, and visible UI states without changing business functionality.

**Architecture:** Keep the current Vue views and Capacitor WebView architecture. Centralize mobile shell tokens and safe-area behavior in `App.vue`/`AppLayout.vue`, then make focused view-level changes in Notes, Home, and NoteEditor. Use source regression tests plus Playwright browser verification with constructed API responses.

**Tech Stack:** Vue 3, Vite, Capacitor, CSS media queries, Node test runner, Playwright.

## Global Constraints

- Preserve existing business flows, API calls, routes, and data contracts.
- Mobile web interactive regions remain at least 44px; Capacitor/Android regions target 48px.
- Use `100vh` fallback followed by `100dvh` for viewport-sensitive regions.
- Preserve the existing blue-green LifeQuest visual direction.
- Do not modify unrelated user changes under `docs/superpowers/`.

### Task 1: Add mobile regression coverage

**Files:**
- Create: `frontend/src/views/mobile-ui-regressions.test.mjs`

- [x] Write source checks for mobile navigation safe-area spacing, Android-sized touch targets, `dvh` fallback, Notes semantic actions, and dialog labeling/focus hooks.
- [x] Run `node --test src/views/mobile-ui-regressions.test.mjs` from `frontend` and confirm it fails against the current implementation.

### Task 2: Harden mobile shell and shared controls

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/layout/AppLayout.vue`
- Modify: `frontend/src/components/layout/Header.vue`

- [x] Add shared mobile tokens for web and Capacitor touch targets, content bottom inset, and viewport height.
- [x] Make the app content reserve the full fixed navigation plus safe area and ensure the last content can scroll above it.
- [x] Remove hover-only behavior from mobile navigation and keep visible pressed/focus treatment.
- [x] Use 48px minimum shell controls in Capacitor/Android mode while retaining 44px web fallback.

### Task 3: Improve Notes mobile interactions and dialogs

**Files:**
- Modify: `frontend/src/views/Notes.vue`

- [x] Replace `div[role=button]` search and notebook entries with native buttons while preserving click routing.
- [x] Give create/delete dialog triggers stable refs and restore focus after close.
- [x] Add `aria-labelledby`, Escape handling, and Tab trapping to the dialogs.
- [x] Raise dialog close controls to the shared touch target and retain mobile scrolling for dialog content.

### Task 4: Improve mobile state presentation

**Files:**
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/views/NoteEditor.vue`
- Modify: `frontend/src/views/Calendar.vue`

- [x] Add a direct CTA to Home's empty daily state without changing route behavior.
- [x] Reserve stable loading/empty/error heights and avoid bottom navigation overlap on mobile.
- [x] Add `100dvh` fallbacks for editor and calendar viewport-sensitive areas.

### Task 5: Verify the first implementation pass

**Files:**
- No new production files.

- [x] Run the focused regression test and existing frontend regression tests.
- [x] Run `npm run build`.
- [x] Start Vite and use constructed API data at 375×812, 390×844, and 768×812.
- [x] Check loading, empty, error, dialog open/close, touch target dimensions, horizontal overflow, and bottom navigation coverage.
- [x] Review the diff and report any remaining platform-specific limitations.
