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
          <strong>{{ dailySummary?.summary?.due_tasks || 0 }}</strong>
        </div>
      </div>
    </section>

    <CultivationStatusBar
      :overview="cultivationOverview"
      :loading="cultivationLoading"
      :error="cultivationError"
      @retry="loadCultivation"
    />

    <div class="daily-card">
      <div class="daily-header">
        <div class="daily-header-left">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <h3 class="daily-title">今日任务</h3>
        </div>
        <span v-if="dailySummary" class="daily-overview">
          今日: {{ dailySummary.summary.completed_habits }}/{{ dailySummary.summary.total_habits }} 习惯已完成,
          {{ dailySummary.summary.due_tasks }} 个任务到期,
          {{ dailySummary.summary.active_goals }} 个目标进行中
        </span>
      </div>

      <div class="daily-body">
        <div v-if="loadingDaily" class="loading-state">
          <span class="loading-spinner"></span>
        </div>
        <div v-else-if="dailyError" class="error-state" role="alert" aria-live="polite">
          <p>{{ dailyError }}</p>
          <button type="button" class="retry-btn" @click="fetchDailySummary">重试</button>
        </div>
        <div v-else-if="dailySummary && dailySummary.habits.length === 0 && dailySummary.tasks.length === 0 && dailySummary.goals.length === 0" class="empty-state">
          <p>今天没有待办事项，去创建一些吧！</p>
        </div>
        <div v-else class="daily-groups">
          <div v-if="dailySummary.habits.length > 0" class="daily-group">
            <h4 class="daily-group-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                <polyline points="17 6 23 6 23 12" />
              </svg>
              今日习惯
            </h4>
            <div class="daily-list">
              <div v-for="habit in dailySummary.habits" :key="habit.id" class="daily-item" :class="{ 'daily-item--done': habit.completed_today }">
                <button
                  class="daily-check-btn"
                  :class="{ 'daily-check-btn--done': habit.completed_today }"
                  :disabled="completingHabitId === habit.id"
                  :aria-disabled="habit.completed_today"
                  @click="completeDailyHabit(habit)"
                >
                  <svg v-if="habit.completed_today" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" />
                  </svg>
                </button>
                <span class="daily-item-title" :class="{ 'daily-item-title--done': habit.completed_today }">{{ habit.title }}</span>
                <span class="daily-streak">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                  </svg>
                  {{ habit.streak }}
                </span>
                <span class="task-difficulty" :class="'task-difficulty--' + habit.difficulty">{{ labelDifficulty(habit.difficulty) }}</span>
              </div>
            </div>
          </div>

          <div v-if="dailySummary.tasks.length > 0" class="daily-group">
            <h4 class="daily-group-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v4l3 3" />
              </svg>
              今日到期任务
            </h4>
            <div class="daily-list">
              <router-link v-for="task in dailySummary.tasks" :key="task.id" to="/todos" class="daily-item daily-item--link">
                <span class="task-status" :class="'task-status--' + task.status"></span>
                <span class="daily-item-title">{{ task.title }}</span>
                <span v-if="isOverdue(task.deadline)" class="daily-overdue">逾期</span>
                <span class="task-difficulty" :class="'task-difficulty--' + task.difficulty">{{ labelDifficulty(task.difficulty) }}</span>
              </router-link>
            </div>
          </div>

          <div v-if="dailySummary.goals.length > 0" class="daily-group">
            <h4 class="daily-group-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <circle cx="12" cy="12" r="6" />
                <circle cx="12" cy="12" r="2" />
              </svg>
              进行中目标
            </h4>
            <div class="daily-list">
              <router-link v-for="goal in dailySummary.goals" :key="goal.id" to="/todos" class="daily-item daily-item--link daily-item--goal">
                <span class="daily-item-title">{{ goal.title }}</span>
                <div class="daily-goal-progress">
                  <div class="daily-goal-bar">
                    <div class="daily-goal-fill" :style="{ width: Math.round(goal.progress || 0) + '%' }"></div>
                  </div>
                  <span class="daily-goal-pct">{{ Math.round(goal.progress || 0) }}%</span>
                </div>
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>

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
      <p v-if="dailySummary?.summary?.total_habits">今日完成 {{ dailySummary.summary.completed_habits }} / {{ dailySummary.summary.total_habits }} 个习惯</p>
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
import { useAuthStore } from '../stores/auth'
import { todoService } from '../services/todo'
import { checkinService } from '../services/checkin'
import { useToast } from '../composables/useToast'
import { useUserStats } from '../composables/useUserStats'
import { getErrorMessage } from '../utils/errorMessage'
import { labelDifficulty } from '../utils/displayLabels'
import CultivationStatusBar from '../components/cultivation/CultivationStatusBar.vue'

const authStore = useAuthStore()
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

const dailySummary = ref(null)
const loadingDaily = ref(true)
const dailyError = ref(null)
const completingHabitId = ref(null)
let dailyRequestId = 0

const recentTasks = computed(() => tasks.value.slice(0, 5))
const recentGoals = computed(() => goals.value.slice(0, 5))
const habitProgress = computed(() => {
  const summary = dailySummary.value?.summary
  if (!summary?.total_habits) return 0
  return Math.round((summary.completed_habits / summary.total_habits) * 100)
})
const pendingTasksCount = computed(() =>
  (tasks.value || []).filter(t => t.status === 'pending' || t.status === 'in_progress').length
)

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

async function fetchDailySummary() {
  const requestId = ++dailyRequestId
  loadingDaily.value = true
  dailyError.value = null
  try {
    const summary = await todoService.getDailySummary()
    if (requestId === dailyRequestId) dailySummary.value = summary
  } catch (e) {
    if (requestId === dailyRequestId) {
      dailyError.value = getErrorMessage(e, '今日待办加载失败，请重试。')
      showError(dailyError.value)
    }
  } finally {
    if (requestId === dailyRequestId) loadingDaily.value = false
  }
}

async function completeDailyHabit(habit) {
  if (habit.completed_today) { showError('该习惯今天已经完成，明天再来继续。'); return }
  completingHabitId.value = habit.id
  try {
    await todoService.completeHabit(habit.id)
    showSuccess('习惯完成！')
    await fetchDailySummary()
    await authStore.fetchUser()
  } catch (e) {
    showError(getErrorMessage(e))
  } finally {
    completingHabitId.value = null
  }
}

function isOverdue(deadline) {
  if (!deadline) return false
  return new Date(deadline) < new Date(new Date().toDateString())
}

onMounted(() => {
  loadCultivation().catch((e) => showError(getErrorMessage(e)))
  fetchCheckinStatus()
  fetchTasks()
  fetchGoals()
  fetchDailySummary()
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

  .daily-card {
    grid-column: 1;
    grid-row: 2;
    margin-bottom: 0;
  }

  .home-aside-actions {
    grid-column: 2;
    grid-row: 2;
  }

  .content-grid {
    display: contents;
  }

  .content-grid .content-section:first-child {
    grid-column: 1;
    grid-row: 3;
  }

  .content-grid .content-section:last-child {
    grid-column: 2;
    grid-row: 3;
  }

  .habit-progress-card {
    grid-column: 2;
    grid-row: 4;
  }
}

.hero-card {
  display: grid;
  gap: var(--spacing-md);
  padding: var(--surface-padding);
  margin-bottom: var(--spacing-md);
  border-radius: var(--surface-radius);
  background:
    radial-gradient(circle at 88% 16%, rgba(110, 231, 183, 0.32), transparent 24%),
    linear-gradient(135deg, #123B5D 0%, #0A6C94 58%, var(--color-primary) 100%);
  box-shadow: var(--shadow-lg);
}

.hero-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
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
  color: #fff;
  text-align: center;
}

.hero-meta-item strong {
  font-size: var(--font-size-base);
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
}

.hero-meta-label {
  font-size: var(--font-size-xs);
  color: rgba(255, 255, 255, 0.76);
  line-height: 1.2;
  white-space: nowrap;
}

.checkin-btn,
.checkin-done-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  min-height: var(--touch-target-min);
  padding: 10px 16px;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  flex-shrink: 0;
}

.checkin-btn {
  color: var(--color-primary);
  background: #fff;
  border: none;
  cursor: pointer;
  font-family: var(--font-family);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  box-shadow: var(--shadow-md);
}

.checkin-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
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
  padding: 12px 0;
  border-bottom: 1px solid rgba(186, 230, 253, 0.7);
}

.daily-item:last-child,
.task-item:last-child,
.goal-item:last-child {
  border-bottom: none;
}

.daily-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
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
  gap: 10px;
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
