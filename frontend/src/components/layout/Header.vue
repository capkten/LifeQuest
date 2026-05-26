<template>
  <header class="header">
    <div class="header-left">
      <button
        class="sidebar-toggle"
        aria-label="Toggle sidebar"
        @click="handleToggle"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
      <h2 class="page-title">{{ title }}</h2>
    </div>
    <div class="header-right">
      <div class="user-dropdown" @click="toggleDropdown" @keydown.escape="dropdownOpen = false" @keydown.enter.prevent="toggleDropdown" @keydown.space.prevent="toggleDropdown" ref="dropdownRef" role="button" tabindex="0" :aria-expanded="dropdownOpen" aria-haspopup="true" aria-label="User menu">
        <div class="user-avatar-sm">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="8" r="4" />
            <path d="M20 21a8 8 0 1 0-16 0" />
          </svg>
        </div>
        <span class="user-name">{{ user?.username || '' }}</span>
        <svg class="chevron" :class="{ 'chevron--open': dropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <polyline points="6 9 12 15 18 9" />
        </svg>

        <transition name="dropdown">
          <div v-if="dropdownOpen" class="dropdown-menu" role="menu">
            <router-link to="/profile" class="dropdown-item" role="menuitem" @click="dropdownOpen = false">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <span>个人资料</span>
            </router-link>
            <div class="dropdown-divider" role="separator"></div>
            <button class="dropdown-item dropdown-item--danger" role="menuitem" @click="handleLogout">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              <span>退出登录</span>
            </button>
          </div>
        </transition>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, inject, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../../stores/auth'

const props = defineProps({
  title: {
    type: String,
    default: '首页'
  }
})

const authStore = useAuthStore()
const user = computed(() => authStore.user)

const toggleSidebar = inject('toggleSidebar', () => {})

function handleToggle() {
  toggleSidebar()
}

const dropdownOpen = ref(false)
const dropdownRef = ref(null)

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
}

function handleClickOutside(event) {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target)) {
    dropdownOpen.value = false
  }
}

function handleLogout() {
  dropdownOpen.value = false
  authStore.logout()
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-xl);
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 50;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.sidebar-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.sidebar-toggle:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.sidebar-toggle svg {
  width: 20px;
  height: 20px;
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text);
}

.header-right {
  display: flex;
  align-items: center;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s ease;
  position: relative;
}

.user-dropdown:hover {
  background: var(--color-bg-tertiary);
}

.user-avatar-sm {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar-sm svg {
  width: 18px;
  height: 18px;
  color: #fff;
}

.user-name {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
}

.chevron {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
  transition: transform 0.2s ease;
}

.chevron--open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: var(--spacing-xs);
  min-width: 160px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  z-index: 100;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  transition: all 0.15s ease;
  text-decoration: none;
  border: none;
  background: none;
  width: 100%;
  cursor: pointer;
  font-family: var(--font-family);
}

.dropdown-item:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

.dropdown-item--danger:hover {
  color: var(--color-error);
}

.dropdown-item svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.dropdown-divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--spacing-xs) 0;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Show hamburger on mobile and tablet (<1200px) */
@media (max-width: 1199px) {
  .sidebar-toggle {
    display: flex;
  }
}

/* Reduce padding on small screens */
@media (max-width: 767px) {
  .header {
    padding: 0 var(--spacing-md);
  }

  .user-name {
    display: none;
  }
}
</style>
