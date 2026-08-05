<template>
  <router-view />
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --color-primary: #0EA5E9;
  --color-primary-light: #38BDF8;
  --color-primary-dark: #0284C7;
  --color-secondary: #1D4ED8;
  --color-secondary-light: #60A5FA;
  --color-secondary-dark: #1E3A8A;
  --color-accent: #10B981;
  --color-accent-light: #6EE7B7;
  --color-accent-dark: #047857;
  --color-success: #22C55E;
  --color-success-light: #86EFAC;
  --color-success-dark: #16A34A;
  --color-warning: #F59E0B;
  --color-warning-light: #FCD34D;
  --color-warning-dark: #D97706;
  --color-error: #EF4444;
  --color-error-light: #FCA5A5;
  --color-error-dark: #DC2626;
  --color-bg: #F4F8FB;
  --color-bg-secondary: #FFFFFF;
  --color-bg-tertiary: #E8F5FA;
  --color-bg-elevated: #FFFFFF;
  --color-text: #16324F;
  --color-text-secondary: #5B7185;
  --color-text-tertiary: #8AA0B2;
  --color-border: #D9E7EF;
  --color-border-strong: #A8D7E8;
  --color-card: #FFFFFF;
  --font-family: 'DM Sans', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-family-display: 'Space Grotesk', 'DM Sans', sans-serif;
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
  --spacing-3xl: 3rem;
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --radius-2xl: 1.25rem;
  --radius-full: 9999px;
  --sidebar-width: 232px;
  --sidebar-collapsed-width: 68px;
  --page-padding-x: 16px;
  --page-padding-y: 16px;
  --page-gap: 14px;
  --content-max-width: 1200px;
  --content-max-width-wide: 1320px;
  --header-height: 56px;
  --bottom-nav-height: 64px;
  --surface-radius: 18px;
  --surface-radius-sm: 14px;
  --surface-padding: 16px;
  --touch-target-min: 44px;
  --touch-target-gap: 8px;
  --safe-area-top: env(safe-area-inset-top, 0px);
  --safe-area-bottom: env(safe-area-inset-bottom, 0px);
  --shadow-sm: 0 1px 2px rgba(22, 50, 79, 0.04);
  --shadow-md: 0 8px 24px rgba(22, 50, 79, 0.08);
  --shadow-lg: 0 14px 34px rgba(22, 50, 79, 0.1);
  --shadow-xl: 0 22px 48px rgba(22, 50, 79, 0.14);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  min-height: 100vh;
  font-family: var(--font-family);
  background-color: var(--color-bg);
  color: var(--color-text);
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
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

button,
a,
[role='button'] {
  -webkit-tap-highlight-color: transparent;
}

button {
  font-family: var(--font-family);
}

.compact-section {
  display: grid;
  gap: var(--spacing-md);
}

@media (min-width: 768px) {
  :where(
    .todos-page,
    .shop-page,
    .projects-page,
    .profile-page,
    .notes-page,
    .calendar-page,
    .finance-page,
    .stats-page,
    .backpack-page,
    .history-page,
    .coin-history-page,
    .project-detail-page,
    .edit-profile-page,
    .note-editor-page,
    .file-manager
  ) {
    width: 100%;
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
  }
}

h1,
h2,
h3,
.page-title,
.section-title {
  font-family: var(--font-family-display);
  letter-spacing: -0.02em;
}

@media (min-width: 768px) {
  :where(.page-header) {
    min-height: 46px;
    margin-bottom: 16px !important;
  }

  :where(.page-title) {
    font-size: clamp(1.2rem, 1.1rem + 0.25vw, 1.5rem);
    line-height: 1.15;
  }
}

:where(
  .project-card,
  .todo-card,
  .item-card,
  .stat-card,
  .achievement-card,
  .title-item,
  .node-card,
  .summary-card,
  .account-card,
  .budget-card,
  .debt-card,
  .overview-card,
  .chart-section,
  .notebook-card,
  .search-result-card,
  .calendar-body,
  .budgets-card,
  .transactions-card
) {
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
}

:where(.project-card, .todo-card, .item-card, .notebook-card) {
  min-width: 0;
}

:where(.project-card-name, .todo-card-title, .item-card-name, .notebook-name) {
  overflow-wrap: anywhere;
}

:where(.project-card, .todo-card, .item-card, .node-card) {
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

:where(.project-card, .todo-card, .item-card, .node-card):hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

:where(
  .tab-count--tasks,
  .tab-count--goals,
  .tab-count--gear,
  .tab-count--collectible,
  .frequency-badge--daily,
  .frequency-badge--weekly,
  .status-badge--active,
  .task-status-badge--in_progress,
  .item-tag--category,
  .category-chip--active,
  .node-icon--folder,
  .overview-card--tasks .overview-icon,
  .overview-card--active .overview-icon,
  .stat-card--level .stat-card-icon,
  .stat-card--exp .stat-card-icon,
  .title-item--active
) {
  background: rgba(14, 165, 233, 0.12) !important;
}

:where(
  .tab-count--tasks,
  .tab-count--gear,
  .frequency-badge--daily,
  .status-badge--active,
  .task-status-badge--in_progress
) {
  color: var(--color-primary-dark) !important;
}

:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.el-button,
.el-input__wrapper,
.el-select__wrapper,
.el-textarea__inner {
  border-radius: var(--radius-lg);
}

.el-button {
  min-height: var(--touch-target-min);
  padding: 0.625rem 1rem;
  font-weight: 600;
}

@media (max-width: 767px) {
  :root {
    --font-size-2xl: 1.125rem;
  }

  .el-button {
    white-space: nowrap;
  }
}

@media (min-width: 768px) {
  :root {
    --page-padding-x: 24px;
    --page-padding-y: 20px;
    --page-gap: 20px;
    --header-height: 60px;
    --surface-padding: 20px;
  }
}

@media (min-width: 1200px) {
  :root {
    --page-padding-x: 32px;
    --page-padding-y: 24px;
    --page-gap: 18px;
    --header-height: 64px;
    --surface-padding: 24px;
  }

  :where(.projects-grid, .notebook-grid, .backpack-page .items-grid) {
    gap: 14px;
  }
}

a {
  color: var(--color-primary);
  text-decoration: none;
  transition: color 0.2s ease;
}

a:hover {
  color: var(--color-primary-light);
}

/* Element Plus Light Theme Overrides */
.el-button--primary {
  --el-button-bg-color: var(--color-primary);
  --el-button-border-color: var(--color-primary);
  --el-button-hover-bg-color: var(--color-primary-light);
  --el-button-hover-border-color: var(--color-primary-light);
  --el-button-active-bg-color: var(--color-primary-dark);
  --el-button-active-border-color: var(--color-primary-dark);
}

.el-input__wrapper {
  background-color: var(--color-bg-secondary) !important;
  box-shadow: 0 0 0 1px var(--color-border) inset !important;
}

.el-input__inner {
  color: var(--color-text) !important;
}

.el-input__inner::placeholder {
  color: var(--color-text-tertiary) !important;
}

.el-form-item__label {
  color: var(--color-text-secondary) !important;
}

.el-card {
  background-color: var(--color-card) !important;
  border-color: var(--color-border) !important;
  border-radius: var(--radius-xl) !important;
  box-shadow: var(--shadow-sm) !important;
}

.el-message-box {
  background-color: var(--color-bg-secondary) !important;
  border-color: var(--color-border) !important;
}

.el-message-box__title {
  color: var(--color-text) !important;
}

.el-message-box__message {
  color: var(--color-text-secondary) !important;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
