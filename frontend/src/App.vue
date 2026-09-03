<template>
  <UpdatePrompt />
  <router-view />
</template>

<script setup>
import UpdatePrompt from './components/layout/UpdatePrompt.vue'
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --color-primary: #0284C7;
  --color-primary-light: #38BDF8;
  --color-primary-dark: #0369A1;
  --color-secondary: #2563EB;
  --color-secondary-light: #60A5FA;
  --color-secondary-dark: #1D4ED8;
  --color-accent: #10B981;
  --color-accent-light: #34D399;
  --color-accent-dark: #059669;
  --color-success: #10B981;
  --color-success-light: #A7F3D0;
  --color-success-dark: #047857;
  --color-warning: #F59E0B;
  --color-warning-light: #FDE68A;
  --color-warning-dark: #D97706;
  --color-error: #EF4444;
  --color-error-light: #FECACA;
  --color-error-dark: #DC2626;
  --color-bg: #F8FAFC;
  --color-bg-secondary: #FFFFFF;
  --color-bg-tertiary: #F1F5F9;
  --color-bg-elevated: #FFFFFF;
  --color-text: #0F172A;
  --color-text-secondary: #64748B;
  --color-text-tertiary: #94A3B8;
  --color-border: #E2E8F0;
  --color-border-strong: #CBD5E1;
  --color-card: #FFFFFF;
  --color-surface: #FFFFFF;
  --color-surface-low: #F8FAFC;
  --color-surface-container: #F1F5F9;
  --color-surface-high: #E2E8F0;
  --color-surface-variant: #E2E8F0;
  --color-on-surface: #0F172A;
  --color-on-surface-variant: #475569;
  --color-outline: #64748B;
  --color-outline-variant: #CBD5E1;
  --color-hero-start: #0F172A;
  --color-hero-end: #0284C7;
  --color-gold: #F59E0B;
  --color-purple: #8B5CF6;
  --font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', 'DM Sans', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --font-family-display: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', 'Space Grotesk', 'DM Sans', sans-serif;
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
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 2.5rem;
  --spacing-3xl: 4rem;
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --radius-2xl: 1.25rem;
  --radius-full: 9999px;
  --sidebar-width: 240px;
  --sidebar-collapsed-width: 72px;
  --page-padding-x: clamp(16px, 2.5vw, 32px);
  --page-padding-y: clamp(16px, 2.5vw, 28px);
  --page-gap: clamp(16px, 2vw, 24px);
  --content-max-width: 1400px;
  --content-max-width-wide: 1520px;
  --header-height: 60px;
  --bottom-nav-height: 64px;
  --surface-radius: 16px;
  --surface-radius-sm: 10px;
  --surface-padding: clamp(18px, 2vw, 26px);
  --touch-target-min: 44px;
  --touch-target-android: 48px;
  --touch-target-gap: 8px;
  --safe-area-top: env(safe-area-inset-top, 0px);
  --safe-area-bottom: env(safe-area-inset-bottom, 0px);
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.03);
  --shadow-md: 0 4px 12px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
  --shadow-lg: 0 12px 24px -4px rgba(15, 23, 42, 0.07), 0 4px 10px -2px rgba(15, 23, 42, 0.03);
  --shadow-xl: 0 20px 32px -6px rgba(15, 23, 42, 0.1), 0 8px 16px -3px rgba(15, 23, 42, 0.05);
  --shadow-glow-primary: 0 0 24px rgba(2, 132, 199, 0.22);
  --shadow-glow-accent: 0 0 24px rgba(16, 185, 129, 0.22);
  --glass-bg: rgba(255, 255, 255, 0.82);
  --glass-border: rgba(255, 255, 255, 0.7);
  --glass-blur: blur(20px) saturate(180%);
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-bounce: 300ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  min-height: 100vh;
  min-height: 100dvh;
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
  min-height: 100dvh;
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

.stitch-surface {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  box-shadow: var(--shadow-sm);
}

.stitch-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary);
  color: var(--color-primary-dark);
  font-size: var(--font-size-xs);
  font-weight: 600;
  white-space: nowrap;
}

.stitch-progress {
  height: 6px;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary);
}

.stitch-progress > span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  transition: width 300ms ease;
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

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
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
    --bottom-nav-height: 72px;
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
