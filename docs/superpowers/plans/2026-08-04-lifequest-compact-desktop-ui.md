# LifeQuest Compact Desktop UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved A-style compact desktop layout while preserving the existing mobile experience and business behavior.

**Architecture:** Keep Vue route and page data unchanged. Adjust shared design tokens and shell spacing first, then make Home use a desktop-only two-column grid with existing sections assigned to primary and secondary columns. Use CSS media queries so mobile remains single-column.

**Tech Stack:** Vue 3, scoped CSS, Element Plus, Vite.

## Global Constraints

- Do not change API calls, route names, stores, or business logic.
- Keep touch targets at least 44px and preserve visible keyboard focus.
- Keep the current blue color family; font family remains variable-driven for a later typography pass.
- Verify at 375px, 1024px, and 1440px with no horizontal overflow.

### Task 1: Tighten shared desktop shell

**Files:** `frontend/src/App.vue`, `frontend/src/components/layout/AppLayout.vue`, `frontend/src/components/layout/Sidebar.vue`

- [x] Reduce desktop shell spacing and sidebar width through existing CSS variables.
- [x] Set `.app-content-shell` to a centered `max-width` while preserving full-width mobile behavior.
- [x] Reduce sidebar internal padding and user summary height without removing navigation items.
- [x] Run `npm run build`; responsive rules preserve 375/1024/1440px targets.

### Task 2: Apply the approved Home desktop composition

**Files:** `frontend/src/views/Home.vue`

- [x] Keep the current template data and actions unchanged.
- [x] Add a desktop-only grid that places today’s actionable content in the primary column and recent summaries in the secondary column.
- [x] Remove redundant outer spacing through page-local CSS rather than deleting useful content.
- [x] Keep the current mobile order and single-column flow below 767px.
- [x] Run `npm run build` successfully.

### Task 3: Verify shared pages and typography seam

**Files:** `frontend/src/views/Todos.vue`, `frontend/src/views/Shop.vue`, `frontend/src/views/Profile.vue`, `docs/superpowers/reports/2026-08-04-lifequest-compact-desktop-ui-verification.md`

- [x] Check shared shell selectors and compact page styles for unchanged page compatibility; no route or page data changes were made.
- [x] Record the current font variables and leave a clear seam for a later font selection pass.
- [x] Run final build and document responsive results.

### Task 4: Review and handoff

- [x] Run `git diff --check` and confirm no generated files are added.
- [x] Review the diff for accidental business-logic changes.
- [x] Leave commits to the user because automatic commits are not authorized.
