# LifeQuest Stitch UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the visual language and responsive layouts from the supplied Stitch PC/mobile designs in the existing LifeQuest Vue application while preserving current routes, API calls, stores and business behavior.

**Architecture:** Treat the supplied Stitch `DESIGN.md` as the visual source of truth, but keep the existing Vue pages and services as the product source of truth. Update shared tokens and shell components first, then migrate pages in capability groups. Use the existing CSS variables and scoped Vue styles instead of replacing the Element Plus-based application with generated static HTML or Tailwind markup.

**Tech Stack:** Vue 3, Vue Router, Pinia, Element Plus, Vite, scoped CSS, existing FastAPI APIs.

## Global Constraints

- Preserve all existing route names, route paths, API wrappers, stores and business logic.
- Use the supplied Stitch palette: app background `#f4f8fb`, primary cyan `#0ea5e9`, secondary royal blue `#1d4ed8`, success emerald, navy text `#16324f`.
- Use `Space Grotesk` for headings and `DM Sans` for body/interface text.
- Use a 4px spacing baseline, 232px desktop sidebar, 68px collapsed tablet rail and 72px mobile bottom navigation.
- Preserve minimum 44px touch targets, visible focus states, `prefers-reduced-motion`, strong text contrast and no horizontal overflow.
- Use consistent SVG icons; do not add emoji icons or copy Stitch's static placeholder links/images into production data.
- Verify 375px, 768px, 1024px and 1440px layouts after each page group.

## Design-to-Code Mapping

| Stitch reference | Existing LifeQuest surface | Implementation decision |
| --- | --- | --- |
| PC `home_dashboard_desktop` and mobile `_7` | `frontend/src/views/Home.vue` | Recompose using existing task/goal/habit data and preserve current empty states. |
| PC/mobile task screens | `frontend/src/views/Todos.vue` | Add the progress header, category tabs, task rows, priority badges and mobile add-action treatment. |
| PC/mobile project screens | `frontend/src/views/Projects.vue`, `ProjectDetail.vue` | Map Active Projects cards and project detail hierarchy onto existing project data. |
| PC/mobile profile screens | `frontend/src/views/Profile.vue`, `EditProfile.vue`, `Backpack.vue` | Reuse the profile/attributes/achievement/inventory visual grouping without changing APIs. |
| PC/mobile shop screens | `frontend/src/views/Shop.vue`, `ExchangeHistory.vue` | Apply featured reward, wallet summary, item cards and redeem CTA patterns. |
| PC/mobile finance screens | `frontend/src/views/Finance.vue` and finance subpages | Apply wallet summary, chart card, savings/budget and transaction hierarchy to existing finance features. |
| Stitch login screen | `frontend/src/views/Login.vue`, `Register.vue` | Align auth shell, form spacing and background treatment while keeping validation and auth flow intact. |
| No direct Stitch reference | Notes, Calendar, Stats, Coin History and detail/history pages | Apply shared tokens, page header, cards, filters and empty states consistently; do not invent a new page-specific visual language. |

---

### Task 1: Establish the shared Stitch visual tokens

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `design-system/lifequest/MASTER.md`
- Reference: supplied `stitch_lifequest_design_system/*/lifequest_dashboard/DESIGN.md`

- [x] Compare every existing root token against the Stitch reference and list intentional differences before editing.
- [x] Normalize color aliases, typography sizes, radii, spacing, border colors and shadow levels so pages can consume one token set.
- [x] Add shared utility styles for page headers, surface cards, pills, progress bars, empty states and focus rings.
- [x] Keep the existing responsive breakpoints and document any breakpoint-specific Stitch adaptation.
- [x] Run `cd frontend; npm run build` and confirm no style or template compilation errors.

### Task 2: Align the desktop shell and mobile navigation

**Files:**
- Modify: `frontend/src/components/layout/AppLayout.vue`
- Modify: `frontend/src/components/layout/Sidebar.vue`
- Modify: `frontend/src/components/layout/Header.vue`
- Verify: `frontend/src/router/index.js`

- [x] Keep the current route-to-page mapping, but update sidebar grouping, active state, icon sizing, user summary and bottom navigation styling to match Stitch.
- [x] Keep all current navigation destinations, including Notes, Calendar, Stats and Finance subroutes even where Stitch uses simplified labels.
- [x] Match the fixed 232px desktop sidebar, 68px collapsed tablet rail and 72px mobile bottom bar with safe-area padding.
- [x] Add/retain visible keyboard focus and stable hover states without layout-shifting transforms.
- [x] Verify the shell at 375px, 768px, 1024px and 1440px with no horizontal scroll.

### Task 3: Rebuild the Home dashboard composition

**Files:**
- Modify: `frontend/src/views/Home.vue`
- Reuse: `frontend/src/composables/useUserStats.js`, existing home services/API calls

- [x] Preserve all current Home data loading, check-in action, task completion behavior and navigation links.
- [x] Implement the Stitch hierarchy: progress hero, today summary, primary task area, quick actions, recent goals and habit progress.
- [x] Use real LifeQuest values instead of Stitch demo values such as `capkin`, `Level 24` or hard-coded counts.
- [x] Provide visually complete loaded, empty, loading and error states for tasks, goals and habits.
- [x] Keep desktop two-column behavior and convert to the Stitch-inspired single-column mobile flow with bottom-navigation clearance.
- [x] Verify with both an empty test account and an account containing tasks/goals/habits.

### Task 4: Migrate Todos and Projects

**Files:**
- Modify: `frontend/src/views/Todos.vue`
- Modify: `frontend/src/views/Projects.vue`
- Modify: `frontend/src/views/ProjectDetail.vue`
- Verify: `backend/tests/test_todos.py`, `backend/tests/test_projects.py`

- [x] Map current task tabs, filters, habits, goals and task rows to the Stitch task hierarchy without removing existing categories or actions.
- [x] Add the Stitch-inspired progress summary, priority/difficulty badges, completion styling and mobile add-task affordance.
- [x] Apply Active Projects cards, progress indicators, milestones and detail hierarchy to the existing project model.
- [x] Keep project task move/edit/delete behavior and cross-project validation unchanged.
- [ ] Run focused backend tests and manually verify task/project interactions in the browser.

### Task 5: Migrate Shop, Profile and Backpack

**Files:**
- Modify: `frontend/src/views/Shop.vue`
- Modify: `frontend/src/views/ExchangeHistory.vue`
- Modify: `frontend/src/views/Profile.vue`
- Modify: `frontend/src/views/EditProfile.vue`
- Modify: `frontend/src/views/Backpack.vue`
- Modify: `frontend/src/views/BackpackHistory.vue`

- [ ] Apply Stitch wallet summary, featured reward, reward grid, redeem CTA and item metadata patterns to the existing Shop data.
- [ ] Keep category filtering, search, purchase/refund rules, stock handling and exchange history behavior intact.
- [ ] Apply profile attribute cards, achievements and inventory grouping to current profile/backpack data.
- [ ] Do not copy remote Stitch avatar or reward image URLs as required application assets; use existing resolved-image behavior and safe placeholders.
- [ ] Verify empty inventory, insufficient coins, purchase success and refund states.

### Task 6: Migrate Finance and supporting insight pages

**Files:**
- Modify: `frontend/src/views/Finance.vue`
- Modify: `frontend/src/views/FinanceAccounts.vue`
- Modify: `frontend/src/views/FinanceTransactions.vue`
- Modify: `frontend/src/views/FinanceBudgets.vue`
- Modify: `frontend/src/views/FinanceDebts.vue`
- Modify as needed: `frontend/src/views/Calendar.vue`, `Stats.vue`, `CoinHistory.vue`

- [x] Apply Stitch financial overview hierarchy: wallet total, trend/chart surface, budget/savings card and recent transactions.
- [x] Keep all account, category, transaction, recurring transaction, budget and debt dialogs and validation rules.
- [x] Use existing chart/data components and only change presentation, spacing and empty/error states.
- [x] Ensure dense tables collapse into readable mobile cards or horizontal regions without page-level overflow.
- [ ] Run the existing finance/security test coverage and verify one desktop and one mobile data-filled scenario.

### Task 7: Apply the shared system to Notes, auth and remaining pages

**Files:**
- Modify: `frontend/src/views/Notes.vue`
- Modify: `frontend/src/views/NotebookFileManage.vue`
- Modify: `frontend/src/views/NoteEditor.vue`
- Modify: `frontend/src/views/Login.vue`
- Modify: `frontend/src/views/Register.vue`
- Modify as needed: `frontend/src/views/ExchangeHistory.vue`, `CoinHistory.vue`

- [x] Use shared page headers, surfaces, controls, modal styles and empty states where Stitch has no direct page reference.
- [x] Keep notebook tree navigation, Markdown editing, file migration behavior and auth validation unchanged.
- [x] Ensure auth pages are visually aligned with the Stitch system without requiring a logged-in layout shell.
- [ ] Verify keyboard focus, form labels, error messages and mobile spacing.

### Task 8: Visual QA, regression verification and handoff

**Files:**
- Create or update: `docs/superpowers/reports/2026-08-05-lifequest-stitch-ui-verification.md`

- [x] Run `cd frontend; npm run build`.
- [x] Run `cd backend; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q` with a timeout of at least 180 seconds; expected result is 73 passing tests unless the suite has changed.
- [x] Check `git diff --check`.
- [ ] Browser-verify Home, Todos, Projects, Shop, Profile, Finance, Notes and Login at 375px, 768px, 1024px and 1440px.
- [ ] Check no horizontal overflow, no missing icons, no clipped bottom navigation and no content hidden behind fixed shell elements.
- [ ] Record known limitations, including any remaining bundle-size warning, before committing the implementation.

## Recommended Order and Milestones

1. Tasks 1–2: shared foundation and shell.
2. Task 3: Home dashboard milestone; review visually before continuing.
3. Tasks 4–5: daily-use and reward workflows.
4. Tasks 6–7: finance, notes, auth and supporting pages.
5. Task 8: full responsive QA and handoff.

The Stitch HTML files are reference material only. They should not be copied into `frontend/src` as standalone pages because they contain static demo data, remote generated assets and navigation names that differ from the existing LifeQuest product.
