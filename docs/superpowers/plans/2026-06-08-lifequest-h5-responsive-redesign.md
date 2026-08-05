# LifeQuest H5 Responsive Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the existing frontend so the authenticated H5 experience is mobile-first, denser, and easier to use on narrow screens while remaining compatible with tablet, desktop, and the client container.

**Architecture:** Keep the existing Vue 3 route and feature structure intact, but introduce a unified responsive layout layer first, then restyle the priority pages in sequence: Home, Todos, Shop, and Profile. The implementation should concentrate changes in the global layout shell and each page's local template/style blocks, avoiding business-logic rewrites.

**Tech Stack:** Vue 3, Vite, Vue Router, Pinia, Element Plus, scoped CSS in `.vue` single-file components

---

## File Structure

### Layout and global styling

- Modify: `frontend/src/App.vue`
  - Owns global CSS variables, base element styles, and shared responsive tokens.
- Modify: `frontend/src/components/layout/AppLayout.vue`
  - Owns the authenticated shell, content area spacing, and bottom navigation behavior.
- Modify: `frontend/src/components/layout/Header.vue`
  - Owns top bar density, mobile header behavior, and user menu spacing.
- Review only: `frontend/src/components/layout/Sidebar.vue`
  - Keep desktop/tablet behavior intact unless a small compatibility fix is needed.

### Page redesign targets

- Modify: `frontend/src/views/Home.vue`
  - Merge the mobile hero/check-in structure, compress stats, and promote today's actionable items.
- Modify: `frontend/src/views/Todos.vue`
  - Rebuild the mobile page header, tabs, list cards, and action density.
- Modify: `frontend/src/views/Shop.vue`
  - Rebuild the mobile summary/actions strip and tighten item cards.
- Modify: `frontend/src/views/Profile.vue`
  - Compress the profile hero, stats, and content group density.

### Verification

- Run: `frontend/package.json`
  - Use `npm run build` for static verification.
- Manual check targets:
  - `frontend/src/views/Home.vue`
  - `frontend/src/views/Todos.vue`
  - `frontend/src/views/Shop.vue`
  - `frontend/src/views/Profile.vue`
  - `frontend/src/components/layout/AppLayout.vue`
  - `frontend/src/components/layout/Header.vue`

## Task 1: Establish the global responsive design layer

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/layout/AppLayout.vue`
- Modify: `frontend/src/components/layout/Header.vue`

- [x] **Step 1: Capture the current global layout rules before editing**

Read:

```powershell
@'
from pathlib import Path
for rel in [
    "src/App.vue",
    "src/components/layout/AppLayout.vue",
    "src/components/layout/Header.vue"
]:
    print(f"===== {rel} =====")
    p = Path(rel)
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if i > 260:
            break
        print(f"{i}:{line}")
'@ | python -
```

Expected: You have the current variables, shell structure, and header rules in view before changing them.

- [x] **Step 2: Define the mobile-first global token changes in `src/App.vue`**

Update the root variables so mobile spacing, font sizing, shell sizing, and shared surface styling are explicit. Keep the current color family but tighten the density.

```css
:root {
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 0.9375rem;
  --font-size-lg: 1rem;
  --font-size-xl: 1.125rem;
  --font-size-2xl: 1.375rem;
  --font-size-3xl: 1.75rem;

  --spacing-2xs: 0.25rem;
  --spacing-xs: 0.5rem;
  --spacing-sm: 0.75rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.25rem;
  --spacing-xl: 1.5rem;
  --spacing-2xl: 2rem;

  --page-padding-x: 16px;
  --page-padding-y: 16px;
  --content-max-width: 1200px;
  --header-height: 56px;
  --bottom-nav-height: 64px;
  --surface-radius: 18px;
  --surface-radius-sm: 14px;
  --surface-padding: 16px;
}

@media (min-width: 768px) {
  :root {
    --page-padding-x: 24px;
    --page-padding-y: 20px;
    --header-height: 60px;
    --surface-padding: 20px;
  }
}

@media (min-width: 1200px) {
  :root {
    --page-padding-x: 32px;
    --page-padding-y: 24px;
    --header-height: 64px;
    --surface-padding: 24px;
  }
}
```

- [x] **Step 3: Add shared global utility surfaces and page rhythm in `src/App.vue`**

Introduce shared page and card primitives that page-local styles can align to.

```css
body {
  font-family: var(--font-family);
  background: var(--color-bg);
  color: var(--color-text);
  overflow-x: hidden;
}

#app {
  min-height: 100vh;
}

.page-shell {
  width: min(100%, var(--content-max-width));
  margin: 0 auto;
  padding: var(--page-padding-y) var(--page-padding-x);
}

.surface-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  box-shadow: var(--shadow-sm);
}

.compact-section {
  display: grid;
  gap: var(--spacing-md);
}
```

- [x] **Step 4: Rework `AppLayout.vue` so mobile gets a real single-column flow**

Keep the current desktop sidebar logic, but make the mobile content area control its own padding and safe-area behavior.

```css
.app-layout {
  min-height: 100vh;
  background: var(--color-bg);
}

.app-main {
  flex: 1;
  margin-left: var(--sidebar-width);
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.app-content {
  flex: 1;
  min-width: 0;
  padding-bottom: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px));
}

@media (max-width: 767px) {
  .app-layout {
    display: block;
  }

  .app-main {
    margin-left: 0;
    min-height: 100vh;
  }

  .app-content {
    padding-bottom: calc(var(--bottom-nav-height) + 12px + env(safe-area-inset-bottom, 0px));
  }
}
```

- [x] **Step 5: Tighten bottom navigation density in `AppLayout.vue`**

Keep the same destinations, but make the mobile nav lighter and safer for touch.

```css
.bottom-nav {
  display: flex;
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px));
  padding: 8px 10px calc(8px + env(safe-area-inset-bottom, 0px));
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--color-border);
}

.bottom-nav-item {
  min-width: 44px;
  min-height: 44px;
  gap: 4px;
  font-size: 11px;
}
```

- [x] **Step 6: Compress `Header.vue` for mobile without breaking desktop**

Adjust the header to stop competing with page-level content on phones.

```css
.header {
  height: var(--header-height);
  padding: 0 var(--page-padding-x);
}

.page-title {
  font-size: var(--font-size-lg);
  line-height: 1.2;
}

.user-dropdown {
  padding: 6px 10px;
}

@media (max-width: 767px) {
  .user-name,
  .chevron {
    display: none;
  }

  .header-left {
    gap: var(--spacing-sm);
  }

  .sidebar-toggle {
    display: inline-flex;
    width: 40px;
    height: 40px;
  }
}
```

- [x] **Step 7: Run the frontend build after the shell changes**

Run:

```powershell
npm run build
```

Expected: Vite production build succeeds with no new CSS/template errors.

- [ ] **Step 8: Commit the shell redesign slice**

```bash
git add src/App.vue src/components/layout/AppLayout.vue src/components/layout/Header.vue
git commit -m "feat(frontend): add mobile-first layout shell"
```

## Task 2: Redesign the Home page for mobile-first density

**Files:**
- Modify: `frontend/src/views/Home.vue`

- [x] **Step 1: Inspect the current Home structure before moving blocks**

Read:

```powershell
@'
from pathlib import Path
p = Path("src/views/Home.vue")
for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
    if i > 420:
        break
    print(f"{i}:{line}")
'@ | python -
```

Expected: You can identify the check-in card, welcome card, stats grid, recent sections, and daily summary sections.

- [x] **Step 2: Merge the welcome and check-in regions into a compact mobile hero**

Refactor the top section so one compact surface owns the greeting, streak/check-in state, and quick user summary.

```vue
<section class="home-hero surface-card">
  <div class="home-hero-main">
    <div>
      <p class="hero-eyebrow">LifeQuest</p>
      <h1 class="hero-title">欢迎回来，{{ user?.username || '冒险者' }}</h1>
      <p class="hero-subtitle">先处理今天最重要的事项。</p>
    </div>
    <button
      v-if="!checkinStatus?.checked_in"
      class="hero-checkin-btn"
      :disabled="checkinLoading"
      @click="doCheckin"
    >
      {{ checkinLoading ? '签到中...' : '签到' }}
    </button>
    <div v-else class="hero-checkin-state">今日已签到</div>
  </div>
  <div class="hero-meta">
    <span>Lv. {{ user?.level || 1 }}</span>
    <span>{{ user?.coins || 0 }} 金币</span>
    <span>连续 {{ checkinStatus?.streak || 0 }} 天</span>
  </div>
</section>
```

- [x] **Step 3: Reduce the stats cards to a thin mobile summary grid**

Keep the same metrics, but remove the oversized card feel on phones.

```css
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.stat-card {
  padding: 14px 12px;
  border-radius: var(--surface-radius-sm);
}

.stat-card-icon {
  width: 28px;
  height: 28px;
}

.stat-card-value {
  font-size: 1.1rem;
  font-weight: 700;
}
```

- [x] **Step 4: Move `今日任务` ahead of the recent lists in the template**

Place the daily summary immediately after the compact hero/stats area so the first scroll contains today's actions rather than passive summaries.

```vue
<div class="compact-section">
  <section class="daily-card surface-card">...</section>
  <section class="content-section surface-card">最近任务...</section>
  <section class="content-section surface-card">最近目标...</section>
</div>
```

- [x] **Step 5: Convert daily, task, and goal rows into flatter mobile list items**

Reduce card thickness and allow secondary metadata to wrap cleanly.

```css
.daily-item,
.task-item,
.goal-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(186, 230, 253, 0.7);
}

.daily-item:last-child,
.task-item:last-child,
.goal-item:last-child {
  border-bottom: none;
}
```

- [x] **Step 6: Add desktop-preserving overrides only where the new mobile structure needs expansion**

Use upward breakpoints so the desktop page still feels roomy.

```css
@media (min-width: 768px) {
  .stats-grid {
    gap: 14px;
  }

  .home-hero {
    padding: 20px;
  }
}

@media (min-width: 1200px) {
  .content-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--spacing-lg);
  }
}
```

- [x] **Step 7: Run the frontend build after Home changes**

Run:

```powershell
npm run build
```

Expected: Build succeeds and the updated `Home.vue` template compiles cleanly.

- [ ] **Step 8: Commit the Home redesign**

```bash
git add src/views/Home.vue
git commit -m "feat(frontend): redesign home page for mobile"
```

## Task 3: Redesign the Todos page for mobile task density

**Files:**
- Modify: `frontend/src/views/Todos.vue`

- [x] **Step 1: Capture the current Todos page structure**

Read:

```powershell
@'
from pathlib import Path
p = Path("src/views/Todos.vue")
for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
    if i > 700:
        break
    print(f"{i}:{line}")
'@ | python -
```

Expected: You can see the header, tabs, filter, card structure, footer stats, dialogs, and action groups.

- [x] **Step 2: Compress the page header and keep a single primary action**

Make the mobile header short and high-signal.

```vue
<div class="page-header">
  <div class="header-copy">
    <h2 class="page-title">待办</h2>
    <span class="item-count">{{ currentList.length }} {{ activeTab === 'habits' ? '个习惯' : activeTab === 'tasks' ? '个任务' : '个目标' }}</span>
  </div>
  <button class="btn-create" @click="showCreateDialog = true">
    新建{{ activeTabSingular }}
  </button>
</div>
```

- [x] **Step 3: Restyle the tab strip into a compact segmented mobile control**

Preserve the same tabs, but remove the heavy card feel.

```css
.tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding: 6px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--color-border);
  border-radius: 16px;
}

.tab-btn {
  min-height: 44px;
  padding: 10px 8px;
  border-radius: 12px;
}
```

- [x] **Step 4: Rebuild the todo cards so the first row holds only essential information**

Keep completion as the primary action, push edit/delete into a secondary action cluster, and allow metadata to wrap below.

```vue
<div class="todo-card">
  <div class="todo-card-mainline">
    <button class="complete-btn">...</button>
    <div class="todo-card-copy">
      <h3 class="todo-card-title">{{ task.title }}</h3>
      <p v-if="task.description" class="todo-card-desc">{{ task.description }}</p>
    </div>
    <div class="todo-card-side">
      <span class="status-badge" :class="'status-badge--' + task.status">{{ formatStatus(task.status) }}</span>
      <button class="action-btn action-btn--more" @click="openEditDialog(task, 'tasks')">...</button>
    </div>
  </div>
  <div class="todo-card-meta-row">...</div>
</div>
```

- [x] **Step 5: Flatten the metadata and reward rows for mobile**

The reward and difficulty area should stop inflating card height.

```css
.todo-card-meta,
.todo-card-stats,
.todo-card-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.todo-card {
  padding: 14px;
  border-radius: var(--surface-radius-sm);
}

.action-buttons {
  gap: 6px;
}
```

- [x] **Step 6: Ensure project filters and dialogs inherit the compact mobile rhythm**

Tighten the filter block and dialog spacing rather than leaving them in desktop proportions.

```css
.project-filter,
.dialog-body {
  gap: 12px;
}

.dialog {
  width: min(100% - 24px, 560px);
  border-radius: 20px;
}
```

- [x] **Step 7: Run the frontend build after Todos changes**

Run:

```powershell
npm run build
```

Expected: Build succeeds and the updated tab/list/dialog markup compiles.

- [ ] **Step 8: Commit the Todos redesign**

```bash
git add src/views/Todos.vue
git commit -m "feat(frontend): redesign todos page for mobile"
```

## Task 4: Redesign the Shop page for mobile purchase flow

**Files:**
- Modify: `frontend/src/views/Shop.vue`

- [x] **Step 1: Capture the current Shop page structure**

Read:

```powershell
@'
from pathlib import Path
p = Path("src/views/Shop.vue")
for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
    if i > 520:
        break
    print(f"{i}:{line}")
'@ | python -
```

Expected: You can identify the page header, balance display, history/create actions, item cards, and dialogs.

- [x] **Step 2: Rebuild the page top area into a compact summary and action stack**

Put the balance first, keep one clear primary action, and demote history for small screens.

```vue
<div class="page-header">
  <div class="shop-summary surface-card">
    <span class="balance-label">当前金币</span>
    <strong class="balance-value">{{ user?.coins || 0 }}</strong>
  </div>
  <div class="shop-actions">
    <button class="btn-history" @click="$router.push('/shop/history')">兑换历史</button>
    <button class="btn-create" @click="showCreateDialog = true">新建商品</button>
  </div>
</div>
```

- [x] **Step 3: Tighten the item card hierarchy**

Move the product icon and ownership actions into a smaller header so the card emphasizes name, price, stock, and purchase state.

```css
.items-grid {
  display: grid;
  gap: 12px;
}

.item-card {
  padding: 14px;
  border-radius: var(--surface-radius-sm);
}

.item-card-header,
.item-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
```

- [x] **Step 4: Demote author edit/delete controls below the main purchase information**

Avoid having management actions fight with the purchase CTA on narrow screens.

```vue
<div class="item-card-admin" v-if="user && item.created_by === user.id">
  <button class="btn-icon btn-icon--edit" @click.stop="openEditDialog(item)">编辑</button>
  <button class="btn-icon btn-icon--delete" @click.stop="openDeleteDialog(item)">删除</button>
</div>
```

- [x] **Step 5: Make the purchase CTA full-width on mobile and inline on larger screens**

```css
.btn-purchase {
  width: 100%;
  min-height: 44px;
}

@media (min-width: 768px) {
  .btn-purchase {
    width: auto;
    min-width: 120px;
  }
}
```

- [x] **Step 6: Run the frontend build after Shop changes**

Run:

```powershell
npm run build
```

Expected: Build succeeds and the updated item card structure compiles.

- [ ] **Step 7: Commit the Shop redesign**

```bash
git add src/views/Shop.vue
git commit -m "feat(frontend): redesign shop page for mobile"
```

## Task 5: Redesign the Profile page for mobile hierarchy

**Files:**
- Modify: `frontend/src/views/Profile.vue`

- [x] **Step 1: Capture the current Profile page structure**

Read:

```powershell
@'
from pathlib import Path
p = Path("src/views/Profile.vue")
for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
    if i > 720:
        break
    print(f"{i}:{line}")
'@ | python -
```

Expected: You can locate the profile hero, stat cards, achievements, titles modal, and toast regions.

- [x] **Step 2: Compress the profile hero into a compact summary surface**

Keep the same data, but reorganize it so avatar, name, title, and level appear immediately without a tall decorative block.

```vue
<section class="profile-hero surface-card">
  <div class="profile-hero-main">
    <div class="profile-avatar">...</div>
    <div class="profile-copy">
      <h1 class="profile-name">{{ user?.username }}</h1>
      <p class="profile-title">{{ user?.title || '冒险者' }}</p>
      <div class="profile-meta">
        <span>Lv. {{ user?.level || 1 }}</span>
        <span>{{ user?.coins || 0 }} 金币</span>
      </div>
    </div>
  </div>
</section>
```

- [x] **Step 3: Reduce the stats region to a compact multi-row summary**

Avoid oversized desktop cards on phones.

```css
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.stat-card {
  padding: 14px;
}

@media (min-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
```

- [x] **Step 4: Tighten achievements and titles sections into lighter cards**

Use smaller cards, shorter descriptions, and more compact gaps so the page stops feeling gallery-like on mobile.

```css
.achievements-grid,
.titles-list {
  gap: 10px;
}

.achievement-card,
.title-item {
  padding: 12px;
  border-radius: var(--surface-radius-sm);
}
```

- [x] **Step 5: Resize the titles modal for mobile**

The modal must fit narrow screens cleanly and allow internal scrolling.

```css
.dialog {
  width: min(100% - 24px, 640px);
  max-height: min(80vh, 720px);
}

.dialog-body {
  overflow-y: auto;
}
```

- [x] **Step 6: Run the frontend build after Profile changes**

Run:

```powershell
npm run build
```

Expected: Build succeeds and the profile modal/cards compile cleanly.

- [ ] **Step 7: Commit the Profile redesign**

```bash
git add src/views/Profile.vue
git commit -m "feat(frontend): redesign profile page for mobile"
```

## Task 6: Perform responsive regression and polish

**Files:**
- Verify: `frontend/src/App.vue`
- Verify: `frontend/src/components/layout/AppLayout.vue`
- Verify: `frontend/src/components/layout/Header.vue`
- Verify: `frontend/src/views/Home.vue`
- Verify: `frontend/src/views/Todos.vue`
- Verify: `frontend/src/views/Shop.vue`
- Verify: `frontend/src/views/Profile.vue`

- [x] **Step 1: Run a final production build**

Run:

```powershell
npm run build
```

Expected: Final build passes with no new warnings that indicate broken templates or imports.

- [x] **Step 2: Manually inspect the required breakpoints**

Check the authenticated app at `375px`, `768px`, `1024px`, and `1440px`.

Use this checklist:

```text
375px:
- no horizontal scroll
- header fits in one row
- bottom nav does not cover content
- home first screen shows greeting + action + daily items quickly
- todos cards no longer feel desktop-sized
- shop purchase CTA is easy to tap
- profile hero and stats fit without large dead space

768px:
- mobile density starts relaxing
- filters, tabs, and action groups still wrap cleanly

1024px:
- layout remains readable with sidebar present
- page modules are not awkwardly stretched

1440px:
- desktop shell still works
- spacing is not collapsed from mobile defaults
```

- [x] **Step 3: Fix any discovered responsive regressions before closing**

Apply only targeted polish for issues found in the verification pass, for example:

```css
@media (max-width: 767px) {
  .page-header,
  .header-right,
  .todo-card-mainline,
  .item-card-footer {
    align-items: stretch;
  }
}
```

- [x] **Step 4: Record the final implementation state**

Run:

```powershell
git status --short
```

Expected: Only the intended frontend/layout files remain modified before the final commit.

- [ ] **Step 5: Commit the regression fixes**

```bash
git add src/App.vue src/components/layout/AppLayout.vue src/components/layout/Header.vue src/views/Home.vue src/views/Todos.vue src/views/Shop.vue src/views/Profile.vue
git commit -m "fix(frontend): polish responsive h5 redesign"
```

## Self-Review

### Spec coverage

- Global mobile-first layout layer: covered by Task 1.
- Home redesign: covered by Task 2.
- Todos redesign: covered by Task 3.
- Shop redesign: covered by Task 4.
- Profile redesign: covered by Task 5.
- Multi-breakpoint verification and desktop safety: covered by Task 6.

### Placeholder scan

- No `TODO`, `TBD`, or “similar to previous task” placeholders remain.
- Every task includes file targets, concrete commands, and implementation examples.

### Type consistency

- The plan uses existing file names and route/page names from the repo: `Home.vue`, `Todos.vue`, `Shop.vue`, `Profile.vue`, `AppLayout.vue`, and `Header.vue`.
- Shared CSS primitives (`page-shell`, `surface-card`, `compact-section`) are introduced first in Task 1 and reused consistently afterward.
