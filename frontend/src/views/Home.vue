<template>
  <div class="home-page">
    <div class="checkin-card" :class="{ 'checkin-card--done': checkinStatus?.checked_in }">
      <div class="checkin-content">
        <div class="checkin-left">
          <div class="checkin-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <div class="checkin-info">
            <h2 class="checkin-title">每日签到</h2>
            <p v-if="checkinStatus?.checked_in" class="checkin-streak">
              已签到 {{ checkinStatus.streak || 0 }} 天
              <span v-if="checkinStatus.streak > 1" class="checkin-badge">
                {{ checkinStatus.streak }} 连签
              </span>
            </p>
            <p v-else class="checkin-streak">
              当前连续签到 {{ checkinStatus?.streak || 0 }} 天
            </p>
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
          {{ checkinLoading ? '签到中...' : '签到' }}
        </button>
        <div v-else class="checkin-done-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M20 6L9 17l-5-5" />
          </svg>
          已签到
        </div>
      </div>
    </div>

    <div class="welcome-card">
      <div class="welcome-content">
        <h1 class="welcome-title">欢迎回来，{{ user?.username || '冒险者' }}！</h1>
        <p class="welcome-subtitle">准备好今天的冒险了吗？</p>
      </div>
      <div class="welcome-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card stat-card--level">
        <div class="stat-card-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        </div>
        <div class="stat-card-info">
          <span class="stat-card-value">{{ user?.level || 1 }}</span>
          <span class="stat-card-label">等级</span>
        </div>
      </div>
      <div class="stat-card stat-card--coins">
        <div class="stat-card-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v12M6 12h12" />
          </svg>
        </div>
        <div class="stat-card-info">
          <span class="stat-card-value">{{ user?.coins || 0 }}</span>
          <span class="stat-card-label">金币</span>
        </div>
      </div>
      <div class="stat-card stat-card--tasks">
        <div class="stat-card-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4l3 3" />
          </svg>
        </div>
        <div class="stat-card-info">
          <span class="stat-card-value">{{ pendingTasksCount }}</span>
          <span class="stat-card-label">待完成任务</span>
        </div>
      </div>
    </div>

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
              <span class="task-difficulty" :class="'task-difficulty--' + task.difficulty">
                {{ task.difficulty }}
              </span>
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
                <div
                  class="goal-progress-fill"
                  :style="{ width: Math.round(goal.progress || 0) + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

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
        <div v-else-if="!dailySummary || (dailySummary.habits.length === 0 && dailySummary.tasks.length === 0 && dailySummary.goals.length === 0)" class="empty-state">
          <p>今天没有待办事项，去创建一些吧！</p>
        </div>
        <div v-else class="daily-groups">
          <!-- Habits -->
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
                  :disabled="habit.completed_today || completingHabitId === habit.id"
                  @click="completeDailyHabit(habit.id)"
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
                <span class="task-difficulty" :class="'task-difficulty--' + habit.difficulty">{{ habit.difficulty }}</span>
              </div>
            </div>
          </div>

          <!-- Due Tasks -->
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
                <span class="task-difficulty" :class="'task-difficulty--' + task.difficulty">{{ task.difficulty }}</span>
              </router-link>
            </div>
          </div>

          <!-- Active Goals -->
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
              <router-link v-for="goal in dailySummary.goals" :key="goal.id" to="/todos" class="daily-item daily-item--link">
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

    <!-- Toast notifications -->
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

const authStore = useAuthStore()
const user = computed(() => authStore.user)
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
const completingHabitId = ref(null)

const recentTasks = computed(() => tasks.value.slice(0, 5))
const recentGoals = computed(() => goals.value.slice(0, 5))
const pendingTasksCount = computed(() =>
  (tasks.value || []).filter(t => t.status === 'pending' || t.status === 'in_progress').length
)

async function fetchTasks() {
  loadingTasks.value = true
  errorTasks.value = null
  try {
    tasks.value = await todoService.getTasks()
  } catch (e) {
    errorTasks.value = '加载任务失败，请重试。'
  } finally {
    loadingTasks.value = false
  }
}

async function fetchCheckinStatus() {
  try {
    checkinStatus.value = await checkinService.getStatus()
  } catch (e) {
    // Non-critical: silently ignore
  }
}

async function doCheckin() {
  checkinLoading.value = true
  try {
    const result = await checkinService.checkin()
    checkinStatus.value = { checked_in: true, streak: result.streak || 0 }
    await authStore.fetchUser()
    const coins = result.coins_earned || 0
    const exp = result.exp_earned || 0
    showSuccess(`签到成功！获得 ${coins} 金币、${exp} 经验值`)
  } catch (e) {
    showError(e.response?.data?.detail || '签到失败，请重试。')
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
    errorGoals.value = '加载目标失败，请重试。'
  } finally {
    loadingGoals.value = false
  }
}

async function fetchDailySummary() {
  loadingDaily.value = true
  try {
    dailySummary.value = await todoService.getDailySummary()
  } catch (e) {
    // Non-critical: silently ignore
  } finally {
    loadingDaily.value = false
  }
}

async function completeDailyHabit(habitId) {
  completingHabitId.value = habitId
  try {
    await todoService.completeHabit(habitId)
    showSuccess('习惯完成！')
    await fetchDailySummary()
    await authStore.fetchUser()
  } catch (e) {
    showError(e.response?.data?.detail || '操作失败，请重试。')
  } finally {
    completingHabitId.value = null
  }
}

function isOverdue(deadline) {
  if (!deadline) return false
  return new Date(deadline) < new Date(new Date().toDateString())
}

onMounted(() => {
  fetchCheckinStatus()
  fetchTasks()
  fetchGoals()
  fetchDailySummary()
})
</script>

<style scoped>
.home-page {
  padding: var(--spacing-xl);
  width: 100%;
}

/* Check-in Card */
.checkin-card {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-radius: var(--radius-xl);
  padding: var(--spacing-lg) var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  box-shadow: var(--shadow-lg);
  transition: all 0.3s ease;
}

.checkin-card--done {
  background: linear-gradient(135deg, var(--color-success), #1a9a4a);
}

.checkin-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.checkin-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  min-width: 0;
}

.checkin-icon-wrap {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.checkin-icon-wrap svg {
  width: 28px;
  height: 28px;
  color: #fff;
}

.checkin-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.checkin-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.checkin-streak {
  font-size: var(--font-size-sm);
  color: rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.checkin-badge {
  display: inline-block;
  padding: 2px 10px;
  background: rgba(255, 255, 255, 0.25);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: #fff;
}

.checkin-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-xl);
  font-size: var(--font-size-base);
  font-weight: 700;
  color: var(--color-primary);
  background: #fff;
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-family: var(--font-family);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  box-shadow: var(--shadow-md);
}

.checkin-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
}

.checkin-btn:active {
  transform: scale(0.95);
}

.checkin-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.checkin-btn svg {
  width: 20px;
  height: 20px;
}

.checkin-done-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-xl);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: #fff;
  background: rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-lg);
}

.checkin-done-badge svg {
  width: 20px;
  height: 20px;
}

.welcome-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-radius: var(--radius-xl);
  padding: var(--spacing-xl) var(--spacing-2xl);
  margin-bottom: var(--spacing-xl);
  box-shadow: var(--shadow-lg);
}

.welcome-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: #fff;
  margin-bottom: var(--spacing-xs);
}

.welcome-subtitle {
  font-size: var(--font-size-base);
  color: rgba(255, 255, 255, 0.8);
}

.welcome-icon svg {
  width: 64px;
  height: 64px;
  color: rgba(255, 255, 255, 0.3);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: border-color 0.2s ease;
}

.stat-card:hover {
  border-color: var(--color-primary);
}

.stat-card-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card--level .stat-card-icon {
  background: rgba(108, 99, 255, 0.15);
}

.stat-card--level .stat-card-icon svg {
  color: var(--color-primary);
}

.stat-card--coins .stat-card-icon {
  background: rgba(255, 217, 61, 0.15);
}

.stat-card--coins .stat-card-icon svg {
  color: var(--color-warning);
}

.stat-card--tasks .stat-card-icon {
  background: rgba(0, 217, 255, 0.15);
}

.stat-card--tasks .stat-card-icon svg {
  color: var(--color-secondary);
}

.stat-card-icon svg {
  width: 24px;
  height: 24px;
}

.stat-card-info {
  display: flex;
  flex-direction: column;
}

.stat-card-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.stat-card-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-lg);
}

.content-section {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
  gap: var(--spacing-sm);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
}

.section-title svg {
  width: 18px;
  height: 18px;
  color: var(--color-primary);
}

.section-link {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}

.section-link:hover {
  color: var(--color-primary-light);
  text-decoration: underline;
}

.section-body {
  padding: var(--spacing-md) var(--spacing-lg);
  min-height: 200px;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 160px;
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
  to { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 160px;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 160px;
  gap: var(--spacing-sm);
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.retry-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.retry-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.task-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}

.task-item:hover {
  background: var(--color-bg-tertiary);
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
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-difficulty {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-weight: 500;
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

.goal-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.goal-item {
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}

.goal-item:hover {
  background: var(--color-bg-tertiary);
}

.goal-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xs);
}

.goal-title {
  font-size: var(--font-size-sm);
  color: var(--color-text);
}

.goal-progress-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 600;
}

/* Daily Task Card */
.daily-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--spacing-xl);
}

.daily-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.daily-header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.daily-header-left svg {
  width: 18px;
  height: 18px;
  color: var(--color-primary);
}

.daily-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.daily-overview {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.daily-body {
  padding: var(--spacing-md) var(--spacing-lg);
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
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-sm) 0;
}

.daily-group-title svg {
  width: 16px;
  height: 16px;
  color: var(--color-primary);
}

.daily-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.daily-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
  min-width: 0;
}

.daily-item:hover {
  background: var(--color-bg-tertiary);
}

.daily-item--done {
  opacity: 0.6;
}

.daily-item--link {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}

.daily-check-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  transition: color 0.15s ease;
}

.daily-check-btn:hover:not(:disabled) {
  color: var(--color-primary);
}

.daily-check-btn--done {
  color: var(--color-success);
  cursor: default;
}

.daily-check-btn:disabled {
  opacity: 0.5;
}

.daily-check-btn svg {
  width: 20px;
  height: 20px;
}

.daily-item-title {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.daily-item-title--done {
  text-decoration: line-through;
  color: var(--color-text-tertiary);
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
  font-size: var(--font-size-xs);
  padding: 1px 6px;
  background: rgba(255, 107, 107, 0.15);
  color: var(--color-error);
  border-radius: var(--radius-full);
  font-weight: 600;
  flex-shrink: 0;
}

.daily-goal-progress {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-width: 120px;
  flex-shrink: 0;
}

.daily-goal-bar {
  flex: 1;
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.daily-goal-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.daily-goal-pct {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 600;
  min-width: 32px;
  text-align: right;
}

/* Responsive */
@media (max-width: 1199px) {
  .home-page {
    padding: var(--spacing-lg);
  }
}

@media (max-width: 767px) {
  .home-page {
    padding: 12px;
  }

  .checkin-content {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .checkin-left {
    width: auto;
    flex: 1;
  }

  .checkin-btn,
  .checkin-done-badge {
    width: auto;
    justify-content: center;
    flex-shrink: 0;
  }

  .checkin-card {
    padding: 12px 14px;
    margin-bottom: 12px;
  }

  .checkin-left {
    gap: 10px;
  }

  .checkin-icon-wrap {
    width: 38px;
    height: 38px;
  }

  .checkin-icon-wrap svg {
    width: 20px;
    height: 20px;
  }

  .checkin-title {
    font-size: 15px;
  }

  .checkin-streak {
    font-size: 11px;
  }

  .checkin-btn,
  .checkin-done-badge {
    padding: 8px 14px;
    font-size: 13px;
    border-radius: var(--radius-md);
    min-width: 88px;
  }

  .checkin-btn svg,
  .checkin-done-badge svg {
    width: 16px;
    height: 16px;
  }

  .welcome-card {
    flex-direction: column;
    align-items: flex-start;
    padding: 12px 14px;
    margin-bottom: 12px;
    border-radius: var(--radius-lg);
    min-height: 0;
  }

  .welcome-icon {
    display: none;
  }

  .stats-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0;
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-bottom: var(--spacing-lg);
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .welcome-title {
    font-size: 18px;
    line-height: 1.2;
    margin-bottom: 0;
  }

  .welcome-subtitle {
    font-size: 12px;
    line-height: 1.35;
  }

  .welcome-content {
    width: 100%;
  }

  .section-header {
    flex-wrap: wrap;
  }

  .section-link {
    width: 100%;
  }

  .daily-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
  }

  .daily-overview {
    font-size: 10px;
  }

  .stat-card {
    gap: 8px;
    padding: 10px 8px;
    border: none;
    border-radius: 0;
    background: transparent;
    min-width: 0;
  }

  .stat-card-icon {
    width: 32px;
    height: 32px;
    border-radius: 10px;
  }

  .stat-card-icon svg {
    width: 16px;
    height: 16px;
  }

  .daily-item {
    flex-wrap: wrap;
    align-items: center;
  }

  .daily-streak,
  .daily-overdue,
  .task-difficulty {
    margin-left: 32px;
  }

  .daily-goal-progress {
    min-width: 100%;
    margin-left: 0;
  }

  .stat-card-value {
    font-size: 16px;
  }

  .stat-card-label {
    font-size: 11px;
  }

  .stat-card-info {
    min-width: 0;
  }

  .stat-card-label,
  .stat-card-value {
    line-height: 1.2;
  }

  .section-body {
    padding: var(--spacing-md);
    min-height: 160px;
  }

  .daily-card {
    margin-bottom: var(--spacing-lg);
  }

  .daily-body {
    padding: var(--spacing-md);
  }

  .toast {
    top: var(--spacing-md);
    left: var(--spacing-md);
    right: var(--spacing-md);
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .content-grid {
    grid-template-columns: 1fr 1fr;
  }
}

.goal-progress-bar {
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.goal-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

/* Toast notifications */
.toast {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  box-shadow: var(--shadow-xl);
  z-index: 2000;
}

.toast svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.toast--success {
  background: var(--color-success);
  color: #fff;
}

.toast--error {
  background: var(--color-error);
  color: #fff;
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
</style>
