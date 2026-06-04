<template>
  <div class="calendar-page">
    <!-- Header -->
    <div class="calendar-header">
      <div class="calendar-nav">
        <button class="nav-btn" @click="prevMonth" aria-label="上一月">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <h2 class="calendar-title">{{ currentYear }}年{{ currentMonth + 1 }}月</h2>
        <button class="nav-btn" @click="nextMonth" aria-label="下一月">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>
      <button class="today-btn" @click="goToday">今天</button>
    </div>

    <div class="calendar-body">
      <!-- Calendar Grid -->
      <div class="calendar-grid-wrapper">
        <!-- Weekday headers -->
        <div class="calendar-weekdays">
          <span v-for="day in weekdays" :key="day" class="weekday-cell">{{ day }}</span>
        </div>
        <!-- Day cells -->
        <div class="calendar-grid">
          <div
            v-for="(cell, idx) in calendarCells"
            :key="idx"
            class="day-cell"
            :class="{
              'day-cell--other': !cell.isCurrentMonth,
              'day-cell--today': cell.isToday,
              'day-cell--selected': cell.date === selectedDate,
            }"
            @click="selectDate(cell.date)"
          >
            <span class="day-number">{{ cell.dayNumber }}</span>
            <div class="event-dots">
              <span
                v-for="dot in cell.dots.slice(0, 3)"
                :key="dot.type + dot.id"
                class="event-dot"
                :class="'event-dot--' + dot.type"
                :style="dot.type === 'task' && dot.project_color ? { background: dot.project_color } : undefined"
              ></span>
              <span v-if="cell.dots.length > 3" class="event-more">+{{ cell.dots.length - 3 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Day Detail Panel -->
      <div class="day-detail" :class="{ 'day-detail--open': selectedDate }">
        <template v-if="selectedDate">
          <div class="detail-header">
            <h3 class="detail-date">{{ formatSelectedDate }}</h3>
            <button class="detail-close" @click="selectedDate = null" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <div v-if="loadingDetail" class="detail-loading">
            <span class="loading-spinner"></span>
          </div>

          <div v-else-if="dayDetail" class="detail-content">
            <!-- Check-in status -->
            <div v-if="dayDetail.checked_in" class="detail-checkin">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              已签到
            </div>

            <!-- Tasks -->
            <div v-if="dayDetail.tasks.length > 0" class="detail-section">
              <h4 class="detail-section-title">
                <span class="dot dot--task"></span>
                任务 ({{ dayDetail.tasks.length }})
              </h4>
              <div
                v-for="task in dayDetail.tasks"
                :key="task.id"
                class="detail-item detail-item--task"
                @click="goToTodos"
              >
                <span class="detail-item-status" :class="'detail-item-status--' + task.status"></span>
                <div class="detail-item-info">
                  <span class="detail-item-title">{{ task.title }}</span>
                  <div class="detail-item-tags">
                    <span class="detail-item-badge" :class="'detail-item-badge--' + task.difficulty">
                      {{ difficultyLabel(task.difficulty) }}
                    </span>
                    <span v-if="task.project_name" class="detail-project-tag" :style="{ borderColor: task.project_color || '#0EA5E9' }">
                      {{ task.project_name }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Goals -->
            <div v-if="dayDetail.goals.length > 0" class="detail-section">
              <h4 class="detail-section-title">
                <span class="dot dot--goal"></span>
                目标 ({{ dayDetail.goals.length }})
              </h4>
              <div
                v-for="goal in dayDetail.goals"
                :key="goal.id"
                class="detail-item detail-item--goal"
              >
                <div class="detail-item-info">
                  <span class="detail-item-title">{{ goal.title }}</span>
                  <div class="goal-progress-mini">
                    <div class="goal-progress-mini-bar">
                      <div
                        class="goal-progress-mini-fill"
                        :style="{ width: Math.round(goal.progress || 0) + '%' }"
                      ></div>
                    </div>
                    <span class="goal-progress-mini-text">{{ Math.round(goal.progress || 0) }}%</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Habits -->
            <div v-if="dayDetail.habits.length > 0" class="detail-section">
              <h4 class="detail-section-title">
                <span class="dot dot--habit"></span>
                习惯 ({{ dayDetail.habits.length }})
              </h4>
              <div
                v-for="habit in dayDetail.habits"
                :key="habit.id"
                class="detail-item detail-item--habit"
              >
                <div class="detail-item-info">
                  <span class="detail-item-title">{{ habit.title }}</span>
                  <span class="detail-item-meta">
                    {{ frequencyLabel(habit.frequency) }} | 连续 {{ habit.streak }} 天
                  </span>
                </div>
              </div>
            </div>

            <!-- Empty state -->
            <div
              v-if="dayDetail.tasks.length === 0 && dayDetail.goals.length === 0 && dayDetail.habits.length === 0 && !dayDetail.checked_in"
              class="detail-empty"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              <p>当日无事件</p>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="detail-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
              <circle cx="12" cy="15" r="1" fill="currentColor" stroke="none" />
            </svg>
            <p>点击日期查看详情</p>
          </div>
        </template>
      </div>
    </div>

    <!-- Mobile detail overlay -->
    <Transition name="overlay">
      <div v-if="selectedDate && isMobile" class="mobile-overlay" @click.self="selectedDate = null">
        <Transition name="sheet">
          <div v-if="selectedDate" class="mobile-sheet">
            <div class="mobile-sheet-handle"></div>
            <div class="detail-header">
              <h3 class="detail-date">{{ formatSelectedDate }}</h3>
              <button class="detail-close" @click="selectedDate = null" aria-label="关闭">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div v-if="loadingDetail" class="detail-loading">
              <span class="loading-spinner"></span>
            </div>
            <div v-else-if="dayDetail" class="detail-content">
              <div v-if="dayDetail.checked_in" class="detail-checkin">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                已签到
              </div>
              <div v-if="dayDetail.tasks.length > 0" class="detail-section">
                <h4 class="detail-section-title">
                  <span class="dot dot--task"></span>
                  任务 ({{ dayDetail.tasks.length }})
                </h4>
                <div
                  v-for="task in dayDetail.tasks"
                  :key="task.id"
                  class="detail-item detail-item--task"
                  @click="goToTodos"
                >
                  <span class="detail-item-status" :class="'detail-item-status--' + task.status"></span>
                  <div class="detail-item-info">
                    <span class="detail-item-title">{{ task.title }}</span>
                    <div class="detail-item-tags">
                      <span class="detail-item-badge" :class="'detail-item-badge--' + task.difficulty">
                        {{ difficultyLabel(task.difficulty) }}
                      </span>
                      <span v-if="task.project_name" class="detail-project-tag" :style="{ borderColor: task.project_color || '#0EA5E9' }">
                        {{ task.project_name }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="dayDetail.goals.length > 0" class="detail-section">
                <h4 class="detail-section-title">
                  <span class="dot dot--goal"></span>
                  目标 ({{ dayDetail.goals.length }})
                </h4>
                <div
                  v-for="goal in dayDetail.goals"
                  :key="goal.id"
                  class="detail-item detail-item--goal"
                >
                  <div class="detail-item-info">
                    <span class="detail-item-title">{{ goal.title }}</span>
                    <div class="goal-progress-mini">
                      <div class="goal-progress-mini-bar">
                        <div
                          class="goal-progress-mini-fill"
                          :style="{ width: Math.round(goal.progress || 0) + '%' }"
                        ></div>
                      </div>
                      <span class="goal-progress-mini-text">{{ Math.round(goal.progress || 0) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="dayDetail.habits.length > 0" class="detail-section">
                <h4 class="detail-section-title">
                  <span class="dot dot--habit"></span>
                  习惯 ({{ dayDetail.habits.length }})
                </h4>
                <div
                  v-for="habit in dayDetail.habits"
                  :key="habit.id"
                  class="detail-item detail-item--habit"
                >
                  <div class="detail-item-info">
                    <span class="detail-item-title">{{ habit.title }}</span>
                    <span class="detail-item-meta">
                      {{ frequencyLabel(habit.frequency) }} | 连续 {{ habit.streak }} 天
                    </span>
                  </div>
                </div>
              </div>
              <div
                v-if="dayDetail.tasks.length === 0 && dayDetail.goals.length === 0 && dayDetail.habits.length === 0 && !dayDetail.checked_in"
                class="detail-empty"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                <p>当日无事件</p>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { calendarService } from '../services/calendar'

const router = useRouter()

const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const now = new Date()
const currentMonth = ref(now.getMonth())
const currentYear = ref(now.getFullYear())
const events = ref([])
const selectedDate = ref(null)
const dayDetail = ref(null)
const loadingDetail = ref(false)
const loadingEvents = ref(false)
const isMobile = ref(false)

function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

// Build calendar grid cells
const calendarCells = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const cells = []

  // First day of month (0=Sun, adjust to Mon-based)
  const firstDay = new Date(year, month, 1)
  let startWeekday = firstDay.getDay() // 0=Sun
  startWeekday = startWeekday === 0 ? 6 : startWeekday - 1 // Convert to Mon=0

  // Last day of month
  const lastDay = new Date(year, month + 1, 0)
  const daysInMonth = lastDay.getDate()

  // Today string
  const todayStr = formatDateStr(now.getFullYear(), now.getMonth(), now.getDate())

  // Build event lookup by date
  const eventsByDate = {}
  for (const ev of events.value) {
    if (!eventsByDate[ev.date]) eventsByDate[ev.date] = []
    eventsByDate[ev.date].push(ev)
  }

  // Previous month padding
  const prevMonthLastDay = new Date(year, month, 0).getDate()
  for (let i = startWeekday - 1; i >= 0; i--) {
    const dayNum = prevMonthLastDay - i
    const prevMonth = month === 0 ? 11 : month - 1
    const prevYear = month === 0 ? year - 1 : year
    const dateStr = formatDateStr(prevYear, prevMonth, dayNum)
    cells.push({
      dayNumber: dayNum,
      date: dateStr,
      isCurrentMonth: false,
      isToday: dateStr === todayStr,
      dots: eventsByDate[dateStr] || [],
    })
  }

  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = formatDateStr(year, month, d)
    cells.push({
      dayNumber: d,
      date: dateStr,
      isCurrentMonth: true,
      isToday: dateStr === todayStr,
      dots: eventsByDate[dateStr] || [],
    })
  }

  // Next month padding to fill 6 rows (42 cells)
  const remaining = 42 - cells.length
  for (let d = 1; d <= remaining; d++) {
    const nextMonth = month === 11 ? 0 : month + 1
    const nextYear = month === 11 ? year + 1 : year
    const dateStr = formatDateStr(nextYear, nextMonth, d)
    cells.push({
      dayNumber: d,
      date: dateStr,
      isCurrentMonth: false,
      isToday: dateStr === todayStr,
      dots: eventsByDate[dateStr] || [],
    })
  }

  return cells
})

const formatSelectedDate = computed(() => {
  if (!selectedDate.value) return ''
  const parts = selectedDate.value.split('-')
  return `${parts[0]}年${parseInt(parts[1])}月${parseInt(parts[2])}日`
})

function formatDateStr(year, month, day) {
  const m = String(month + 1).padStart(2, '0')
  const d = String(day).padStart(2, '0')
  return `${year}-${m}-${d}`
}

function getMonthRange(year, month) {
  const start = formatDateStr(year, month, 1)
  const lastDay = new Date(year, month + 1, 0).getDate()
  const end = formatDateStr(year, month, lastDay)
  // Also include padding range (prev/next month days visible)
  const firstDay = new Date(year, month, 1)
  let startWeekday = firstDay.getDay()
  startWeekday = startWeekday === 0 ? 6 : startWeekday - 1
  const rangeStart = new Date(year, month, 1 - startWeekday)
  const totalCells = 42
  const rangeEnd = new Date(rangeStart)
  rangeEnd.setDate(rangeStart.getDate() + totalCells - 1)

  return {
    start: `${rangeStart.getFullYear()}-${String(rangeStart.getMonth() + 1).padStart(2, '0')}-${String(rangeStart.getDate()).padStart(2, '0')}`,
    end: `${rangeEnd.getFullYear()}-${String(rangeEnd.getMonth() + 1).padStart(2, '0')}-${String(rangeEnd.getDate()).padStart(2, '0')}`,
  }
}

async function fetchEvents() {
  loadingEvents.value = true
  try {
    const range = getMonthRange(currentYear.value, currentMonth.value)
    events.value = await calendarService.getEvents(range.start, range.end)
  } catch (e) {
    events.value = []
  } finally {
    loadingEvents.value = false
  }
}

async function selectDate(dateStr) {
  selectedDate.value = dateStr
  loadingDetail.value = true
  dayDetail.value = null
  try {
    dayDetail.value = await calendarService.getDayDetail(dateStr)
  } catch (e) {
    dayDetail.value = null
  } finally {
    loadingDetail.value = false
  }
}

function prevMonth() {
  if (currentMonth.value === 0) {
    currentMonth.value = 11
    currentYear.value--
  } else {
    currentMonth.value--
  }
  selectedDate.value = null
  dayDetail.value = null
}

function nextMonth() {
  if (currentMonth.value === 11) {
    currentMonth.value = 0
    currentYear.value++
  } else {
    currentMonth.value++
  }
  selectedDate.value = null
  dayDetail.value = null
}

function goToday() {
  const today = new Date()
  currentMonth.value = today.getMonth()
  currentYear.value = today.getFullYear()
  selectedDate.value = formatDateStr(today.getFullYear(), today.getMonth(), today.getDate())
  selectDate(selectedDate.value)
}

function goToTodos() {
  router.push('/todos')
}

function difficultyLabel(diff) {
  const map = { easy: '简单', medium: '中等', hard: '困难' }
  return map[diff] || diff
}

function frequencyLabel(freq) {
  const map = { daily: '每天', weekly: '每周', monthly: '每月' }
  return map[freq] || freq
}

// Fetch events when month changes
watch([currentMonth, currentYear], () => {
  fetchEvents()
})

onMounted(() => {
  fetchEvents()
})
</script>

<style scoped>
.calendar-page {
  padding: var(--spacing-xl);
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
}

/* Header */
.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-xl);
}

.calendar-nav {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.nav-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text);
  transition: all 0.15s ease;
}

.nav-btn:hover {
  background: var(--color-bg-tertiary);
  border-color: var(--color-primary);
}

.nav-btn svg {
  width: 18px;
  height: 18px;
}

.calendar-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text);
  min-width: 120px;
  text-align: center;
  margin: 0;
}

.today-btn {
  padding: var(--spacing-xs) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s ease;
}

.today-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

/* Body layout */
.calendar-body {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: var(--spacing-xl);
}

/* Calendar Grid */
.calendar-grid-wrapper {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  border-bottom: 1px solid var(--color-border);
}

.weekday-cell {
  padding: var(--spacing-sm) 0;
  text-align: center;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-tertiary);
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

.day-cell {
  aspect-ratio: 1 / 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: var(--spacing-xs);
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
  position: relative;
  min-height: 64px;
}

.day-cell:hover {
  background: var(--color-bg-tertiary);
}

.day-cell--other {
  opacity: 0.35;
}

.day-cell--today {
  position: relative;
}

.day-cell--today .day-number {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-full);
  font-weight: 700;
}

.day-cell--selected {
  background: var(--color-primary);
  background: rgba(108, 99, 255, 0.08);
  border-radius: var(--radius-md);
}

.day-number {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
}

.day-cell--other .day-number {
  color: var(--color-text-tertiary);
}

/* Event dots */
.event-dots {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-wrap: wrap;
  justify-content: center;
  max-width: 100%;
}

.event-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.event-dot--task {
  background: #4a9eff;
}

.event-dot--goal {
  background: #a855f7;
}

.event-dot--habit {
  background: #22c55e;
}

.event-dot--checkin {
  background: #eab308;
}

.event-more {
  font-size: 9px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  line-height: 1;
}

/* Detail Panel */
.day-detail {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  height: fit-content;
  max-height: calc(100vh - 180px);
  overflow-y: auto;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.detail-date {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.detail-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all 0.15s ease;
}

.detail-close:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.detail-close svg {
  width: 16px;
  height: 16px;
}

.detail-loading {
  display: flex;
  justify-content: center;
  padding: var(--spacing-xl) 0;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Detail content */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.detail-checkin {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(81, 207, 102, 0.12);
  color: var(--color-success);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  width: fit-content;
}

.detail-checkin svg {
  width: 18px;
  height: 18px;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.detail-section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0;
  padding-bottom: var(--spacing-xs);
  border-bottom: 1px solid var(--color-border);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.dot--task {
  background: #4a9eff;
}

.dot--goal {
  background: #a855f7;
}

.dot--habit {
  background: #22c55e;
}

/* Detail items */
.detail-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}

.detail-item--task {
  cursor: pointer;
}

.detail-item:hover {
  background: var(--color-bg-tertiary);
}

.detail-item-status {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
  margin-top: 5px;
}

.detail-item-status--pending {
  background: var(--color-text-tertiary);
}

.detail-item-status--in_progress {
  background: var(--color-secondary);
}

.detail-item-status--completed {
  background: var(--color-success);
}

.detail-item-status--cancelled {
  background: var(--color-error);
}

.detail-item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.detail-item-title {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-item-badge {
  display: inline-block;
  width: fit-content;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.detail-item-badge--easy {
  background: rgba(81, 207, 102, 0.15);
  color: var(--color-success);
}

.detail-item-badge--medium {
  background: rgba(255, 217, 61, 0.15);
  color: var(--color-warning);
}

.detail-item-badge--hard {
  background: rgba(255, 107, 107, 0.15);
  color: var(--color-error);
}

.detail-item-tags {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  flex-wrap: wrap;
}

.detail-project-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  border: 1px solid;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  background: var(--color-bg-tertiary);
}

.detail-item-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* Goal progress mini */
.goal-progress-mini {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.goal-progress-mini-bar {
  flex: 1;
  height: 4px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.goal-progress-mini-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.goal-progress-mini-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: 600;
  flex-shrink: 0;
}

/* Empty and placeholder */
.detail-empty,
.detail-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-2xl) 0;
  color: var(--color-text-tertiary);
}

.detail-empty svg,
.detail-placeholder svg {
  width: 40px;
  height: 40px;
  opacity: 0.5;
}

.detail-empty p,
.detail-placeholder p {
  font-size: var(--font-size-sm);
  margin: 0;
}

/* Mobile overlay */
.mobile-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.mobile-sheet {
  width: 100%;
  max-height: 70vh;
  background: var(--color-card);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  padding: var(--spacing-md) var(--spacing-lg) var(--spacing-xl);
  overflow-y: auto;
}

.mobile-sheet-handle {
  width: 40px;
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  margin: 0 auto var(--spacing-md);
}

/* Overlay transitions */
.overlay-enter-active,
.overlay-leave-active {
  transition: opacity 0.2s ease;
}

.overlay-enter-from,
.overlay-leave-to {
  opacity: 0;
}

.sheet-enter-active,
.sheet-leave-active {
  transition: transform 0.3s ease;
}

.sheet-enter-from,
.sheet-leave-to {
  transform: translateY(100%);
}

/* Responsive */
@media (max-width: 1199px) {
  .calendar-page {
    padding: var(--spacing-lg);
  }

  .calendar-body {
    grid-template-columns: 1fr 300px;
  }
}

@media (max-width: 767px) {
  .calendar-page {
    padding: var(--spacing-md);
  }

  .calendar-body {
    grid-template-columns: 1fr;
  }

  .day-detail {
    display: none;
  }

  .day-cell {
    min-height: 52px;
    aspect-ratio: auto;
    padding: 4px 2px;
  }

  .day-number {
    font-size: var(--font-size-xs);
  }

  .event-dot {
    width: 4px;
    height: 4px;
  }

  .event-more {
    font-size: 8px;
  }
}
</style>
