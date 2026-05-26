<template>
  <aside class="sidebar" :class="{
    'sidebar--open': isOpen,
    'sidebar--collapsed': isCollapsed
  }">
    <div class="sidebar-header">
      <h1 class="logo">LifeQuest</h1>
      <p v-if="!isCollapsed" class="logo-subtitle">Life Quest</p>
    </div>

    <div v-if="!isCollapsed" class="user-card">
      <div class="user-avatar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
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
        <span class="stat-label">等级</span>
        <span class="stat-value">{{ user?.level || 1 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v12M6 12h12" />
          </svg>
        </span>
        <span class="stat-label">金币</span>
        <span class="stat-value">{{ user?.coins || 0 }}</span>
      </div>
    </div>

    <div v-if="!isCollapsed" class="exp-bar-container">
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
        :aria-label="`Experience progress: ${expPercent}% toward next level`"
      >
        <div class="exp-bar-fill" :style="{ width: expPercent + '%' }"></div>
      </div>
    </div>

    <nav class="sidebar-nav">
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
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStats } from '../../composables/useUserStats'

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

const { user, expPercent } = useUserStats()

// Check if current route is exactly home
const isHomeActive = computed(() => route.path === '/')
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  min-height: 100vh;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  padding: var(--spacing-lg);
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
  padding-bottom: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.sidebar--collapsed .sidebar-header {
  padding-bottom: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  text-align: center;
}

.logo {
  font-size: var(--font-size-2xl);
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
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-tertiary);
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
  margin-bottom: var(--spacing-md);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm);
  background: var(--color-bg-tertiary);
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
  margin-bottom: var(--spacing-lg);
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
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  transition: all 0.2s ease;
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
  background: var(--color-primary);
  color: #fff;
}

.nav-item--active:hover {
  background: var(--color-primary-light);
  color: #fff;
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
