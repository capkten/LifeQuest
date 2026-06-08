<template>
  <div class="profile-page">
    <div class="profile-header">
      <div class="profile-avatar">
        <img v-if="avatarSrc" :src="avatarSrc" alt="用户头像" class="profile-avatar-img" />
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="8" r="4" />
          <path d="M20 21a8 8 0 1 0-16 0" />
        </svg>
      </div>
      <div class="profile-info">
        <h2 class="profile-username">
          {{ user?.username || '冒险者' }}
          <span v-if="activeTitle" class="profile-active-title">{{ activeTitle.name }}</span>
        </h2>
        <span class="profile-title">{{ user?.title || '冒险者' }}</span>
        <span class="profile-email">{{ user?.email || '' }}</span>
      </div>
      <div class="profile-actions">
        <button class="edit-profile-btn" @click="showTitleModal = true">更换称号</button>
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

    <!-- Title Change Modal -->
    <Teleport to="body">
      <div v-if="showTitleModal" class="dialog-overlay" @click.self="showTitleModal = false">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="title-dialog-title">
          <div class="dialog-header">
            <h3 id="title-dialog-title" class="dialog-title">更换称号</h3>
            <button class="dialog-close" @click="showTitleModal = false" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <div v-if="titlesLoading" class="titles-loading">加载中...</div>
            <div v-else class="titles-list">
              <div
                v-for="title in allTitles"
                :key="title.id"
                class="title-item"
                :class="{
                  'title-item--active': activeTitle?.id === title.id,
                  'title-item--locked': !isUnlocked(title.id)
                }"
                @click="isUnlocked(title.id) && activateTitle(title)"
              >
                <div class="title-item-icon">
                  <svg v-if="isUnlocked(title.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <circle cx="12" cy="8" r="7" />
                    <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <div class="title-item-info">
                  <span class="title-item-name">{{ title.name }}</span>
                  <span class="title-item-desc">
                    {{ isUnlocked(title.id) ? (title.description || '') : (title.unlock_condition || '未解锁') }}
                  </span>
                </div>
                <div v-if="activeTitle?.id === title.id" class="title-item-active-mark">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                </div>
              </div>
              <div v-if="allTitles.length === 0" class="titles-empty">暂无称号数据</div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStats } from '../composables/useUserStats'
import { achievementService } from '../services/achievement'
import { todoService } from '../services/todo'
import { titleService } from '../services/title'
import { useToast } from '../composables/useToast'
import { useAuthStore } from '../stores/auth'
import { useResolvedImage } from '../composables/useResolvedImage'

const router = useRouter()
const authStore = useAuthStore()
const { user, requiredExp, expPercent } = useUserStats()
const { successToast, errorToast, showSuccess, showError } = useToast()
const avatarSrc = useResolvedImage(computed(() => user.value?.avatar))

const stats = reactive({
  totalTasksCompleted: 0,
  maxHabitStreak: 0
})

const allTitles = ref([])
const unlockedTitleIds = ref(new Set())
const activeTitle = ref(null)
const titlesLoading = ref(false)
const showTitleModal = ref(false)

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
  fetchTitles()
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

function isUnlocked(titleId) {
  return unlockedTitleIds.value.has(titleId)
}

async function activateTitle(title) {
  try {
    await titleService.activateTitle(title.id)
    activeTitle.value = title
    await authStore.fetchUser()
    showSuccess(`称号已更换为「${title.name}」`)
    showTitleModal.value = false
  } catch (e) {
    showError(e.response?.data?.detail || '更换称号失败，请重试。')
  }
}

async function fetchTitles() {
  titlesLoading.value = true
  try {
    const [all, my] = await Promise.all([
      titleService.getAllTitles(),
      titleService.getMyTitles()
    ])
    allTitles.value = all || []
    const ids = new Set()
    for (const t of (my || [])) {
      const tid = t.title_id || t.title?.id || t.id
      if (tid) ids.add(tid)
      if (t.is_active || t.active) {
        activeTitle.value = allTitles.value.find(at => at.id === tid) || t
      }
    }
    unlockedTitleIds.value = ids
    if (!activeTitle.value && user.value?.title) {
      activeTitle.value = allTitles.value.find(t => t.name === user.value.title) || null
    }
  } catch (e) {
    // Non-critical: silently ignore
  } finally {
    titlesLoading.value = false
  }
}

function goToEditProfile() {
  router.push({ name: 'EditProfile' })
}
</script>

<style scoped>
.profile-page {
  padding: var(--page-padding-y) var(--page-padding-x);
  width: 100%;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  padding: var(--surface-padding);
  margin-bottom: var(--spacing-md);
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
  min-width: 0;
}

.profile-username {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
  word-break: break-word;
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
  white-space: nowrap;
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.stats-section {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  padding: var(--surface-padding);
  margin-bottom: var(--spacing-md);
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
  border-radius: var(--surface-radius-sm);
  padding: 14px;
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
  border-radius: var(--surface-radius);
  padding: var(--surface-padding);
  margin-bottom: var(--spacing-md);
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
  border-radius: var(--surface-radius);
  padding: var(--surface-padding);
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
  gap: 10px;
}

.achievement-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: 12px;
  background: var(--color-bg-tertiary);
  border-radius: var(--surface-radius-sm);
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
  min-width: 0;
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
    padding: var(--page-padding-y) var(--page-padding-x);
    max-width: none;
  }
}

@media (min-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .stats-section .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
    padding: var(--surface-padding);
  }

  .profile-info {
    align-items: center;
  }

  .profile-username,
  .profile-email {
    text-align: center;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stats-section .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dialog {
    max-width: 100%;
    max-height: calc(100vh - (var(--spacing-sm) * 2));
  }

  .dialog-body {
    padding: var(--spacing-md);
  }

  .toast {
    top: var(--spacing-md);
    left: var(--spacing-md);
    right: var(--spacing-md);
  }
}

/* Title display */
.profile-active-title {
  display: inline-block;
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  padding: 2px 10px;
  border-radius: var(--radius-full);
  vertical-align: middle;
  margin-left: var(--spacing-sm);
}

/* Title Modal */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.dialog {
  width: min(100% - 24px, 640px);
  max-height: min(80vh, 720px);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.dialog-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
}

.dialog-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: background 0.15s ease;
}

.dialog-close:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.dialog-close svg {
  width: 18px;
  height: 18px;
}

.dialog-body {
  padding: var(--spacing-lg);
  overflow-y: auto;
}

.titles-loading {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.titles-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.titles-empty {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.title-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: background 0.15s ease;
}

.title-item:hover:not(.title-item--locked) {
  background: var(--color-bg-tertiary);
}

.title-item--locked {
  opacity: 0.5;
  cursor: not-allowed;
}

.title-item--active {
  background: rgba(108, 99, 255, 0.1);
  border: 1px solid var(--color-primary);
}

.title-item-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--color-bg-tertiary);
}

.title-item-icon svg {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.title-item--locked .title-item-icon svg {
  color: var(--color-text-tertiary);
}

.title-item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.title-item-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
}

.title-item-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.title-item-active-mark {
  flex-shrink: 0;
}

.title-item-active-mark svg {
  width: 22px;
  height: 22px;
  color: var(--color-primary);
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

/* Responsive for profile-actions */
@media (max-width: 767px) {
  .profile-actions {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
    width: 100%;
  }

  .profile-level-badge {
    width: 56px;
    height: 56px;
    align-self: center;
  }

  .level-badge-number {
    font-size: var(--font-size-lg);
  }

  .edit-profile-btn {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: var(--font-size-sm);
  }
}
</style>
