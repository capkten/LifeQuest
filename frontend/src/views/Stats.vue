<template>
  <div class="stats-page">
    <div class="page-header">
      <h1 class="page-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M18 20V10" />
          <path d="M12 20V4" />
          <path d="M6 20v-6" />
        </svg>
        数据统计
      </h1>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchAll">重试</button>
    </div>

    <template v-else>
      <!-- Overview Cards -->
      <div class="overview-grid">
        <div class="overview-card overview-card--tasks">
          <div class="overview-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
          <div class="overview-info">
            <span class="overview-value">{{ overview.total_tasks_completed }}</span>
            <span class="overview-label">完成任务</span>
          </div>
        </div>
        <div class="overview-card overview-card--coins">
          <div class="overview-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v12M6 12h12" />
            </svg>
          </div>
          <div class="overview-info">
            <span class="overview-value">{{ overview.total_coins_earned }}</span>
            <span class="overview-label">累计金币</span>
          </div>
        </div>
        <div class="overview-card overview-card--streak">
          <div class="overview-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
          </div>
          <div class="overview-info">
            <span class="overview-value">{{ overview.current_streak }}</span>
            <span class="overview-label">当前连续</span>
          </div>
        </div>
        <div class="overview-card overview-card--active">
          <div class="overview-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
          </div>
          <div class="overview-info">
            <span class="overview-value">{{ overview.days_active }}</span>
            <span class="overview-label">活跃天数</span>
          </div>
        </div>
      </div>

      <!-- Task Completion Trend -->
      <div class="chart-section">
        <div class="chart-header">
          <h3 class="chart-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M18 20V10" />
              <path d="M12 20V4" />
              <path d="M6 20v-6" />
            </svg>
            任务完成趋势
          </h3>
          <div class="period-tabs">
            <button
              v-for="p in taskPeriods"
              :key="p.value"
              class="period-tab"
              :class="{ 'period-tab--active': taskPeriod === p.value }"
              @click="setTaskPeriod(p.value)"
            >{{ p.label }}</button>
          </div>
        </div>
        <div class="chart-body">
          <div v-if="loadingTasks" class="chart-loading"><span class="loading-spinner"></span></div>
          <div v-else-if="taskTrends.length === 0" class="chart-empty">暂无数据</div>
          <div v-else class="bar-chart">
            <div class="bar-chart-y-axis">
              <span v-for="tick in taskYTicks" :key="tick" class="y-tick">{{ tick }}</span>
            </div>
            <div class="bar-chart-area">
              <div class="bar-chart-grid">
                <div v-for="tick in taskYTicks" :key="tick" class="grid-line"></div>
              </div>
              <div class="bar-chart-bars">
                <div
                  v-for="(item, i) in taskTrends"
                  :key="i"
                  class="bar-group"
                  :title="item.date + ': ' + item.completed + ' 完成, ' + item.created + ' 创建'"
                >
                  <div class="bar-pair">
                    <div
                      class="bar bar--completed"
                      :style="{ height: barHeight(item.completed, taskMaxVal) }"
                    ></div>
                    <div
                      class="bar bar--created"
                      :style="{ height: barHeight(item.created, taskMaxVal) }"
                    ></div>
                  </div>
                  <span class="bar-label">{{ barLabel(item.date, taskPeriod) }}</span>
                </div>
              </div>
            </div>
            <div class="chart-legend">
              <span class="legend-item"><span class="legend-dot legend-dot--completed"></span>完成</span>
              <span class="legend-item"><span class="legend-dot legend-dot--created"></span>创建</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Habit Completion Rate -->
      <div class="chart-section">
        <div class="chart-header">
          <h3 class="chart-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <circle cx="12" cy="12" r="6" />
              <circle cx="12" cy="12" r="2" />
            </svg>
            习惯完成情况
          </h3>
          <div class="period-tabs">
            <button
              v-for="p in habitPeriods"
              :key="p.value"
              class="period-tab"
              :class="{ 'period-tab--active': habitPeriod === p.value }"
              @click="setHabitPeriod(p.value)"
            >{{ p.label }}</button>
          </div>
        </div>
        <div class="chart-body">
          <div v-if="loadingHabits" class="chart-loading"><span class="loading-spinner"></span></div>
          <div v-else-if="habitStats.length === 0" class="chart-empty">暂无数据</div>
          <div v-else class="line-chart-wrapper">
            <svg
              class="line-chart"
              :viewBox="'0 0 ' + lineChartWidth + ' ' + lineChartHeight"
              preserveAspectRatio="none"
            >
              <!-- Grid lines -->
              <line
                v-for="i in 4"
                :key="'hg'+i"
                :x1="linePadLeft"
                :y1="linePadTop + (i - 1) * ((lineChartHeight - linePadTop - linePadBot) / 3)"
                :x2="lineChartWidth - linePadRight"
                :y2="linePadTop + (i - 1) * ((lineChartHeight - linePadTop - linePadBot) / 3)"
                class="grid-line-svg"
              />
              <!-- Area fill -->
              <polygon :points="habitAreaPoints" class="line-area" />
              <!-- Line -->
              <polyline :points="habitLinePoints" class="line-stroke line-stroke--primary" />
              <!-- Dots -->
              <circle
                v-for="(pt, i) in habitDots"
                :key="'hd'+i"
                :cx="pt.x"
                :cy="pt.y"
                r="3"
                class="line-dot line-dot--primary"
              />
            </svg>
            <div class="line-chart-x-labels">
              <span
                v-for="(item, i) in habitXLabels"
                :key="'hl'+i"
                class="x-label"
              >{{ item }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Coin Trends -->
      <div class="chart-section">
        <div class="chart-header">
          <h3 class="chart-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v12" />
              <path d="M15 9.5c0-1.38-1.34-2.5-3-2.5s-3 1.12-3 2.5 1.34 2.5 3 2.5 3 1.12 3 2.5-1.34 2.5-3 2.5" />
            </svg>
            金币收支趋势
          </h3>
          <div class="period-tabs">
            <button
              v-for="p in coinPeriods"
              :key="p.value"
              class="period-tab"
              :class="{ 'period-tab--active': coinPeriod === p.value }"
              @click="setCoinPeriod(p.value)"
            >{{ p.label }}</button>
          </div>
        </div>
        <div class="chart-body">
          <div v-if="loadingCoins" class="chart-loading"><span class="loading-spinner"></span></div>
          <div v-else-if="coinTrends.length === 0" class="chart-empty">暂无数据</div>
          <div v-else class="line-chart-wrapper">
            <svg
              class="line-chart"
              :viewBox="'0 0 ' + lineChartWidth + ' ' + lineChartHeight"
              preserveAspectRatio="none"
            >
              <line
                v-for="i in 4"
                :key="'cg'+i"
                :x1="linePadLeft"
                :y1="linePadTop + (i - 1) * ((lineChartHeight - linePadTop - linePadBot) / 3)"
                :x2="lineChartWidth - linePadRight"
                :y2="linePadTop + (i - 1) * ((lineChartHeight - linePadTop - linePadBot) / 3)"
                class="grid-line-svg"
              />
              <!-- Earned line -->
              <polyline :points="coinEarnedLinePoints" class="line-stroke line-stroke--earned" />
              <circle
                v-for="(pt, i) in coinEarnedDots"
                :key="'ce'+i"
                :cx="pt.x"
                :cy="pt.y"
                r="3"
                class="line-dot line-dot--earned"
              />
              <!-- Spent line -->
              <polyline :points="coinSpentLinePoints" class="line-stroke line-stroke--spent" />
              <circle
                v-for="(pt, i) in coinSpentDots"
                :key="'cs'+i"
                :cx="pt.x"
                :cy="pt.y"
                r="3"
                class="line-dot line-dot--spent"
              />
            </svg>
            <div class="line-chart-x-labels">
              <span
                v-for="(item, i) in coinXLabels"
                :key="'cl'+i"
                class="x-label"
              >{{ item }}</span>
            </div>
            <div class="chart-legend">
              <span class="legend-item"><span class="legend-dot legend-dot--earned"></span>收入</span>
              <span class="legend-item"><span class="legend-dot legend-dot--spent"></span>支出</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Level Progress -->
      <div class="chart-section">
        <div class="chart-header">
          <h3 class="chart-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            等级进度
          </h3>
        </div>
        <div class="chart-body">
          <div class="level-section">
            <div class="level-info">
              <div class="level-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
                <span class="level-number">Lv.{{ levelProgress.current_level }}</span>
              </div>
              <div class="level-detail">
                <span class="level-exp">{{ levelProgress.current_exp }} / {{ levelProgress.required_exp }} EXP</span>
                <span class="level-percent">{{ levelProgress.exp_percent }}%</span>
              </div>
            </div>
            <div class="level-bar">
              <div
                class="level-bar-fill"
                :style="{ width: levelProgress.exp_percent + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { statsService } from '../services/stats'

const loading = ref(true)
const error = ref(null)

const overview = ref({
  total_tasks_completed: 0,
  total_habits: 0,
  current_streak: 0,
  total_coins_earned: 0,
  total_exp: 0,
  current_level: 1,
  days_active: 0,
})
const levelProgress = ref({ current_level: 1, current_exp: 0, required_exp: 100, exp_percent: 0 })

const taskPeriod = ref('week')
const habitPeriod = ref('week')
const coinPeriod = ref('month')

const taskTrends = ref([])
const habitStats = ref([])
const coinTrends = ref([])

const loadingTasks = ref(false)
const loadingHabits = ref(false)
const loadingCoins = ref(false)

const taskPeriods = [
  { value: 'week', label: '周' },
  { value: 'month', label: '月' },
  { value: 'year', label: '年' },
]
const habitPeriods = [
  { value: 'week', label: '周' },
  { value: 'month', label: '月' },
]
const coinPeriods = [
  { value: 'week', label: '周' },
  { value: 'month', label: '月' },
  { value: 'year', label: '年' },
]

// --- Task bar chart helpers ---
const taskMaxVal = computed(() => {
  let max = 0
  for (const item of taskTrends.value) {
    if (item.completed > max) max = item.completed
    if (item.created > max) max = item.created
  }
  return max || 1
})

const taskYTicks = computed(() => {
  const max = taskMaxVal.value
  const step = max <= 5 ? 1 : Math.ceil(max / 5)
  const ticks = []
  for (let v = 0; v <= max; v += step) ticks.push(v)
  if (ticks[ticks.length - 1] < max) ticks.push(max)
  return ticks.reverse()
})

function barHeight(val, max) {
  if (!max) return '0%'
  return Math.round((val / max) * 100) + '%'
}

function barLabel(dateStr, period) {
  if (period === 'year') return dateStr.slice(5)
  const parts = dateStr.split('-')
  return parts[2]
}

// --- Line chart layout constants ---
const lineChartWidth = 600
const lineChartHeight = 200
const linePadLeft = 10
const linePadRight = 10
const linePadTop = 20
const linePadBot = 10

const chartDrawW = lineChartWidth - linePadLeft - linePadRight
const chartDrawH = lineChartHeight - linePadTop - linePadBot

function calcLinePoints(data, key, maxVal) {
  if (!data.length) return ''
  const max = maxVal || 1
  return data.map((item, i) => {
    const x = linePadLeft + (i / Math.max(data.length - 1, 1)) * chartDrawW
    const y = linePadTop + chartDrawH - (item[key] / max) * chartDrawH
    return `${x},${y}`
  }).join(' ')
}

function calcDots(data, key, maxVal) {
  if (!data.length) return []
  const max = maxVal || 1
  return data.map((item, i) => ({
    x: linePadLeft + (i / Math.max(data.length - 1, 1)) * chartDrawW,
    y: linePadTop + chartDrawH - (item[key] / max) * chartDrawH,
  }))
}

// --- Habit line chart ---
const habitMaxVal = computed(() => {
  let max = 0
  for (const item of habitStats.value) {
    if (item.completed > max) max = item.completed
    if (item.total > max) max = item.total
  }
  return max || 1
})

const habitLinePoints = computed(() => calcLinePoints(habitStats.value, 'completed', habitMaxVal.value))
const habitDots = computed(() => calcDots(habitStats.value, 'completed', habitMaxVal.value))

const habitAreaPoints = computed(() => {
  if (!habitStats.value.length) return ''
  const max = habitMaxVal.value || 1
  const pts = habitStats.value.map((item, i) => {
    const x = linePadLeft + (i / Math.max(habitStats.value.length - 1, 1)) * chartDrawW
    const y = linePadTop + chartDrawH - (item.completed / max) * chartDrawH
    return `${x},${y}`
  })
  const firstX = linePadLeft
  const lastX = linePadLeft + chartDrawW
  const bottom = linePadTop + chartDrawH
  return `${firstX},${bottom} ${pts.join(' ')} ${lastX},${bottom}`
})

const habitXLabels = computed(() => {
  const data = habitStats.value
  if (!data.length) return []
  const step = Math.max(1, Math.floor(data.length / 7))
  return data.filter((_, i) => i % step === 0 || i === data.length - 1).map(item => {
    const parts = item.date.split('-')
    return parts[2]
  })
})

// --- Coin line chart ---
const coinMaxVal = computed(() => {
  let max = 0
  for (const item of coinTrends.value) {
    if (item.earned > max) max = item.earned
    if (item.spent > max) max = item.spent
  }
  return max || 1
})

const coinEarnedLinePoints = computed(() => calcLinePoints(coinTrends.value, 'earned', coinMaxVal.value))
const coinEarnedDots = computed(() => calcDots(coinTrends.value, 'earned', coinMaxVal.value))
const coinSpentLinePoints = computed(() => calcLinePoints(coinTrends.value, 'spent', coinMaxVal.value))
const coinSpentDots = computed(() => calcDots(coinTrends.value, 'spent', coinMaxVal.value))

const coinXLabels = computed(() => {
  const data = coinTrends.value
  if (!data.length) return []
  const step = Math.max(1, Math.floor(data.length / 7))
  return data.filter((_, i) => i % step === 0 || i === data.length - 1).map(item => {
    if (coinPeriod.value === 'year') return item.date.slice(5)
    const parts = item.date.split('-')
    return parts[2]
  })
})

// --- Data fetching ---
async function fetchOverview() {
  overview.value = await statsService.getOverview()
}

async function fetchLevel() {
  levelProgress.value = await statsService.getLevelProgress()
}

async function fetchTaskTrends() {
  loadingTasks.value = true
  try {
    taskTrends.value = await statsService.getTaskTrends(taskPeriod.value)
  } finally {
    loadingTasks.value = false
  }
}

async function fetchHabitStats() {
  loadingHabits.value = true
  try {
    habitStats.value = await statsService.getHabitStats(habitPeriod.value)
  } finally {
    loadingHabits.value = false
  }
}

async function fetchCoinTrends() {
  loadingCoins.value = true
  try {
    coinTrends.value = await statsService.getCoinTrends(coinPeriod.value)
  } finally {
    loadingCoins.value = false
  }
}

function setTaskPeriod(p) {
  taskPeriod.value = p
  fetchTaskTrends()
}

function setHabitPeriod(p) {
  habitPeriod.value = p
  fetchHabitStats()
}

function setCoinPeriod(p) {
  coinPeriod.value = p
  fetchCoinTrends()
}

async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    await Promise.all([
      fetchOverview(),
      fetchLevel(),
      fetchTaskTrends(),
      fetchHabitStats(),
      fetchCoinTrends(),
    ])
  } catch (e) {
    error.value = '加载统计数据失败，请重试。'
  } finally {
    loading.value = false
  }
}

onMounted(fetchAll)
</script>

<style scoped>
.stats-page {
  padding: var(--spacing-xl);
  width: 100%;
}

.page-header {
  margin-bottom: var(--spacing-xl);
}

.page-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.page-title svg {
  width: 28px;
  height: 28px;
  color: var(--color-primary);
}

/* Loading / Error */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: var(--spacing-md);
  color: var(--color-error);
  font-size: var(--font-size-base);
}

.retry-btn {
  padding: var(--spacing-sm) var(--spacing-xl);
  font-size: var(--font-size-sm);
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: background 0.15s ease;
}

.retry-btn:hover {
  background: var(--color-primary-light);
}

/* Overview Grid */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.overview-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: border-color 0.2s ease;
}

.overview-card:hover {
  border-color: var(--color-primary);
}

.overview-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.overview-card--tasks .overview-icon {
  background: rgba(108, 99, 255, 0.15);
}
.overview-card--tasks .overview-icon svg {
  color: var(--color-primary);
}

.overview-card--coins .overview-icon {
  background: rgba(255, 217, 61, 0.15);
}
.overview-card--coins .overview-icon svg {
  color: var(--color-warning);
}

.overview-card--streak .overview-icon {
  background: rgba(255, 107, 107, 0.15);
}
.overview-card--streak .overview-icon svg {
  color: var(--color-error);
}

.overview-card--active .overview-icon {
  background: rgba(0, 217, 255, 0.15);
}
.overview-card--active .overview-icon svg {
  color: var(--color-secondary);
}

.overview-icon svg {
  width: 24px;
  height: 24px;
}

.overview-info {
  display: flex;
  flex-direction: column;
}

.overview-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.overview-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

/* Chart Section */
.chart-section {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-xl);
  overflow: hidden;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.chart-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.chart-title svg {
  width: 18px;
  height: 18px;
  color: var(--color-primary);
}

.period-tabs {
  display: flex;
  gap: var(--spacing-xs);
}

.period-tab {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.period-tab:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.period-tab--active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.period-tab--active:hover {
  background: var(--color-primary-light);
  color: #fff;
}

.chart-body {
  padding: var(--spacing-lg);
  min-height: 260px;
}

.chart-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* Bar Chart */
.bar-chart {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.bar-chart-y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 30px;
}

.bar-chart-area {
  position: relative;
  display: flex;
  min-height: 200px;
}

.bar-chart-grid {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  pointer-events: none;
}

.grid-line {
  height: 1px;
  background: var(--color-border);
  opacity: 0.5;
}

.bar-chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  flex: 1;
  padding-top: var(--spacing-sm);
}

.bar-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
}

.bar-pair {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  width: 100%;
  height: 200px;
}

.bar {
  flex: 1;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  transition: height 0.4s ease;
  min-height: 2px;
}

.bar--completed {
  background: var(--color-primary);
}

.bar--created {
  background: var(--color-secondary);
  opacity: 0.7;
}

.bar-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  text-align: center;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: var(--spacing-lg);
  padding-top: var(--spacing-sm);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  display: inline-block;
}

.legend-dot--completed {
  background: var(--color-primary);
}

.legend-dot--created {
  background: var(--color-secondary);
  opacity: 0.7;
}

.legend-dot--earned {
  background: var(--color-success);
}

.legend-dot--spent {
  background: var(--color-error);
}

/* Line Chart */
.line-chart-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.line-chart {
  width: 100%;
  height: 200px;
}

.grid-line-svg {
  stroke: var(--color-border);
  stroke-width: 1;
  opacity: 0.5;
}

.line-stroke {
  fill: none;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.line-stroke--primary {
  stroke: var(--color-primary);
}

.line-stroke--earned {
  stroke: var(--color-success);
}

.line-stroke--spent {
  stroke: var(--color-error);
}

.line-area {
  fill: var(--color-primary);
  opacity: 0.1;
}

.line-dot {
  stroke: #fff;
  stroke-width: 2;
}

.line-dot--primary {
  fill: var(--color-primary);
}

.line-dot--earned {
  fill: var(--color-success);
}

.line-dot--spent {
  fill: var(--color-error);
}

.line-chart-x-labels {
  display: flex;
  justify-content: space-between;
  padding: 0 var(--spacing-sm);
}

.x-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
}

/* Level Progress */
.level-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.level-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.level-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.level-badge svg {
  width: 32px;
  height: 32px;
  color: var(--color-warning);
}

.level-number {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.level-detail {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.level-exp {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.level-percent {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-primary);
}

.level-bar {
  height: 12px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.level-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width 0.6s ease;
}

/* Responsive */
@media (max-width: 1199px) {
  .stats-page {
    padding: var(--spacing-lg);
  }
}

@media (max-width: 767px) {
  .stats-page {
    padding: var(--spacing-md);
  }

  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-md);
  }

  .overview-card {
    padding: var(--spacing-md);
    gap: var(--spacing-md);
  }

  .overview-icon {
    width: 40px;
    height: 40px;
  }

  .overview-icon svg {
    width: 20px;
    height: 20px;
  }

  .overview-value {
    font-size: var(--font-size-xl);
  }

  .chart-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .bar-pair {
    height: 140px;
  }

  .line-chart {
    height: 150px;
  }

  .bar-label {
    font-size: 8px;
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  .overview-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
