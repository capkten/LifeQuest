<template>
  <div class="profile-page">
    <div class="profile-header">
      <div class="profile-avatar">
        <img v-if="user?.avatar" :src="user.avatar" alt="用户头像" class="profile-avatar-img" />
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="8" r="4" />
          <path d="M20 21a8 8 0 1 0-16 0" />
        </svg>
      </div>
      <div class="profile-info">
        <h2 class="profile-username">{{ user?.username || '冒险者' }}</h2>
        <span class="profile-title">{{ user?.title || '冒险者' }}</span>
        <span class="profile-email">{{ user?.email || '' }}</span>
      </div>
      <div class="profile-actions">
        <button class="edit-profile-btn" @click="goToEditProfile">编辑资料</button>
        <div class="profile-level-badge">
          <span class="level-badge-number">{{ user?.level || 1 }}</span>
          <span class="level-badge-label">等级</span>
        </div>
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
      <div class="stat-card stat-card--exp">
        <div class="stat-card-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
        </div>
        <div class="stat-card-info">
          <span class="stat-card-value">{{ user?.experience || 0 }}</span>
          <span class="stat-card-label">经验值</span>
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
    </div>

    <div class="exp-section">
      <div class="exp-header">
        <h3 class="exp-title">经验值进度</h3>
        <span class="exp-text">{{ user?.experience || 0 }} / {{ requiredExp }} XP</span>
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
      <span class="exp-percent">{{ expPercent }}% 距离下一级</span>
    </div>

    <div class="stats-section">
      <h3 class="section-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M18 20V10" />
          <path d="M12 20V4" />
          <path d="M6 20v-6" />
        </svg>
        统计数据
      </h3>
      <div class="stats-grid">
        <div class="stat-card stat-card--tasks">
          <div class="stat-card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
          <div class="stat-card-info">
            <span class="stat-card-value">{{ stats.totalTasksCompleted }}</span>
            <span class="stat-card-label">已完成任务</span>
          </div>
        </div>
        <div class="stat-card stat-card--streak">
          <div class="stat-card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
          </div>
          <div class="stat-card-info">
            <span class="stat-card-value">{{ stats.maxHabitStreak }}</span>
            <span class="stat-card-label">最佳连续天数</span>
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
            <span class="stat-card-label">累计金币</span>
          </div>
        </div>
        <div class="stat-card stat-card--exp">
          <div class="stat-card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
          </div>
          <div class="stat-card-info">
            <span class="stat-card-value">{{ user?.experience || 0 }}</span>
            <span class="stat-card-label">累计经验</span>
          </div>
        </div>
      </div>
    </div>

    <div class="achievements-section">
      <h3 class="section-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="8" r="7" />
          <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
        </svg>
        成就
      </h3>
      <div class="achievements-grid" v-if="!achievementsLoading">
        <div
          v-for="ach in mergedAchievements"
          :key="ach.id"
          class="achievement-card"
        >
          <div
            class="achievement-icon"
            :class="ach.unlocked ? 'achievement-icon--unlocked' : 'achievement-icon--locked'"
          >
            <svg v-if="ach.unlocked" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <div class="achievement-info">
            <span class="achievement-name">{{ ach.name }}</span>
            <span class="achievement-desc">{{ ach.description || '' }}</span>
            <span v-if="ach.unlocked && ach.unlocked_at" class="achievement-date">
              {{ formatDate(ach.unlocked_at) }} 解锁
            </span>
          </div>
        </div>
        <div v-if="mergedAchievements.length === 0" class="achievements-empty">
          暂无成就数据
        </div>
      </div>
      <div v-else class="achievements-grid">
        <div class="achievements-loading">加载中...</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStats } from '../composables/useUserStats'
import { achievementService } from '../services/achievement'
import { todoService } from '../services/todo'

const router = useRouter()
const { user, requiredExp, expPercent } = useUserStats()

const stats = reactive({
  totalTasksCompleted: 0,
  maxHabitStreak: 0
})

const allAchievements = ref([])
const unlockedIds = ref(new Set())
const unlockDates = ref({})
const achievementsLoading = ref(true)

const mergedAchievements = computed(() => {
  return allAchievements.value.map((ach) => ({
    ...ach,
    unlocked: unlockedIds.value.has(ach.id),
    unlocked_at: unlockDates.value[ach.id] || null
  }))
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

onMounted(async () => {
  try {
    const [all, userAchs, tasks, habits] = await Promise.all([
      achievementService.getAchievements(),
      achievementService.getUserAchievements(),
      todoService.getTasks().catch(() => []),
      todoService.getHabits().catch(() => [])
    ])

    // Achievement data
    allAchievements.value = all || []
    const ids = new Set()
    const dates = {}
    for (const ua of (userAchs || [])) {
      const achId = ua.achievement_id || ua.achievement?.id
      if (achId) {
        ids.add(achId)
        dates[achId] = ua.unlocked_at
      }
    }
    unlockedIds.value = ids
    unlockDates.value = dates

    // Stats: total completed tasks
    const taskList = Array.isArray(tasks) ? tasks : (tasks?.data || [])
    stats.totalTasksCompleted = taskList.filter(t => t.status === 'completed').length

    // Stats: max habit streak (best_streak across all habits)
    const habitList = Array.isArray(habits) ? habits : (habits?.data || [])
    stats.maxHabitStreak = habitList.reduce((max, h) => Math.max(max, h.best_streak || h.streak || 0), 0)
  } catch (e) {
    console.error('Failed to load profile data:', e)
  } finally {
    achievementsLoading.value = false
  }
})

function goToEditProfile() {
  router.push({ name: 'EditProfile' })
}
</script>

<style scoped>
.profile-page {
  padding: var(--spacing-xl);
  width: 100%;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.profile-avatar {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.profile-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-avatar svg {
  width: 40px;
  height: 40px;
  color: #fff;
}

.profile-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.profile-username {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.profile-title {
  font-size: var(--font-size-base);
  color: var(--color-primary);
  font-weight: 500;
}

.profile-email {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.profile-level-badge {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.profile-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  flex-shrink: 0;
}

.edit-profile-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-bg-tertiary);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.edit-profile-btn:hover {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.level-badge-number {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

.level-badge-label {
  font-size: var(--font-size-xs);
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
}

.stats-section {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.stats-section .stats-grid {
  margin-bottom: 0;
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

.stat-card--tasks .stat-card-icon {
  background: rgba(81, 207, 102, 0.15);
}

.stat-card--tasks .stat-card-icon svg {
  color: var(--color-success);
}

.stat-card--streak .stat-card-icon {
  background: rgba(255, 140, 50, 0.15);
}

.stat-card--streak .stat-card-icon svg {
  color: #ff8c32;
}

.stat-card--level .stat-card-icon {
  background: rgba(108, 99, 255, 0.15);
}

.stat-card--level .stat-card-icon svg {
  color: var(--color-primary);
}

.stat-card--exp .stat-card-icon {
  background: rgba(0, 217, 255, 0.15);
}

.stat-card--exp .stat-card-icon svg {
  color: var(--color-secondary);
}

.stat-card--coins .stat-card-icon {
  background: rgba(255, 217, 61, 0.15);
}

.stat-card--coins .stat-card-icon svg {
  color: var(--color-warning);
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

.exp-section {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.exp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.exp-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.exp-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.exp-bar {
  height: 10px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--spacing-sm);
}

.exp-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.exp-percent {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.achievements-section {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-lg) 0;
}

.section-title svg {
  width: 22px;
  height: 22px;
  color: var(--color-primary);
}

.achievements-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.achievement-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-lg);
  transition: background 0.15s ease;
}

.achievement-card:hover {
  background: var(--color-border);
}

.achievement-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.achievement-icon svg {
  width: 22px;
  height: 22px;
}

.achievement-icon--unlocked {
  background: rgba(81, 207, 102, 0.15);
}

.achievement-icon--unlocked svg {
  color: var(--color-success);
}

.achievement-icon--locked {
  background: rgba(150, 150, 150, 0.15);
}

.achievement-icon--locked svg {
  color: var(--color-text-tertiary);
}

.achievement-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.achievement-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
}

.achievement-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.achievement-date {
  font-size: var(--font-size-xs);
  color: var(--color-success);
  margin-top: 2px;
}

.achievements-empty,
.achievements-loading {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* Responsive */
@media (max-width: 1199px) {
  .profile-page {
    padding: var(--spacing-lg);
    max-width: none;
  }
}

@media (max-width: 900px) {
  .stats-section .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 767px) {
  .profile-page {
    padding: var(--spacing-md);
  }

  .profile-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: var(--spacing-md);
    padding: var(--spacing-lg);
  }

  .profile-info {
    align-items: center;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .stats-section .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
