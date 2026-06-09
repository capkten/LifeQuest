<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <Sidebar :is-open="sidebarOpen" :is-collapsed="sidebarCollapsed" />
    <div class="app-main">
      <Header :title="pageTitle" />
      <main class="app-content">
        <div class="app-content-shell">
          <router-view />
        </div>
      </main>
    </div>

    <!-- Bottom Navigation (mobile only) -->
    <nav class="bottom-nav" aria-label="Main navigation">
      <router-link to="/" class="bottom-nav-item" active-class="bottom-nav-item--active">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
        <span>首页</span>
      </router-link>
      <router-link to="/todos" class="bottom-nav-item" active-class="bottom-nav-item--active">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M9 11l3 3L22 4" />
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
        </svg>
        <span>待办</span>
      </router-link>
      <router-link to="/notes" class="bottom-nav-item" active-class="bottom-nav-item--active">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
        <span>笔记</span>
      </router-link>
      <router-link to="/shop" class="bottom-nav-item" active-class="bottom-nav-item--active">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <path d="M16 10a4 4 0 0 1-8 0" />
        </svg>
        <span>商城</span>
      </router-link>
      <router-link to="/profile" class="bottom-nav-item" active-class="bottom-nav-item--active">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        <span>个人</span>
      </router-link>
    </nav>

    <!-- Mobile sidebar overlay -->
    <div
      v-if="sidebarOpen"
      class="sidebar-overlay"
      @click="sidebarOpen = false"
    ></div>
  </div>
</template>

<script setup>
import { ref, computed, provide, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const route = useRoute()

const sidebarOpen = ref(false)
const sidebarCollapsed = ref(false)
const isMobile = ref(false)
const isTablet = ref(false)

function updateBreakpoints() {
  const w = window.innerWidth
  isMobile.value = w < 768
  isTablet.value = w >= 768 && w < 1200

  if (isMobile.value) {
    sidebarOpen.value = false
    sidebarCollapsed.value = false
  } else if (isTablet.value) {
    sidebarCollapsed.value = true
  } else {
    sidebarCollapsed.value = false
    sidebarOpen.value = false
  }
}

function toggleSidebar() {
  if (isMobile.value) {
    sidebarOpen.value = !sidebarOpen.value
  } else if (isTablet.value) {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
}

// Close mobile sidebar on route change
watch(() => route.path, () => {
  if (isMobile.value) {
    sidebarOpen.value = false
  }
})

onMounted(() => {
  updateBreakpoints()
  window.addEventListener('resize', updateBreakpoints)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateBreakpoints)
})

provide('toggleSidebar', toggleSidebar)
provide('sidebarOpen', sidebarOpen)
provide('isMobile', isMobile)

const pageTitle = computed(() => {
  const titles = {
    Home: '首页',
    Todos: '待办',
    Tasks: '任务',
    Goals: '目标',
    Notes: '笔记',
    Calendar: '日历',
    NotebookFileManage: '笔记本',
    Shop: '商城',
    Backpack: '背包',
    Profile: '个人'
  }
  return titles[route.name] || 'LifeQuest'
})
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(20, 184, 166, 0.12), transparent 28%),
    var(--color-bg);
}

.app-main {
  flex: 1;
  margin-left: var(--sidebar-width);
  min-width: 0;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s ease;
}

.app-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: calc(var(--page-padding-y) + var(--safe-area-bottom));
}

.app-content-shell {
  width: 100%;
  max-width: none;
  padding: var(--page-padding-y) var(--page-padding-x);
  display: flex;
  flex-direction: column;
  gap: var(--page-gap);
}

/* Tablet: sidebar collapsed */
.sidebar-collapsed .app-main {
  margin-left: var(--sidebar-collapsed-width);
}

/* Mobile overlay */
.sidebar-overlay {
  display: none;
}

/* Bottom nav: hidden by default */
.bottom-nav {
  display: none;
}

/* Mobile (<768px) */
@media (max-width: 767px) {
  .app-layout {
    display: block;
  }

  .app-main {
    margin-left: 0;
    min-height: 100vh;
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 90;
  }

  .bottom-nav {
    display: flex;
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    height: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px));
    padding: 8px 10px calc(8px + var(--safe-area-bottom));
    background: rgba(255, 255, 255, 0.94);
    backdrop-filter: blur(12px);
    border-top: 1px solid var(--color-border);
    z-index: 80;
    justify-content: space-around;
    align-items: center;
  }

  .app-content {
    padding-bottom: calc(var(--bottom-nav-height) + 12px + var(--safe-area-bottom));
  }

  .app-content-shell {
    width: 100%;
    padding-bottom: 0;
  }
}

.bottom-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  gap: 4px;
  padding: var(--spacing-xs) var(--spacing-sm);
  color: var(--color-text-tertiary);
  text-decoration: none;
  font-size: 11px;
  font-weight: 500;
  transition: color 0.15s ease;
  border-radius: var(--radius-md);
}

.bottom-nav-item:hover,
.bottom-nav-item--active {
  color: var(--color-primary);
}

.bottom-nav-item svg {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}
</style>
