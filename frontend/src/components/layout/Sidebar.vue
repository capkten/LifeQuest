<template>
  <aside class="sidebar" :class="{
    'sidebar--open': isOpen,
    'sidebar--collapsed': isCollapsed
  }">
    <div class="sidebar-header">
      <h1 class="logo">LifeQuest</h1>
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

    <nav class="sidebar-nav">
      <span v-if="!isCollapsed" class="nav-section-label">规划</span>
      <router-link to="/" class="nav-item" :class="{ 'nav-item--active': isHomeActive }" :title="isCollapsed ? '首页' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
        <span v-if="!isCollapsed">首页</span>
      </router-link>
      <router-link to="/todos" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '待办' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M9 11l3 3L22 4" />
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
        </svg>
        <span v-if="!isCollapsed">待办</span>
      </router-link>
      <router-link to="/projects" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '项目' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
        <span v-if="!isCollapsed">项目</span>
      </router-link>
      <router-link to="/calendar" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '日历' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        <span v-if="!isCollapsed">日历</span>
      </router-link>
      <router-link to="/notes" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '笔记' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
        <span v-if="!isCollapsed">笔记</span>
      </router-link>
      <span v-if="!isCollapsed && cultivationUnlocked" class="nav-section-label">修炼</span>
      <router-link v-if="cultivationUnlocked" to="/cultivation" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '修炼' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M12 3v18M5 8h14M7 16h10" />
        </svg>
        <span v-if="!isCollapsed">修炼</span>
      </router-link>
      <router-link v-if="cultivationUnlocked" to="/world" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '凡界' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
        </svg>
        <span v-if="!isCollapsed">凡界</span>
      </router-link>
      <router-link v-if="cultivationUnlocked" to="/sects" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '宗门' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M3 21h18M5 21V9l7-5 7 5v12M9 21v-6h6v6" />
        </svg>
        <span v-if="!isCollapsed">宗门</span>
      </router-link>
      <router-link v-if="cultivationUnlocked" to="/techniques" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '功法' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M4 5a3 3 0 0 1 3-3h13v18H7a3 3 0 0 0-3 3z" /><path d="M7 2v18" />
        </svg>
        <span v-if="!isCollapsed">功法</span>
      </router-link>
      <router-link v-if="cultivationUnlocked" to="/npcs" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? (isAscended ? '仙官' : '凡界 NPC') : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="7" r="4" /><path d="M4 21a8 8 0 0 1 16 0" />
        </svg>
        <span v-if="!isCollapsed">{{ isAscended ? '仙官' : '凡界 NPC' }}</span>
      </router-link>
      <router-link v-if="cultivationUnlocked" to="/tribulations" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '渡劫' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
        </svg>
        <span v-if="!isCollapsed">渡劫</span>
      </router-link>
      <span v-if="!isCollapsed" class="nav-section-label">奖励</span>
      <router-link to="/shop" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '商城' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <path d="M16 10a4 4 0 0 1-8 0" />
        </svg>
        <span v-if="!isCollapsed">商城</span>
      </router-link>
      <router-link to="/backpack" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '背包' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
          <path d="M16 7V5a4 4 0 0 0-8 0v2" />
          <line x1="12" y1="12" x2="12" y2="16" />
          <line x1="10" y1="14" x2="14" y2="14" />
        </svg>
        <span v-if="!isCollapsed">背包</span>
      </router-link>
      <span v-if="!isCollapsed" class="nav-section-label">洞察</span>
      <router-link to="/finance" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '记账' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M2 10h20" />
          <circle cx="12" cy="15" r="2" />
        </svg>
        <span v-if="!isCollapsed">记账</span>
      </router-link>
      <router-link to="/stats" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '统计' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M18 20V10" />
          <path d="M12 20V4" />
          <path d="M6 20v-6" />
        </svg>
        <span v-if="!isCollapsed">统计</span>
      </router-link>
      <router-link to="/profile" class="nav-item" active-class="nav-item--active" :title="isCollapsed ? '个人' : ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        <span v-if="!isCollapsed">个人</span>
      </router-link>
    </nav>
  </aside>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStats } from '../../composables/useUserStats'
import { useResolvedImage } from '../../composables/useResolvedImage'
import { labelFromServer, labelRealm, labelResource } from '../../utils/displayLabels'

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
const cultivationUnlocked = computed(() => Boolean(cultivationOverview.value && cultivationOverview.value.unlocked !== false))
const isAscended = computed(() => cultivationOverview.value?.ascended === true)

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
  height: 100vh;
  background: var(--color-card);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  padding: var(--spacing-md);
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
  transition: width 0.3s ease, transform 0.3s ease;
  overflow-x: hidden;
  overflow-y: auto;
}

.sidebar--collapsed {
  width: var(--sidebar-collapsed-width);
  padding: var(--spacing-lg) var(--spacing-sm);
}

.sidebar-header {
  padding-bottom: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.sidebar--collapsed .sidebar-header {
  padding-bottom: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  text-align: center;
}

.logo {
  font-family: var(--font-family-display);
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-primary);
}

.sidebar--collapsed .logo {
  font-size: var(--font-size-lg);
}

.logo-subtitle {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-xs);
}

.user-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-surface-low);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-md);
}

.user-avatar {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-avatar svg {
  width: 24px;
  height: 24px;
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
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-title {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.user-stats {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm);
  background: var(--color-surface-low);
  border-radius: var(--radius-md);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon svg {
  width: 18px;
  height: 18px;
  color: var(--color-primary-light);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.stat-value {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
}

.exp-bar-container {
  margin-bottom: var(--spacing-md);
}

.exp-bar-label {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-xs);
}

.exp-bar {
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.exp-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.nav-section-label {
  padding: 10px var(--spacing-sm) 3px;
  color: var(--color-text-tertiary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  line-height: 1;
}

.sidebar-nav::-webkit-scrollbar {
  display: none;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-height: var(--touch-target-min);
  padding: 9px var(--spacing-sm);
  border-radius: var(--radius-lg);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  transition: background-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
  text-decoration: none;
  white-space: nowrap;
}

.sidebar--collapsed .nav-item {
  justify-content: center;
  padding: var(--spacing-sm);
  gap: 0;
}

.nav-item:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.nav-item--active {
  background: var(--color-bg-tertiary);
  color: var(--color-primary-dark);
  box-shadow: inset 3px 0 0 var(--color-primary);
}

.nav-item--active:hover {
  background: var(--color-surface-container);
  color: var(--color-primary-dark);
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
