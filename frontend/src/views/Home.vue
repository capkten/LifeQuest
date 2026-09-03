<template>
  <div class="home-page">
    <section class="hero-card">
      <div class="hero-main">
        <div class="hero-copy">
          <p class="hero-eyebrow">LifeQuest</p>
          <h1 class="welcome-title">欢迎回来，{{ user?.username || '冒险者' }}！</h1>
          <p class="welcome-subtitle">先处理今天最重要的事项，别让首屏只停留在展示。</p>
          <p class="hero-status">
            {{ checkinStatus?.checked_in ? `今日已签到，连续 ${checkinStatus?.streak || 0} 天` : `当前连续签到 ${checkinStatus?.streak || 0} 天` }}
          </p>
          <div class="hero-progress" aria-label="经验值进度">
            <div class="hero-progress-label">
              <span>升级所需经验 {{ (user?.level || 1) + 1 }}</span>
              <strong>{{ expPercent }}%</strong>
            </div>
            <div class="hero-progress-track">
              <span :style="{ width: expPercent + '%' }"></span>
            </div>
          </div>
        </div>
        <button
          v-if="!checkinStatus?.checked_in"
          class="checkin-btn"
          :disabled="checkinLoading"
          @click="doCheckin"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          {{ checkinLoading ? '签到中...' : '立即签到' }}
        </button>
        <div v-else class="checkin-done-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M20 6L9 17l-5-5" />
          </svg>
          今日已签到
        </div>
      </div>

      <div class="hero-meta">
        <div class="hero-meta-item">
          <span class="hero-meta-label">等级</span>
          <strong>等级 {{ user?.level || 1 }}</strong>
        </div>
        <div class="hero-meta-item">
          <span class="hero-meta-label">金币</span>
          <strong>{{ user?.coins || 0 }}</strong>
        </div>
        <div class="hero-meta-item">
          <span class="hero-meta-label">连续签到</span>
          <strong>{{ checkinStatus?.streak || 0 }} 天</strong>
        </div>
        <div class="hero-meta-item">
          <span class="hero-meta-label">今日待办</span>
          <strong>{{ actionCenter?.summary?.open_count || 0 }}</strong>
        </div>
      </div>
    </section>

    <CultivationStatusBar
      :overview="cultivationOverview"
      :loading="cultivationLoading"
      :error="cultivationError"
      @retry="loadCultivation"
    />

    <TodayActionCenter
      :data="actionCenter"
      :loading="actionCenterLoading"
      :error="actionCenterError"
      :completing-key="completingActionKey"
      @complete="handleActionComplete"
      @open="handleActionOpen"
      @retry="fetchActionCenter"
    />

    <aside class="home-aside-actions">
      <section class="quick-actions-card">
        <div class="aside-card-title">
          <span class="aside-card-kicker">专注行动</span>
          <h3>快速行动</h3>
        </div>
        <div class="quick-actions-list">
          <router-link to="/todos" class="quick-action-item">
            <span class="quick-action-icon quick-action-icon--primary">+</span>
            <span>创建任务</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
          </router-link>
          <router-link to="/projects" class="quick-action-item">
            <span class="quick-action-icon quick-action-icon--secondary">◇</span>
            <span>新建项目</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
          </router-link>
          <router-link to="/finance" class="quick-action-item">
            <span class="quick-action-icon quick-action-icon--accent">¥</span>
            <span>记录账目</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
          </router-link>
        </div>
      </section>
    </aside>

    <div class="content-grid">
      <div class="content-section">
        <div class="section-header">
          <h3 class="section-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
            最近任务
          </h3>
          <router-link to="/todos" class="section-link">查看全部</router-link>
        </div>
        <div class="section-body">
          <div v-if="loadingTasks" class="loading-state">
            <span class="loading-spinner"></span>
          </div>
          <div v-else-if="errorTasks" class="error-state">
            <p>{{ errorTasks }}</p>
            <button class="retry-btn" @click="fetchTasks">重试</button>
          </div>
          <div v-else-if="recentTasks.length === 0" class="empty-state">
            <p>暂无任务，创建你的第一个任务吧！</p>
          </div>
          <div v-else class="task-list">
            <div v-for="task in recentTasks" :key="task.id" class="task-item">
              <span class="task-status" :class="'task-status--' + task.status"></span>
              <span class="task-title">{{ task.title }}</span>
              <span class="task-difficulty" :class="'task-difficulty--' + task.difficulty">{{ labelDifficulty(task.difficulty) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="content-section">
        <div class="section-header">
          <h3 class="section-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <circle cx="12" cy="12" r="6" />
              <circle cx="12" cy="12" r="2" />
            </svg>
            最近目标
          </h3>
          <router-link to="/todos" class="section-link">查看全部</router-link>
        </div>
        <div class="section-body">
          <div v-if="loadingGoals" class="loading-state">
            <span class="loading-spinner"></span>
          </div>
          <div v-else-if="errorGoals" class="error-state">
            <p>{{ errorGoals }}</p>
            <button class="retry-btn" @click="fetchGoals">重试</button>
          </div>
          <div v-else-if="recentGoals.length === 0" class="empty-state">
            <p>暂无目标，设定你的第一个目标吧！</p>
          </div>
          <div v-else class="goal-list">
            <div v-for="goal in recentGoals" :key="goal.id" class="goal-item">
              <div class="goal-info">
                <span class="goal-title">{{ goal.title }}</span>
                <span class="goal-progress-text">{{ Math.round(goal.progress || 0) }}%</span>
              </div>
              <div class="goal-progress-bar">
                <div class="goal-progress-fill" :style="{ width: Math.round(goal.progress || 0) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <section class="habit-progress-card">
      <div class="habit-progress-heading">
        <div>
          <span class="aside-card-kicker">每日节奏</span>
          <h3>习惯进度</h3>
        </div>
        <strong>{{ habitProgress }}%</strong>
      </div>
      <div class="habit-progress-ring" :style="{ '--progress': habitProgress + '%' }">
        <div class="habit-progress-ring-inner">
          <strong>{{ habitProgress }}%</strong>
          <span>完成</span>
        </div>
      </div>
      <p v-if="actionCenter?.summary?.habit_due_count">今日完成 {{ actionCenter.summary.habit_completed_count }} / {{ actionCenter.summary.habit_due_count }} 个习惯</p>
      <p v-else>创建习惯，建立自己的每日节奏。</p>
    </section>

    <Transition name="toast">
      <div v-if="successToast" class="toast toast--success">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M20 6L9 17l-5-5" />
        </svg>
        {{ successToast }}
      </div>
    </Transition>
    <Transition name="toast">
      <div v-if="errorToast" class="toast toast--error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
        {{ errorToast }}
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { todoService } from '../services/todo'
import { checkinService } from '../services/checkin'
import { useActionCenter } from '../composables/useActionCenter'
import { useToast } from '../composables/useToast'
import { useUserStats } from '../composables/useUserStats'
import { getErrorMessage } from '../utils/errorMessage'
import { labelDifficulty } from '../utils/displayLabels'
import CultivationStatusBar from '../components/cultivation/CultivationStatusBar.vue'
import TodayActionCenter from '../components/home/TodayActionCenter.vue'

const authStore = useAuthStore()
const router = useRouter()
const user = computed(() => authStore.user)
const {
  expPercent,
  cultivationOverview,
  cultivationLoading,
  cultivationError,
  loadCultivation
} = useUserStats()
const { successToast, errorToast, showSuccess, showError } = useToast()

const checkinStatus = ref(null)
const checkinLoading = ref(false)

const tasks = ref([])
const goals = ref([])
const loadingTasks = ref(true)
const loadingGoals = ref(true)
const errorTasks = ref(null)
const errorGoals = ref(null)
const {
  data: actionCenter,
  loading: actionCenterLoading,
  error: actionCenterError,
  completingKey: completingActionKey,
  load: fetchActionCenter,
  complete: completeAction,
} = useActionCenter()

const recentTasks = computed(() => tasks.value.slice(0, 5))
const recentGoals = computed(() => goals.value.slice(0, 5))
const habitProgress = computed(() => {
  const summary = actionCenter.value?.summary
  if (!summary?.habit_due_count) return 0
  return Math.round((summary.habit_completed_count / summary.habit_due_count) * 100)
})

async function fetchTasks() {
  loadingTasks.value = true
  errorTasks.value = null
  try {
    tasks.value = await todoService.getTasks()
  } catch (e) {
    errorTasks.value = getErrorMessage(e)
  } finally {
    loadingTasks.value = false
  }
}

async function fetchCheckinStatus() {
  try {
    checkinStatus.value = await checkinService.getStatus()
  } catch (e) {
    showError(getErrorMessage(e))
  }
}

async function doCheckin() {
  if (checkinStatus.value?.checked_in) { showError('今天已经签到过了。'); return }
  checkinLoading.value = true
  try {
    const result = await checkinService.checkin()
    checkinStatus.value = { checked_in: true, streak: result.streak || 0 }
    await authStore.fetchUser()
    const coins = result.coins_earned || 0
    const exp = result.exp_earned || 0
    showSuccess(`签到成功！获得 ${coins} 金币、${exp} 经验值`)
  } catch (e) {
    showError(getErrorMessage(e))
  } finally {
    checkinLoading.value = false
  }
}

async function fetchGoals() {
  loadingGoals.value = true
  errorGoals.value = null
  try {
    goals.value = await todoService.getGoals()
  } catch (e) {
    errorGoals.value = getErrorMessage(e)
  } finally {
    loadingGoals.value = false
  }
}

async function handleActionComplete(item) {
  try {
    await completeAction(item)
    showSuccess(`${item.title} 已完成`)
    await Promise.allSettled([authStore.fetchUser(), loadCultivation()])
  } catch (e) {
    showError(getErrorMessage(e, '完成行动失败，请重试。'))
  }
}

function handleActionOpen() {
  router.push('/todos')
}

onMounted(() => {
  loadCultivation().catch((e) => showError(getErrorMessage(e)))
  fetchCheckinStatus()
  fetchTasks()
  fetchGoals()
  fetchActionCenter().catch(() => {})
})
</script>

<style scoped>
.home-page {
  width: 100%;
}

@media (min-width: 1200px) {
  .home-page {
    display: grid;
    grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.8fr);
    gap: var(--page-gap);
    align-items: start;
  }

  .hero-card {
    grid-column: 1 / -1;
    margin-bottom: 0;
  }

  .cultivation-status-bar {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .today-action-center {
    grid-column: 1;
    grid-row: 3;
    margin-bottom: 0;
  }

  .home-aside-actions {
    grid-column: 2;
    grid-row: 3;
  }

  .content-grid {
    display: contents;
  }

  .content-grid .content-section:first-child {
    grid-column: 1;
    grid-row: 4;
  }

  .content-grid .content-section:last-child {
    grid-column: 2;
    grid-row: 4;
  }

  .habit-progress-card {
    grid-column: 2;
    grid-row: 5;
  }
}

.hero-card {
  padding: clamp(20px, 2.5vw, 32px);
  border-radius: var(--surface-radius);
  color: #fff;
  background:
    radial-gradient(circle at 86% 18%, rgba(56, 189, 248, 0.28), transparent 36%),
    radial-gradient(circle at 14% 88%, rgba(16, 185, 129, 0.2), transparent 32%),
    linear-gradient(135deg, #0F172A 0%, #1E293B 52%, #0369A1 100%);
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.hero-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-lg);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.hero-eyebrow {
  font-size: var(--font-size-xs);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.75);
}

.welcome-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.welcome-subtitle {
  font-size: var(--font-size-base);
  color: rgba(255, 255, 255, 0.82);
}

.hero-status {
  font-size: var(--font-size-sm);
  color: rgba(255, 255, 255, 0.88);
}

.hero-progress {
  display: grid;
  gap: 6px;
  max-width: 420px;
  margin-top: 4px;
}

.hero-progress-label {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-sm);
  color: rgba(255, 255, 255, 0.76);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero-progress-label strong {
  color: #fff;
  letter-spacing: 0;
}

.hero-progress-track {
  height: 7px;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.2);
}

.hero-progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #c9e6ff, #6ffbbe);
  transition: width 300ms ease;
}

.hero-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.hero-meta-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
  padding: 10px 12px;
  border-radius: var(--surface-radius-sm);
  background: rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.22);
  color: #fff;
  text-align: center;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.hero-meta-item:hover {
  background: rgba(255, 255, 255, 0.22);
  transform: translateY(-2px);
}

.hero-meta-item strong {
  font-size: var(--font-size-base);
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
}

.hero-meta-label {
  font-size: var(--font-size-xs);
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.2;
  white-space: nowrap;
  font-weight: 500;
}

.checkin-btn,
.checkin-done-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  min-height: var(--touch-target-min);
  padding: 10px 18px;
  border-radius: var(--radius-xl);
  font-size: var(--font-size-sm);
  font-weight: 700;
  flex-shrink: 0;
}

.checkin-btn {
  color: var(--color-primary-dark);
  background: #fff;
  border: none;
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
}

.checkin-btn:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}

.checkin-btn:active {
  transform: translateY(0) scale(0.98);
}

.checkin-btn:disabled {
  opacity: 0.72;
  cursor: not-allowed;
  transform: none;
}

.checkin-btn svg,
.checkin-done-badge svg {
  width: 16px;
  height: 16px;
}

.checkin-done-badge {
  color: #fff;
  background: rgba(255, 255, 255, 0.2);
}

.daily-card,
.content-section {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.daily-card {
  margin-bottom: var(--spacing-md);
}

.home-aside-actions {
  min-width: 0;
}

.quick-actions-card,
.habit-progress-card {
  padding: var(--spacing-lg);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  box-shadow: var(--shadow-sm);
}

.aside-card-title,
.habit-progress-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.aside-card-title h3,
.habit-progress-heading h3 {
  margin-top: 3px;
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text);
}

.aside-card-kicker {
  display: block;
  color: var(--color-text-tertiary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  line-height: 1;
}

.quick-actions-list {
  display: grid;
  gap: var(--spacing-sm);
}

.quick-action-item {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--spacing-sm);
  min-height: 56px;
  padding: 8px 12px;
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-decoration: none;
  transition: background-color var(--transition-base), border-color var(--transition-base), transform var(--transition-base);
}

.quick-action-item:hover {
  color: var(--color-text);
  background: var(--color-surface-low);
  border-color: var(--color-border-strong);
  transform: translateY(-1px);
}

.quick-action-item > svg {
  width: 17px;
  height: 17px;
  color: var(--color-text-tertiary);
}

.quick-action-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  font-family: var(--font-family-display);
  font-size: 20px;
  font-weight: 600;
}

.quick-action-icon--primary {
  color: var(--color-primary-dark);
  background: var(--color-bg-tertiary);
}

.quick-action-icon--secondary {
  color: var(--color-secondary);
  background: var(--color-surface-variant);
}

.quick-action-icon--accent {
  color: var(--color-accent-dark);
  background: rgba(16, 185, 129, 0.14);
}

.habit-progress-card {
  text-align: center;
}

.habit-progress-heading {
  text-align: left;
}

.habit-progress-heading > strong {
  color: var(--color-primary-dark);
  font-family: var(--font-family-display);
  font-size: var(--font-size-xl);
}

.habit-progress-ring {
  display: grid;
  place-items: center;
  width: 148px;
  height: 148px;
  margin: var(--spacing-lg) auto;
  border-radius: 50%;
  background: conic-gradient(var(--color-secondary) var(--progress), var(--color-bg-tertiary) 0);
}

.habit-progress-ring-inner {
  display: grid;
  place-items: center;
  align-content: center;
  width: 116px;
  height: 116px;
  border-radius: 50%;
  background: var(--color-card);
}

.habit-progress-ring-inner strong {
  color: var(--color-text);
  font-family: var(--font-family-display);
  font-size: 1.75rem;
  line-height: 1;
}

.habit-progress-ring-inner span,
.habit-progress-card > p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.daily-header,
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
}

.daily-header-left,
.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.daily-header-left svg,
.section-title svg,
.daily-group-title svg {
  width: 18px;
  height: 18px;
  color: var(--color-primary);
  flex-shrink: 0;
}

.daily-title,
.section-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
}

.daily-overview {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.daily-body,
.section-body {
  padding: var(--spacing-md);
}

.daily-groups {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.daily-group-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.daily-list,
.task-list,
.goal-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.daily-item,
.task-item,
.goal-item {
  min-width: 0;
  padding: 12px 16px;
  margin-bottom: 8px;
  border-radius: var(--radius-lg);
  background: var(--color-surface-low);
  border: 1px solid var(--color-border);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.daily-item:last-child,
.task-item:last-child,
.goal-item:last-child {
  margin-bottom: 0;
}

.daily-item:hover,
.task-item:hover,
.goal-item:hover {
  background: #ffffff;
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.daily-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
}

.daily-item--done {
  opacity: 0.6;
}

.daily-item--link {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}

.daily-item--goal {
  grid-template-columns: minmax(0, 1fr) 132px;
}

.daily-check-btn {
  width: var(--touch-target-min);
  height: var(--touch-target-min);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  background: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
  transition: color 0.15s ease;
}

.daily-check-btn:hover:not(:disabled) {
  color: var(--color-primary);
}

.daily-check-btn--done {
  color: var(--color-success);
  cursor: default;
}

.daily-check-btn svg {
  width: 20px;
  height: 20px;
}

.daily-item-title,
.task-title {
  min-width: 0;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 600;
}

.daily-item-title {
  font-size: var(--font-size-sm);
}

.daily-item-title--done {
  color: var(--color-text-tertiary);
  text-decoration: line-through;
}

.task-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.task-status {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.task-status--pending {
  background: var(--color-text-tertiary);
}

.task-status--in_progress {
  background: var(--color-secondary);
}

.task-status--completed {
  background: var(--color-success);
}

.task-status--cancelled {
  background: var(--color-error);
}

.task-title {
  font-size: var(--font-size-sm);
}

.task-difficulty,
.daily-overdue {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.task-difficulty {
  text-transform: capitalize;
}

.task-difficulty--easy {
  background: rgba(81, 207, 102, 0.15);
  color: var(--color-success);
}

.task-difficulty--medium {
  background: rgba(255, 217, 61, 0.15);
  color: var(--color-warning);
}

.task-difficulty--hard {
  background: rgba(255, 107, 107, 0.15);
  color: var(--color-error);
}

.daily-streak {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: var(--font-size-xs);
  color: var(--color-warning);
  font-weight: 600;
  flex-shrink: 0;
}

.daily-streak svg {
  width: 14px;
  height: 14px;
}

.daily-overdue {
  background: rgba(255, 107, 107, 0.15);
  color: var(--color-error);
}

.goal-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: var(--spacing-xs);
}

.goal-title {
  min-width: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text);
}

.goal-progress-text,
.daily-goal-pct {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 600;
}

.goal-progress-bar,
.daily-goal-bar {
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.goal-progress-fill,
.daily-goal-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.daily-goal-progress {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-width: 132px;
}

.daily-goal-bar {
  flex: 1;
}

.loading-state,
.empty-state,
.error-state {
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.error-state {
  flex-direction: column;
  gap: var(--spacing-sm);
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.retry-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  color: var(--color-primary);
  background: transparent;
  cursor: pointer;
  font-family: var(--font-family);
}

.section-link {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  font-weight: 500;
}

.toast {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: 2000;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: #fff;
  box-shadow: var(--shadow-xl);
}

.toast svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.toast--success {
  background: var(--color-success);
}

.toast--error {
  background: var(--color-error);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

@media (max-width: 767px) {
  .hero-card {
    padding: 14px;
    border-radius: var(--surface-radius-sm);
  }

  .hero-main {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-meta {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }

  .hero-meta-item {
    gap: 2px;
    padding: 8px 4px;
  }

  .checkin-btn,
  .checkin-done-badge {
    width: 100%;
  }

  .hero-meta-item strong {
    font-size: 13px;
  }

  .hero-meta-label {
    font-size: 10px;
  }

  .hero-status {
    font-size: 12px;
  }

  .hero-progress {
    max-width: none;
  }

  .quick-actions-card,
  .habit-progress-card {
    padding: var(--spacing-md);
  }

  .daily-card {
    margin-bottom: 12px;
  }

  .section-header,
  .daily-header {
    flex-wrap: wrap;
  }

  .section-link {
    width: 100%;
  }

  .daily-overview {
    font-size: 10px;
  }

  .daily-item {
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
  }

  .daily-item--goal {
    grid-template-columns: minmax(0, 1fr);
  }

  .daily-streak,
  .daily-overdue,
  .task-difficulty {
    margin-left: 44px;
  }

  .daily-goal-progress {
    min-width: 100%;
    grid-column: 1 / -1;
  }

  .toast {
    top: var(--spacing-md);
    left: var(--spacing-md);
    right: var(--spacing-md);
  }
}

@media (min-width: 1200px) {
  .daily-body,
  .section-body {
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .daily-groups {
    gap: var(--spacing-md);
  }
}
</style>
