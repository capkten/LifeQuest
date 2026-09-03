<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <Sidebar :is-open="sidebarOpen" :is-collapsed="sidebarCollapsed" />
    <div class="app-main">
      <Header :title="pageTitle" />
      <main class="app-content" :class="{ 'app-content--full-width': isFullWidthRoute }">
        <div class="app-content-shell" :class="{ 'app-content-shell--full-width': isFullWidthRoute }">
          <router-view />
        </div>
      </main>
    </div>

    <!-- Bottom Navigation (mobile only) -->
    <nav class="bottom-nav" aria-label="主导航">
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
      <router-link to="/cultivation" class="bottom-nav-item" active-class="bottom-nav-item--active">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        <span>修炼</span>
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

const isFullWidthRoute = computed(() => {
  const fullWidthNames = ['NotebookFileManage', 'NotebookWorkspaceView', 'NotebookWorkspaceEdit', 'NoteEditor', 'NoteSync']
  return fullWidthNames.includes(route.name) || String(route.path).startsWith('/notes/')
})

const pageTitle = computed(() => {
  const titles = {
    Home: '首页',
    Todos: '待办',
    Tasks: '任务',
    Goals: '目标',
    Notes: '笔记',
    NoteSync: '文件夹同步',
    Calendar: '日历',
    WeeklyReview: '周复盘',
    NotebookFileManage: '笔记本',
    Shop: '商城',
    Backpack: '背包',
    Profile: '个人',
    Cultivation: '修炼',
    World: '凡界',
    Sects: '宗门',
    Techniques: '功法',
    Npcs: '人物关系',
    Tribulations: '渡劫'
  }
  return titles[route.name] || 'LifeQuest'
})
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--color-bg);
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
  overflow-x: clip;
  padding-bottom: calc(var(--page-padding-y) + var(--safe-area-bottom));
}

.app-content-shell {
  width: 100%;
  max-width: var(--content-max-width);
  margin: 0 auto;
  min-width: 0;
  padding: var(--page-padding-y) var(--page-padding-x);
  display: flex;
  flex-direction: column;
  gap: var(--page-gap);
}

.app-content--full-width {
  padding-bottom: 0;
}

.app-content-shell--full-width {
  max-width: 100%;
  margin: 0;
  padding: 8px 16px 16px;
  gap: 0;
}

.app-content-shell > * {
  min-width: 0;
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
    min-height: 100dvh;
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
    padding: 6px 12px calc(6px + var(--safe-area-bottom));
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-top: 1px solid rgba(217, 231, 239, 0.8);
    box-shadow: 0 -4px 20px rgba(22, 50, 79, 0.05);
    z-index: 80;
    justify-content: space-around;
    align-items: center;
  }

  .app-content {
    --mobile-content-bottom-inset: calc(var(--bottom-nav-height) + 72px + var(--safe-area-bottom));
    padding-bottom: var(--mobile-content-bottom-inset);
  }

  .app-content-shell {
    width: 100%;
    max-width: none;
    margin: 0;
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
  gap: 3px;
  padding: 5px 10px;
  color: var(--color-text-tertiary);
  text-decoration: none;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.02em;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: var(--radius-xl);
}

.bottom-nav-item:hover,
.bottom-nav-item--active {
  color: var(--color-primary-dark);
  background: var(--color-bg-tertiary);
  transform: translateY(-1px);
}

.bottom-nav-item svg {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.bottom-nav-item--active svg {
  transform: scale(1.08);
}

@media (pointer: coarse) {
  .bottom-nav-item {
    min-width: var(--touch-target-android);
    min-height: var(--touch-target-android);
  }
}
</style>
