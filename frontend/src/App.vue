<template>
  <router-view />
</template>

<style>
:root {
  /* Primary Colors */
  --color-primary: #6C63FF;
  --color-primary-light: #8B85FF;
  --color-primary-dark: #4A42E6;

  /* Secondary Colors */
  --color-secondary: #00D9FF;
  --color-secondary-light: #33E1FF;
  --color-secondary-dark: #00B8D9;

  /* Accent Colors */
  --color-accent: #FF6B6B;
  --color-accent-light: #FF8E8E;
  --color-accent-dark: #E64D4D;

  /* Success Colors */
  --color-success: #51CF66;
  --color-success-light: #8CE99A;
  --color-success-dark: #40C057;

  /* Warning Colors */
  --color-warning: #FFD93D;
  --color-warning-light: #FFE066;
  --color-warning-dark: #FCC419;

  /* Error Colors */
  --color-error: #FF6B6B;
  --color-error-light: #FF8E8E;
  --color-error-dark: #E64D4D;

  /* Neutral Colors */
  --color-bg: #0F0E17;
  --color-bg-secondary: #1A1932;
  --color-bg-tertiary: #232136;
  --color-text: #FFFFFE;
  --color-text-secondary: #A7A9BE;
  --color-text-tertiary: #6B6D7B;
  --color-border: #2E2F3E;
  --color-card: #1A1932;

  /* Typography */
  --font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 2rem;

  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 3rem;

  /* Border Radius */
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --radius-full: 9999px;

  /* Layout */
  --sidebar-width: 260px;
  --sidebar-collapsed-width: 68px;
  --bottom-nav-height: 60px;
  --content-max-width: 1200px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.3);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.3);
  --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.3);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-family);
  background-color: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a {
  color: var(--color-primary);
  text-decoration: none;
  transition: color 0.2s ease;
}

a:hover {
  color: var(--color-primary-light);
}

/* Element Plus Dark Theme Overrides */
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
</style>
