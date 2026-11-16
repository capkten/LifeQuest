<template>
  <aside class="sidebar" :class="{
    'sidebar--open': isOpen,
    'sidebar--collapsed': isCollapsed
  }">
    <div class="sidebar-header">
      <div class="logo-row">
        <h1 class="logo">{{ isCollapsed ? 'LQ' : 'LifeQuest' }}</h1>
        <span v-if="!isCollapsed" class="logo-version">v{{ appVersion }}</span>
      </div>
      <p v-if="!isCollapsed" class="logo-subtitle">修行与生活</p>
    </div>

    <div v-if="!isCollapsed" class="user-card">
      <div class="user-avatar">
        <img v-if="avatarSrc" :src="avatarSrc" alt="头像" class="user-avatar-img" />
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="8" r="4" />
          <path d="M20 21a8 8 0 1 0-16 0" />
        </svg>
      </div>
      <div class="user-details">
        <span class="user-name">{{ user?.username || '加载中...' }}</span>
        <span class="user-title">{{ user?.title || '冒险者' }}</span>
      </div>
    </div>

    <div v-if="!isCollapsed" class="user-stats">
      <div class="stat-item">
        <span class="stat-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        </span>
        <span class="stat-label">{{ cultivationOverview ? '境界' : '等级' }}</span>
        <span class="stat-value">{{ cultivationOverview ? `${labelFromServer(cultivationOverview, 'realm_label', cultivationOverview?.realm_key, labelRealm)} ${cultivationOverview.minor_stage}` : (user?.level || 1) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v12M6 12h12" />
          </svg>
        </span>
        <span class="stat-label">{{ cultivationOverview ? labelFromServer(cultivationOverview, 'spirit_stones_label', 'spirit_stones', labelResource) : '金币' }}</span>
        <span class="stat-value">{{ cultivationOverview ? cultivationOverview.spirit_stones : (user?.coins || 0) }}</span>
      </div>
    </div>

    <div v-if="!isCollapsed && !cultivationOverview" class="exp-bar-container">
      <div class="exp-bar-label">
        <span>EXP</span>
        <span>{{ expPercent }}%</span>
      </div>
      <div
        class="exp-bar"
        role="progressbar"
        :aria-valuenow="expPercent"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="`经验进度：距离下一等级 ${expPercent}%`"
      >
        <div class="exp-bar-fill" :style="{ width: expPercent + '%' }"></div>
      </div>
    </div>

    <div v-else-if="!isCollapsed" class="exp-bar-container">
      <div class="exp-bar-label">
        <span>修为</span>
        <span>{{ cultivationPercent }}%</span>
      </div>
      <div class="exp-bar" role="progressbar" :aria-valuenow="cultivationPercent" aria-valuemin="0" aria-valuemax="100" aria-label="修为进度">
        <div class="exp-bar-fill" :style="{ width: cultivationPercent + '%' }"></div>
      </div>
    </div>

    <nav class="sidebar-nav" aria-label="侧边导航">
      <template v-for="group in navigationGroups" :key="group.label">
        <span v-if="!isCollapsed" class="nav-section-label">{{ group.label }}</span>
        <router-link v-for="item in group.items" :key="item.to" :to="item.to" class="nav-item" :class="{ 'nav-item--active': item.to === '/' ? isHomeActive : route.path.startsWith(item.to) }" :title="isCollapsed ? item.label : ''">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path :d="item.icon" /></svg>
          <span v-if="!isCollapsed">{{ item.label }}</span>
        </router-link>
      </template>
    </nav>
  </aside>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStats } from '../../composables/useUserStats'
import { useResolvedImage } from '../../composables/useResolvedImage'
import { labelFromServer, labelRealm, labelResource } from '../../utils/displayLabels'

const appVersion = __APP_VERSION__

const route = useRoute()

defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  isCollapsed: {
    type: Boolean,
    default: false
  }
})

const {
  user,
  expPercent,
  cultivationOverview,
  cultivationPercent,
  loadCultivation
} = useUserStats()
const avatarSrc = useResolvedImage(computed(() => user.value?.avatar))
const isAscended = computed(() => cultivationOverview.value?.ascended === true)
const navigationGroups = computed(() => [
  { label: '洞府', items: [{ to: '/', label: '洞府', icon: 'M3 10 12 3l9 7v11H3ZM9 21v-8h6v8' }] },
  { label: '执行', items: [{ to: '/todos', label: '待办', icon: 'm4 12 5 5L20 6M3 3h7M3 21h18' }] },
  { label: '成长', items: [
    { to: '/cave/growth', label: '成长', icon: 'M12 21V9M12 15C5 15 3 10 3 4c7 0 9 4 9 11ZM12 11c0-6 3-9 9-9 0 6-3 9-9 9Z' },
    { to: '/sects', label: '宗门', icon: 'M3 21h18M5 21V9l7-5 7 5v12M9 21v-6h6v6' },
    { to: '/techniques', label: '功法', icon: 'M4 5a3 3 0 0 1 3-3h13v18H7a3 3 0 0 0-3 3ZM7 2v18' },
    { to: '/world', label: '凡界', icon: 'm2 20 7-15 5 9 3-5 5 11Z' },
    { to: '/tribulations', label: '渡劫', icon: 'M13 2 3 14h9l-1 8 10-12h-9l1-8Z' },
    { to: '/npcs', label: '人物', icon: 'M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM4 21a8 8 0 0 1 16 0' },
    ...(isAscended.value ? [{ to: '/immortal/world', label: '仙界', icon: 'M12 2 2 12l10 10 10-10Z' }] : []),
  ] },
  { label: '更多', items: [
    { to: '/finance', label: '财务', icon: 'M3 5h18v15H3ZM3 10h18M15 15h3' },
    { to: '/notes', label: '笔记', icon: 'M4 3h16v18H4ZM8 8h8M8 12h8M8 16h5' },
    { to: '/projects', label: '项目', icon: 'M3 5h7l2 3h9v13H3Z' },
    { to: '/calendar', label: '日历', icon: 'M3 5h18v16H3ZM3 10h18M8 2v6M16 2v6' },
    { to: '/stats', label: '统计', icon: 'M5 20v-6M12 20V4M19 20V9' },
    { to: '/review', label: '周复盘', icon: 'M4 3h16v18H4ZM8 8h8M8 13h8' },
    { to: '/shop', label: '商城', icon: 'M3 7h18v14H3ZM3 7l3-5h12l3 5M8 11a4 4 0 0 0 8 0' },
    { to: '/backpack', label: '背包', icon: 'M3 7h18v14H3ZM8 7V4h8v3M9 14h6' },
    { to: '/cave/settings', label: '洞府设置', icon: 'M4 5h16M4 12h16M4 19h16M8 2v6M16 9v6M8 16v6' },
    { to: '/profile', label: '个人资料', icon: 'M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM4 21a8 8 0 0 1 16 0' },
  ] },
])

onMounted(() => {
  if (!cultivationOverview.value) {
    loadCultivation().catch(() => {})
  }
})

// Check if current route is exactly home
const isHomeActive = computed(() => route.path === '/')
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100dvh;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 50;
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  border-right: 1px solid var(--home-hairline);
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 16px 10px;
}

.sidebar--collapsed {
  width: var(--sidebar-collapsed-width);
  padding: 16px 8px;
}

.sidebar-header {
  padding: 4px 6px 14px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.sidebar--collapsed .sidebar-header {
  padding-bottom: 10px;
  margin-bottom: 10px;
  text-align: center;
}

.logo {
  font-family: var(--font-family-display);
  font-size: 1.45rem;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: -0.02em;
}

.logo-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.logo-version {
  color: var(--color-text-tertiary);
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar--collapsed .logo {
  font-size: var(--font-size-base);
}

.logo-subtitle {
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: var(--home-soft);
  border: 0;
  border-radius: 14px;
  margin-bottom: 10px;
}

.user-avatar {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, #12B886, #0F8A67);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-avatar svg {
  width: 20px;
  height: 20px;
  color: #fff;
}

.user-avatar-img {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-full);
  object-fit: cover;
}

.user-details {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-title {
  font-size: 11px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.user-stats {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: 6px 4px;
  background: transparent;
  border: 0;
  border-radius: 10px;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon svg {
  width: 14px;
  height: 14px;
  color: var(--color-primary);
}

.stat-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.stat-value {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
}

.exp-bar-container {
  margin-bottom: 12px;
  padding: 0 4px;
}

.exp-bar-label {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 3px;
}

.exp-bar {
  height: 5px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.exp-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #12B886, #38D9A9);
  border-radius: var(--radius-full);
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.nav-section-label {
  padding: 12px 8px 4px;
  color: #8A99A8;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.sidebar-nav::-webkit-scrollbar {
  display: none;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 38px;
  padding: 6px 10px;
  border-radius: 10px;
  color: var(--color-text-secondary);
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.15s ease, color 0.15s ease;
  text-decoration: none;
  white-space: nowrap;
}

.sidebar--collapsed .nav-item {
  justify-content: center;
  padding: 8px;
  gap: 0;
}

.nav-item:hover {
  background: var(--home-soft);
  color: var(--color-text);
}

.nav-item--active {
  background: var(--rank-1-bg);
  color: var(--rank-1-accent);
  font-weight: 650;
  box-shadow: none;
  border: 0;
}

.nav-item--active:hover {
  background: var(--rank-1-chip);
  color: var(--rank-1-accent);
}

.nav-item svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

/* Mobile (<768px): sidebar hidden by default, slides in as overlay */
@media (max-width: 767px) {
  .sidebar {
    transform: translateX(-100%);
    box-shadow: none;
    z-index: 100;
    width: var(--sidebar-width);
  }

  .nav-item {
    min-height: 44px;
  }

  .sidebar--open {
    transform: translateX(0);
    box-shadow: var(--shadow-xl);
  }
}

/* Tablet (768-1200px): collapsible sidebar */
@media (min-width: 768px) and (max-width: 1199px) {
  .sidebar--collapsed {
    transform: translateX(0);
  }
}
</style>
