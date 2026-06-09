<template>
  <router-view />
</template>

<style>
:root {
  --color-primary: #0EA5E9;
  --color-primary-light: #38BDF8;
  --color-primary-dark: #0284C7;
  --color-secondary: #6366F1;
  --color-secondary-light: #818CF8;
  --color-secondary-dark: #4F46E5;
  --color-accent: #059669;
  --color-accent-light: #34D399;
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
  --color-bg: #F0F9FF;
  --color-bg-secondary: #FFFFFF;
  --color-bg-tertiary: #E0F2FE;
  --color-bg-elevated: #F8FDFF;
  --color-text: #0C4A6E;
  --color-text-secondary: #64748B;
  --color-text-tertiary: #94A3B8;
  --color-border: #BAE6FD;
  --color-border-strong: #7DD3FC;
  --color-card: #FFFFFF;
  --font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-family-display: 'Cinzel', 'Cormorant Garamond', serif;
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
  --sidebar-width: 260px;
  --sidebar-collapsed-width: 68px;
  --page-padding-x: 16px;
  --page-padding-y: 16px;
  --page-gap: 16px;
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
  --shadow-sm: 0 1px 2px rgba(14, 165, 233, 0.06);
  --shadow-md: 0 10px 30px rgba(14, 165, 233, 0.08);
  --shadow-lg: 0 16px 40px rgba(14, 165, 233, 0.12);
  --shadow-xl: 0 24px 48px rgba(14, 165, 233, 0.14);
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
  line-height: 1.6;
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

.compact-section {
  display: grid;
  gap: var(--spacing-md);
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
    --page-gap: 24px;
    --header-height: 64px;
    --surface-padding: 24px;
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
