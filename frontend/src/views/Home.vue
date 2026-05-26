<template>
  <div class="home-page">
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { todoService } from '../services/todo'

const authStore = useAuthStore()
const user = computed(() => authStore.user)

const tasks = ref([])
const goals = ref([])
const loadingTasks = ref(true)
const loadingGoals = ref(true)
const errorTasks = ref(null)
const errorGoals = ref(null)

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

onMounted(() => {
  fetchTasks()
  fetchGoals()
})
</script>

<style scoped>
.home-page {
  padding: var(--spacing-xl);
  max-width: 1100px;
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

/* Responsive */
@media (max-width: 1199px) {
  .home-page {
    padding: var(--spacing-lg);
  }
}

@media (max-width: 767px) {
  .home-page {
    padding: var(--spacing-md);
  }

  .welcome-card {
    flex-direction: column;
    align-items: flex-start;
    padding: var(--spacing-lg);
  }

  .welcome-icon {
    display: none;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .content-grid {
    grid-template-columns: 1fr;
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
</style>
