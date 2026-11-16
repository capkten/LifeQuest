<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <Sidebar :is-open="sidebarOpen" :is-collapsed="sidebarCollapsed" />
    <div class="app-main">
      <Header v-if="!isImmersiveRoute" :title="pageTitle" />
      <main class="app-content" :class="{ 'app-content--full-width': isFullWidthRoute, 'app-content--cave': isImmersiveRoute }">
        <div class="app-content-shell" :class="{ 'app-content-shell--full-width': isFullWidthRoute, 'app-content-shell--cave': isImmersiveRoute }">
          <aside v-if="cave.offline.value" class="cave-network-notice" role="status"><strong>离线</strong><span>{{ cave.cacheDate.value ? `显示 ${cave.cacheDate.value} 的缓存。` : '暂时无法连接。' }}已有入定继续计时，收功会在联网后确认。</span><span v-if="cave.staleCache.value">这不是今天的数据，今日签与三签已暂时收起。</span></aside>
          <aside v-for="item in cave.pendingSettlements.value" :key="item.id" class="cave-network-notice" aria-label="待收功"><span>{{ item.status === 'blocked' ? '这段收功需要确认。' : '有一段时间正在等待联网收功。' }}</span><router-link :to="`/cave/return/${item.id}`" class="cave-link">查看待收功</router-link></aside>
          <router-view />
          <p v-if="notifications.notice.value" class="cave-notification-notice" role="status">{{ notifications.notice.value }}</p>
        </div>
      </main>
    </div>

    <aside v-if="showSessionBar" class="cave-mini-bar" aria-label="进行中的入定">
      <span><strong>{{ sessionRemainingText }}</strong><span>{{ cave.activeSession.value.todo_title || '静坐片刻' }}</span></span>
      <router-link :to="`/cave/session/${cave.activeSession.value.id}`" aria-label="回到入定">回到入定</router-link>
    </aside>
    <CaveSessionSheet />

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
      <button type="button" class="bottom-nav-item" :class="{ 'bottom-nav-item--active': moreOpen || activeTab === 'more' }" :aria-expanded="moreOpen" aria-controls="cave-more-links" @click="moreOpen = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></svg>
        <span>更多</span>
      </button>
    </nav>
    <el-drawer v-model="moreOpen" title="更多" direction="btt" size="65%" class="cave-more-drawer">
      <nav id="cave-more-links" class="more-links" aria-label="更多功能">
        <router-link v-for="item in moreLinks" :key="item.to" :to="item.to" @click="moreOpen = false">{{ item.label }}<span aria-hidden="true">›</span></router-link>
      </nav>
    </el-drawer>

    <!-- Mobile sidebar overlay -->
    <div
      v-if="sidebarOpen"
      class="sidebar-overlay"
      @click="sidebarOpen = false"
    ></div>
  </div>
</template>

<script setup>
import { ref, computed, provide, onMounted, onUnmounted, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Capacitor } from '@capacitor/core'
import { App } from '@capacitor/app'
import CaveSessionSheet from '../cave/CaveSessionSheet.vue'
import '../cave/cave.css'
import { createCaveFeedback } from '../../services/caveFeedback.js'
import { createCaveNotifications } from '../../services/caveNotifications.js'
import { useAuthStore } from '../../stores/auth.js'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import { useAndroidBackButton } from '../../composables/useAndroidBackButton'
import { useCave } from '../../composables/useCave.js'
import { caveService } from '../../services/cave.js'
import { useCultivationStore } from '../../stores/cultivation.js'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const cave = useCave(caveService, { identity: authStore.user?.id })
const cultivationStore = useCultivationStore()
const queuedReturns = new Set()
watch(cave.pendingSettlements, items => { for (const item of items) queuedReturns.add(item.id) }, { immediate: true })
watch(() => cave.settledSession.value?.id, id => {
  if (!id) return
  cultivationStore.refresh().catch(() => {})
  if (queuedReturns.delete(id)) router.push(`/cave/return/${id}`)
})
const feedback = createCaveFeedback({ platform: Capacitor.getPlatform() })
const notificationPlatform = Capacitor.getPlatform() === 'android' ? 'android' : globalThis.__TAURI_INTERNALS__ ? 'windows' : 'web'
const notifications = createCaveNotifications({ platform: notificationPlatform, api: caveService, getOwnerId: () => authStore.user?.id })
provide('caveNotifications', notifications)
provide('cave', cave)
provide('caveFeedback', feedback)
const moreOpen = ref(false)
let caveTimer = null
let appStateListener = null
let disposed = false
let appActive = true
let notificationCleanup = null
let notificationListenerPending = false
async function handleNotificationAction(action) {
  const owner = authStore.user?.id
  if (!owner || disposed || !notifications.enabled.value) return
  Promise.resolve().then(() => caveService.recordEvent({
    event: 'notification_click', session_id: action.sessionId,
    notification_type: action.action === 'finish' ? 'finish' : action.type,
    delay_ms: Math.min(Number.MAX_SAFE_INTEGER, Math.max(0, Math.floor(action.delayMs))),
    source: 'notification', mode: cave.mode.value, has_active_session: Boolean(cave.activeSession.value),
    request_id: globalThis.crypto.randomUUID(),
  })).catch(() => {})
  if (action.action === 'finish' && action.canComplete) {
    const session = await cave.loadSession(action.sessionId)
    if (disposed || authStore.user?.id !== owner) return
    if (session?.status === 'active' && cave.activeSession.value?.id === action.sessionId && cave.canComplete.value) {
      const result = await cave.settleSession()
      if (disposed || authStore.user?.id !== owner) return
      if (result) {
        if (result.status === 'completed') feedback.play('complete')
        router.push(`/cave/return/${result.id}`)
        return
      }
    }
  }
  if (!disposed && authStore.user?.id === owner) router.push(action.path)
}
async function listenForNotifications() {
  if (!notifications.isSupported || !authStore.user?.id || notificationCleanup || notificationListenerPending || disposed) return
  notificationListenerPending = true
  try {
    const cleanup = await notifications.listen(handleNotificationAction)
    if (disposed) await cleanup()
    else notificationCleanup = cleanup
  } finally {
    notificationListenerPending = false
  }
}
function syncNotifications() {
  const owner = authStore.user?.id
  if (!notifications.isSupported || !owner || !cave.data.value || disposed) return
  const session = cave.activeSession.value
  if (session?.user_id && session.user_id !== owner) return
  notifications.syncSession(cave.pendingSettlements.value.some(item => item.id === session?.id) ? null : session, { serverNow: cave.getServerNow() })
}
watch(() => authStore.user?.id, (owner, previous) => { queuedReturns.clear(); cave.setUser(owner || null); if (previous && owner !== previous) notifications.clear(); listenForNotifications() }, { flush: 'sync' })
watch([
  () => authStore.user?.id, () => cave.activeSession.value?.id,
  () => cave.activeSession.value?.started_at, () => cave.activeSession.value?.target_duration,
  () => cave.data.value?.server_now, () => cave.pendingSettlements.value.map(item => item.id).join(','), notifications.enabled, notifications.permission,
], syncNotifications, { immediate: true })
const sessionRemainingText = computed(() => `${String(Math.floor(cave.remainingSeconds.value / 60)).padStart(2, '0')}:${String(cave.remainingSeconds.value % 60).padStart(2, '0')}`)
const showSessionBar = computed(() => cave.activeSession.value && !cave.pendingSettlements.value.some(item => item.id === cave.activeSession.value.id) && !['Home', 'CaveSession', 'CaveReturn'].includes(route.name))
function enterReturnWhenDue() {
  const session = cave.activeSession.value
  if (session && cave.remainingSeconds.value === 0 && appActive && document.visibilityState === 'visible' && !(route.name === 'CaveReturn' && route.params.id === session.id)) router.replace(`/cave/return/${session.id}`)
}
watch([cave.remainingSeconds, () => cave.activeSession.value?.id, () => route.name], enterReturnWhenDue)
watchEffect(() => {
  document.title = cave.activeSession.value ? `${sessionRemainingText.value} · ${cave.activeSession.value.todo_title || '静坐片刻'} · 入定` : `${route.meta?.title || '洞府'} · LifeQuest`
})
async function refreshForeground() {
  if (document.visibilityState !== 'visible' || !appActive || disposed) return
  await cave.load()
  if (disposed) return
  cave.tick()
  enterReturnWhenDue()
}

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
  listenForNotifications()
  window.addEventListener('resize', updateBreakpoints)
  caveTimer = window.setInterval(() => cave.tick(), 1000)
  document.addEventListener('visibilitychange', refreshForeground)
  if (!['Home', 'CaveSession', 'CaveReturn'].includes(route.name)) cave.load()
  if (Capacitor.isNativePlatform()) {
    App.addListener('appStateChange', ({ isActive }) => {
      appActive = isActive
      if (isActive) refreshForeground()
    }).then(listener => { if (disposed) listener.remove(); else appStateListener = listener })
  }
})

onUnmounted(() => {
  disposed = true
  window.removeEventListener('resize', updateBreakpoints)
  document.removeEventListener('visibilitychange', refreshForeground)
  appStateListener?.remove()
  window.clearInterval(caveTimer)
  cave.dispose()
  feedback.dispose()
  notificationCleanup?.()
  notifications.dispose()
  document.title = 'LifeQuest - 生活冒险家'
})

provide('toggleSidebar', toggleSidebar)
provide('sidebarOpen', sidebarOpen)
provide('isMobile', isMobile)

const isFullWidthRoute = computed(() => {
  const fullWidthNames = ['NotebookFileManage', 'NotebookWorkspaceView', 'NotebookWorkspaceEdit', 'NoteEditor', 'NoteSync']
  return fullWidthNames.includes(route.name) || String(route.path).startsWith('/notes/')
})

const isImmersiveRoute = computed(() => ['Home', 'CaveSession', 'CaveReturn', 'CaveSettings', 'CaveGrowth', 'CaveCodex', 'CaveCompanions', 'CaveLetters'].includes(route.name))
const moreLinks = [
  { to: '/finance', label: '财务' },
  { to: '/notes', label: '笔记' },
  { to: '/projects', label: '项目' },
  { to: '/calendar', label: '日历' },
  { to: '/stats', label: '统计' },
  { to: '/review', label: '周复盘' },
  { to: '/shop', label: '商城' },
  { to: '/backpack', label: '背包' },
  { to: '/cave/settings', label: '洞府设置' },
  { to: '/profile', label: '个人资料' },
]

const tabs = [
  {
    key: 'home',
    to: '/',
    label: '洞府',
    paths: ['M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z', 'M9 22V12h6v10'],
  },
  {
    key: 'todos',
    to: '/todos',
    label: '待办',
    paths: ['M9 11l3 3L22 4', 'M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11'],
  },
  {
    key: 'growth',
    to: '/cave/growth',
    label: '成长',
    paths: ['M12 21V9', 'M12 15C5 15 3 10 3 4c7 0 9 4 9 11Z', 'M12 11c0-6 3-9 9-9 0 6-3 9-9 9Z'],
  },
]

const TAB_ROUTE_DOMAINS = {
  home: ['Home', 'CaveSession', 'CaveReturn'],
  todos: ['Todos'],
  growth: ['CaveGrowth', 'CaveCodex', 'CaveCompanions', 'CaveLetters', 'Cultivation', 'World', 'Sects', 'Techniques', 'Npcs', 'Tribulations', 'ImmortalWorld', 'ImmortalActivities', 'ImmortalOfficials'],
}

const activeTab = computed(() => {
  const name = route.name
  const match = Object.entries(TAB_ROUTE_DOMAINS).find(([, names]) => names.includes(name))
  return match ? match[0] : 'more'
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

.app-content-shell--cave { max-width: 1180px; padding-top: 24px; }
.cave-notification-notice { max-width: 680px; margin: 16px auto 0; color: #536d62; font-size: 14px; line-height: 1.7; }
.cave-network-notice { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; padding: 12px 16px; background: #edf2ee; color: #24443d; border-radius: 12px; font-size: 14px; line-height: 1.7; }.cave-network-notice > span { flex: 1 1 220px; }
.cave-mini-bar { position: fixed; left: calc(var(--sidebar-width) + 24px); right: 24px; bottom: 24px; z-index: 85; display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 64px; max-width: 640px; margin: 0 auto; padding: 10px 16px; border-radius: 12px; background: #24443d; color: #fff; box-shadow: 0 8px 28px #24443d26; }.cave-mini-bar > span { display: flex; align-items: center; gap: 16px; min-width: 0; }.cave-mini-bar strong { font-size: 22px; font-weight: 500; font-variant-numeric: tabular-nums; }.cave-mini-bar > span > span { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.cave-mini-bar a { display: flex; align-items: center; min-height: 44px; color: #fff; white-space: nowrap; font-size: 14px; padding: 8px; text-underline-offset: 4px; }.cave-mini-bar a:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }.sidebar-collapsed .cave-mini-bar { left: calc(var(--sidebar-collapsed-width) + 24px); }@media(max-width:767px) { .cave-mini-bar, .sidebar-collapsed .cave-mini-bar { left: 12px; right: 12px; bottom: calc(var(--bottom-nav-height) + var(--safe-area-bottom) + 10px); } }
.more-links { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.more-links a { display: flex; align-items: center; justify-content: space-between; min-height: 52px; padding: 12px 16px; background: #edf2ee; color: #24443d; border-radius: 12px; text-decoration: none; font-size: 16px; }
.more-links a:focus-visible, .bottom-nav-item:focus-visible { outline: 2px solid #3d8f78; outline-offset: 3px; }
button.bottom-nav-item { border: 0; background: none; font-family: inherit; cursor: pointer; }
@media (max-width: 767px) { .app-content-shell--cave { padding: 12px 18px 0; }.app-content--cave { background: #f7faf8; } }

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
  font-size: 12px;
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
  background: rgba(61, 143, 120, 0.12);
  transform: none;
}

@media (hover: hover) {
  .bottom-nav-item:hover {
    color: var(--color-text-secondary);
    background: var(--color-bg-tertiary);
  }

  .bottom-nav-item--active:hover {
    color: var(--color-primary-dark);
    background: rgba(61, 143, 120, 0.12);
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
