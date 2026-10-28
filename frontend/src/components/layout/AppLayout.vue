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
      <router-link
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.to"
        class="bottom-nav-item"
        :class="{ 'bottom-nav-item--active': activeTab === tab.key }"
        :aria-current="activeTab === tab.key ? 'page' : undefined"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path v-for="(d, index) in tab.paths" :key="index" :d="d" />
          <circle v-for="(c, index) in tab.circles || []" :key="`c${index}`" :cx="c[0]" :cy="c[1]" :r="c[2]" />
          <line v-for="(l, index) in tab.lines || []" :key="`l${index}`" :x1="l[0]" :y1="l[1]" :x2="l[2]" :y2="l[3]" />
        </svg>
        <span>{{ tab.label }}</span>
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
import { useAndroidBackButton } from '../../composables/useAndroidBackButton'

const route = useRoute()

useAndroidBackButton()

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

const tabs = [
  {
    key: 'home',
    to: '/',
    label: '首页',
    paths: ['M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z', 'M9 22V12h6v10'],
  },
  {
    key: 'todos',
    to: '/todos',
    label: '待办',
    paths: ['M9 11l3 3L22 4', 'M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11'],
  },
  {
    key: 'finance',
    to: '/finance',
    label: '记账',
    paths: ['M2 6h20v14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2z', 'M2 10h20'],
    circles: [[16, 16, 1.6]],
  },
  {
    key: 'notes',
    to: '/notes',
    label: '笔记',
    paths: ['M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z', 'M14 2v6h6'],
    lines: [[16, 13, 8, 13], [16, 17, 8, 17]],
  },
  {
    key: 'profile',
    to: '/profile',
    label: '我的',
    paths: ['M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'],
    circles: [[12, 7, 4]],
  },
]

// Routes sharing a tab's area keep that tab lit; anything else (商城、背包、
// 修炼、项目…) leaves the bar neutral and relies on the header title.
const TAB_ROUTE_DOMAINS = {
  home: ['Home'],
  todos: ['Todos'],
  finance: ['Finance', 'FinanceAccounts', 'FinanceTransactions', 'FinanceBudgets', 'FinanceDebts'],
  notes: ['Notes', 'NotebookWorkspace', 'NotebookWorkspaceView', 'NotebookWorkspaceEdit', 'NewNote', 'NewNoteInWorkspace', 'NoteEditor', 'NoteSync'],
  profile: ['Profile', 'EditProfile'],
}

const activeTab = computed(() => {
  const name = route.name
  const match = Object.entries(TAB_ROUTE_DOMAINS).find(([, names]) => names.includes(name))
  return match ? match[0] : null
})

const pageTitle = computed(() => route.meta?.title || 'LifeQuest')
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

.bottom-nav-item:active {
  background: var(--color-bg-tertiary);
  transform: scale(0.97);
}

.bottom-nav-item--active,
.bottom-nav-item--active:active {
  color: var(--color-primary-dark);
  background: rgba(14, 165, 233, 0.12);
  transform: none;
}

@media (hover: hover) {
  .bottom-nav-item:hover {
    color: var(--color-text-secondary);
    background: var(--color-bg-tertiary);
  }

  .bottom-nav-item--active:hover {
    color: var(--color-primary-dark);
    background: rgba(14, 165, 233, 0.12);
  }
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
