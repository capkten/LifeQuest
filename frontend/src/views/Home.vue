<template>
  <div class="home-page">
    <TodayWorkbench ref="todayWorkbench" class="home-workbench" @changed="refreshHomeTasks" />

    <div v-if="pageError" class="home-error" role="alert">
      <span>{{ pageError }}</span>
      <button type="button" @click="reloadPage">重试</button>
    </div>

    <section class="hero-card">
      <div class="identity-head">
        <p class="identity-eyebrow">{{ realmLine }}</p>
        <div
          class="identity-progress"
          role="progressbar"
          :aria-valuenow="progressPercent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="progressLabel"
        >
          <span class="identity-progress-name">{{ progressLabel }}</span>
          <div class="identity-progress-track">
            <span :style="{ width: progressPercent + '%' }"></span>
          </div>
          <span class="identity-progress-value">{{ progressPercent }}%</span>
        </div>
      </div>

      <div class="identity-metrics">
        <div class="identity-metric">
          <span class="identity-metric-label">境界</span>
          <strong class="metric-figure">{{ realmText }}</strong>
        </div>
        <div class="identity-metric">
          <span class="identity-metric-label">{{ stoneLabel }}</span>
          <strong class="metric-figure" :class="{ 'metric-pulse': coinsPulsing }">{{ stoneValue }}</strong>
        </div>
        <div class="identity-metric">
          <span class="identity-metric-label">连续签到</span>
          <strong class="metric-figure">{{ checkinStatus?.streak || 0 }} 天</strong>
        </div>
        <div class="identity-metric">
          <span class="identity-metric-label">今日待办</span>
          <strong class="metric-figure">{{ actionCenter?.summary?.open_count || 0 }}</strong>
        </div>
      </div>

      <div class="identity-actions">
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
          {{ checkinLoading ? '签到中…' : '立即签到' }}
        </button>
        <div v-else class="checkin-done-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M20 6L9 17l-5-5" />
          </svg>
          今日已签到
        </div>
        <div class="identity-chips">
          <button type="button" class="identity-chip" @click="todayWorkbench?.focusQuickAdd()">＋ 任务</button>
          <router-link to="/projects" class="identity-chip">◇ 项目</router-link>
          <router-link to="/finance" class="identity-chip">¥ 记账</router-link>
        </div>
      </div>
    </section>

    <TodayActionCenter
      class="home-habits"
      :data="actionCenter"
      :loading="actionCenterLoading"
      :error="actionCenterError"
      :completing-key="completingActionKey"
      @complete="handleActionComplete"
      @open="handleActionOpen"
      @retry="fetchActionCenter"
    />

    <Transition name="toast">
      <div v-if="successToast" class="toast toast--success" role="status" aria-live="polite">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M20 6L9 17l-5-5" />
        </svg>
        {{ successToast }}
      </div>
    </Transition>
    <Transition name="toast">
      <div v-if="errorToast" class="toast toast--error" role="alert" aria-live="assertive">
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { todoService } from '../services/todo'
import { checkinService } from '../services/checkin'
import { useActionCenter } from '../composables/useActionCenter'
import { useToast } from '../composables/useToast'
import { useUserStats } from '../composables/useUserStats'
import { useValuePulse } from '../composables/useValuePulse'
import { getErrorMessage } from '../utils/errorMessage'
import { labelFromServer, labelRealm, labelResource } from '../utils/displayLabels'
import TodayWorkbench from '../components/home/TodayWorkbench.vue'
import TodayActionCenter from '../components/home/TodayActionCenter.vue'

const authStore = useAuthStore()
const router = useRouter()
const todayWorkbench = ref(null)
const user = computed(() => authStore.user)
const {
  expPercent,
  cultivationPercent,
  cultivationOverview,
  loadCultivation
} = useUserStats()
const { successToast, errorToast, showSuccess, showError } = useToast()

// Reward counters pulse briefly when they go up, so earning reads as an event.
const { pulsing: coinsPulsing } = useValuePulse(computed(() => user.value?.coins ?? 0))

const pageError = ref(null)
const checkinStatus = ref(null)
const checkinLoading = ref(false)

const {
  data: actionCenter,
  loading: actionCenterLoading,
  error: actionCenterError,
  completingKey: completingActionKey,
  load: fetchActionCenter,
  complete: completeAction,
} = useActionCenter()

const realmText = computed(() => labelFromServer(
  cultivationOverview.value,
  'realm_label',
  cultivationOverview.value?.realm_key,
  labelRealm
))
const realmLine = computed(() => {
  const overview = cultivationOverview.value
  if (!overview) return '修行与生活'
  return `${realmText.value} · 第 ${overview.minor_stage ?? 1} 阶段`
})
const stoneLabel = computed(() => labelFromServer(
  cultivationOverview.value,
  'spirit_stones_label',
  'spirit_stones',
  labelResource
))
const stoneValue = computed(() => cultivationOverview.value
  ? cultivationOverview.value.spirit_stones
  : (user.value?.coins || 0))
const progressPercent = computed(() => cultivationOverview.value
  ? cultivationPercent.value
  : expPercent.value)
const progressLabel = computed(() => cultivationOverview.value ? '修为进度' : '经验值进度')

async function fetchCheckinStatus() {
  pageError.value = null
  try {
    checkinStatus.value = await checkinService.getStatus()
  } catch (e) {
    pageError.value = getErrorMessage(e, '签到状态暂时无法读取。')
  }
}

async function doCheckin() {
  if (checkinLoading.value) return
  if (checkinStatus.value?.checked_in) { showError('今天已经签到过了。'); return }
  checkinLoading.value = true
  try {
    const result = await checkinService.checkin()
    checkinStatus.value = { checked_in: true, streak: result.streak || 0 }
    const coins = result.reward_coins || 0
    const exp = result.reward_exp || 0
    showSuccess(`签到成功！获得 ${coins} 金币、${exp} 经验值`)
  } catch (e) {
    showError(getErrorMessage(e))
  } finally {
    checkinLoading.value = false
  }

  /*
   * Rewards refreshes run after the check-in settles and never reject: a
   * failing refresh must not report a successful check-in as a failure.
   */
  await Promise.allSettled([authStore.fetchUser(), loadCultivation(), fetchActionCenter()])
}

async function handleActionComplete(item) {
  try {
    await completeAction(item)
    showSuccess(`${item.title} 已完成`)
    await Promise.allSettled([authStore.fetchUser(), loadCultivation()])
    todayWorkbench.value?.load?.()
  } catch (e) {
    showError(getErrorMessage(e, '完成行动失败，请重试。'))
  }
}

function handleActionOpen() {
  router.push('/todos')
}

function refreshHomeTasks() {
  return Promise.allSettled([fetchActionCenter?.() ?? Promise.resolve()])
}

function reloadPage() {
  return Promise.allSettled([fetchCheckinStatus(), loadCultivation(), fetchActionCenter?.() ?? Promise.resolve()])
}

function dailyHabitBlockReason(habit) {
  if (habit.completed_today) return '该习惯今天已经完成，明天再来继续。'
  if (habit.paused_today === true || habit.is_active === false) return '该习惯已暂停。'
  if (habit.excused_today === true) return '该习惯今天已请假。'
  if (habit.scheduled_today === false) return '今天不是该习惯的计划日。'
  if (habit.frequency === 'weekly_target' && habit.weekly_remaining <= 0) return '本周已完成目标次数，下周再继续。'
  return ''
}

async function completeDailyHabit(habit) {
  if (completingActionKey.value !== null) return
  const blockReason = dailyHabitBlockReason(habit)
  if (blockReason) {
    showError(blockReason)
    return
  }
  try {
    await todoService.completeHabit(habit.id)
    showSuccess('习惯完成！')
    await refreshHomeTasks()
  } catch (e) {
    showError(getErrorMessage(e))
  }
}

onMounted(() => {
  loadCultivation().catch((e) => showError(getErrorMessage(e)))
  fetchCheckinStatus()
  fetchActionCenter().catch(() => {})
})
</script>

<style scoped>
.home-page {
  position: relative;
  isolation: isolate;
  display: grid;
  gap: var(--page-gap);
  width: 100%;
  min-height: calc(100dvh - var(--header-height) - (var(--page-padding-y) * 2));
}

.home-page::before {
  content: '';
  position: absolute;
  inset: calc(var(--page-padding-y) * -1) calc(var(--page-padding-x) * -1);
  background: var(--home-canvas-wash), var(--home-canvas);
  z-index: -1;
  pointer-events: none;
}

.hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px clamp(20px, 4vw, 56px);
  padding: clamp(14px, 1.8vw, 20px) clamp(18px, 2.4vw, 28px);
  border: 0;
  border-radius: 20px;
  background: linear-gradient(120deg, rgba(255, 255, 255, 0.96) 0%, rgba(250, 254, 252, 0.96) 100%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03), 0 14px 34px -26px rgba(15, 23, 42, 0.32);
}

.identity-head {
  display: grid;
  gap: 8px;
  min-width: 200px;
  max-width: 320px;
  flex: 0 1 260px;
}

.identity-eyebrow {
  margin: 0;
  color: var(--rank-1-accent);
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.identity-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.identity-progress-name {
  color: var(--home-ink-tertiary);
  font-size: 11.5px;
  white-space: nowrap;
}

.identity-progress-track {
  flex: 1;
  min-width: 60px;
  height: 5px;
  border-radius: 999px;
  background: #E6EFEC;
  overflow: hidden;
}

.identity-progress-track span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #12B886 0%, #38D9A9 100%);
  transition: width 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.identity-progress-value {
  color: var(--home-ink-tertiary);
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
}

.identity-metrics {
  display: grid;
  grid-template-columns: repeat(4, auto);
  gap: 0;
}

.identity-metric {
  display: grid;
  gap: 2px;
  padding: 0 clamp(10px, 1.4vw, 16px);
  border-left: 1px solid var(--home-hairline);
  min-width: 0;
}

.identity-metric:first-child {
  border-left: 0;
  padding-left: 0;
}

.identity-metric-label {
  color: var(--home-ink-tertiary);
  font-size: 11px;
}

.identity-metric .metric-figure {
  font-size: 16px;
  font-weight: 650;
  letter-spacing: -0.01em;
  color: var(--color-text);
  white-space: nowrap;
  overflow-wrap: anywhere;
}

.identity-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.checkin-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 40px;
  padding: 8px 16px;
  border: 0;
  border-radius: 999px;
  background: var(--rank-1-accent);
  color: #FFFFFF;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: transform 160ms cubic-bezier(0.22, 1, 0.36, 1), box-shadow 160ms ease;
}

.checkin-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px -12px rgba(15, 138, 103, 0.65);
}

.checkin-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.checkin-btn svg {
  width: 16px;
  height: 16px;
}

.checkin-done-badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 40px;
  padding: 8px 15px;
  border-radius: 999px;
  background: var(--rank-1-chip);
  color: var(--rank-1-accent);
  font-weight: 600;
  font-size: 13px;
  white-space: nowrap;
}

.checkin-done-badge svg {
  width: 16px;
  height: 16px;
}

.identity-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.identity-chip {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--home-hairline);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 12.5px;
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
  transition: background 160ms ease, color 160ms ease;
}

.identity-chip:hover {
  background: var(--home-soft);
  color: var(--color-text);
}

.identity-chip:focus-visible,
.checkin-btn:focus-visible {
  outline: 2px solid var(--rank-1-accent);
  outline-offset: 3px;
}

.home-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 14px;
  background: #FEF3F2;
  color: #b42318;
  font-size: 13.5px;
}

.home-error button {
  min-height: 40px;
  padding: 6px 14px;
  border-radius: 10px;
  border: 1px solid rgba(180, 35, 24, 0.25);
  background: #FFFFFF;
  color: #b42318;
  cursor: pointer;
}

.toast {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: 2000;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 12px 18px;
  border-radius: 14px;
  font-size: 13.5px;
  font-weight: 600;
  color: #FFFFFF;
  box-shadow: var(--shadow-lg);
}

.toast svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.toast--success {
  background: var(--rank-1-accent);
}

.toast--error {
  background: #B42318;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 180ms ease, transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 1080px) {
  .hero-card {
    justify-content: flex-start;
  }

  .identity-head {
    flex: 1 1 200px;
  }

  .identity-metrics {
    flex: 1 1 100%;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    padding-top: 12px;
    border-top: 1px solid var(--home-hairline);
  }

  .identity-metric:first-child {
    padding-left: 0;
  }
}

@media (max-width: 600px) {
  .hero-card {
    gap: 12px;
    padding: 16px;
    border-radius: 18px;
  }

  .identity-head {
    flex: 1 1 100%;
    max-width: none;
  }

  .identity-metrics {
    gap: 10px 0;
  }

  .identity-metric {
    padding: 0 10px;
  }

  .identity-metric:nth-child(3) {
    border-left: 0;
    padding-left: 0;
  }

  .identity-actions {
    flex: 1 1 100%;
    justify-content: space-between;
    gap: 8px;
  }

  .checkin-btn,
  .checkin-done-badge {
    flex: 1 1 auto;
    justify-content: center;
    min-height: 44px;
  }

  .identity-chips {
    flex: 0 0 auto;
  }

  .identity-chip {
    min-height: 44px;
    padding: 6px 10px;
  }

  .toast {
    top: calc(var(--header-height) + 10px);
    left: var(--spacing-md);
    right: var(--spacing-md);
  }
}

@media (prefers-reduced-motion: reduce) {
  .identity-progress-track span,
  .checkin-btn,
  .toast-enter-active,
  .toast-leave-active {
    transition: none;
  }
}
</style>
