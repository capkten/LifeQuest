<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="val => emit('update:modelValue', val)"
    :show-close="!isFocusing"
    :close-on-click-modal="!isFocusing"
    :close-on-press-escape="!isFocusing"
    class="cultivation-retreat-dialog"
    destroy-on-close
    width="580px"
    center
  >
    <div ref="modalContainer" class="retreat-modal-body" :class="{ 'fullscreen-mode': isFullscreen }">
      <!-- Header Bar -->
      <div class="retreat-header">
        <div class="retreat-title-wrap">
          <span class="realm-badge">{{ realmName }}</span>
          <h2 class="retreat-title">洞府静修 · 闭关入定</h2>
        </div>
        <div class="header-actions">
          <el-tooltip :content="isFullscreen ? '退出全屏' : '全屏沉浸'" placement="bottom">
            <el-button
              size="small"
              circle
              class="icon-action-btn"
              @click="toggleFullscreen"
            >
              <i :class="isFullscreen ? 'el-icon-crop' : 'el-icon-full-screen'">⛶</i>
            </el-button>
          </el-tooltip>
          <el-tooltip content="机缘图鉴" placement="bottom">
            <el-button
              size="small"
              circle
              class="icon-action-btn"
              @click="emit('open-catalog')"
            >
              📜
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <!-- Bound Todo Banner -->
      <div v-if="boundTodoTitle" class="bound-todo-card">
        <span class="bound-icon">🎯</span>
        <div class="bound-info">
          <span class="bound-label">本轮闭关参悟事项</span>
          <span class="bound-name">{{ boundTodoTitle }}</span>
        </div>
      </div>

      <!-- Main Countdown / Status Ring -->
      <div class="ring-wrapper">
        <RetreatCountdownRing
          :remaining-seconds="remainingSeconds"
          :total-seconds="totalSeconds"
          :is-focusing="isFocusing"
          :size="260"
        />
      </div>

      <!-- Preset Selection (When Idle) -->
      <div v-if="!activeRetreat" class="preset-section">
        <span class="section-label">选择闭关时辰</span>
        <div class="duration-presets">
          <button
            v-for="mins in [15, 25, 45, 60]"
            :key="mins"
            class="preset-chip"
            :class="{ active: selectedDuration === mins }"
            @click="selectedDuration = mins"
          >
            {{ mins }} 分钟
            <span class="preset-exp">+{{ mins * 10 }} 修为</span>
          </button>
        </div>
      </div>

      <!-- Focus In Progress Info -->
      <div v-else class="focus-progress-info">
        <p class="dao-quote">
          {{ isCompleted ? '心境升华，周天运转大圆满。' : '内照自心，不起妄念，徐徐导引真气归元。' }}
        </p>
      </div>

      <!-- Settlement / Linkage Options when completed or near completion -->
      <div v-if="boundTodoTitle && (isCompleted || canComplete)" class="todo-sync-option">
        <el-checkbox v-model="markTodoComplete">
          功成出关时，同时将此待办标记为已完成
        </el-checkbox>
      </div>

      <!-- Footer Buttons -->
      <div class="retreat-footer-controls">
        <!-- Start Button -->
        <el-button
          v-if="!activeRetreat"
          type="primary"
          size="large"
          class="ink-btn-primary retreat-cta"
          :loading="loading"
          @click="handleStart"
        >
          启关入定 ({{ selectedDuration }}分钟)
        </el-button>

        <!-- Focusing Controls -->
        <template v-else>
          <el-button
            v-if="canComplete || isCompleted"
            type="success"
            size="large"
            class="ink-btn-success retreat-cta"
            :loading="loading"
            @click="handleComplete"
          >
            出关圆满结算
          </el-button>

          <el-button
            type="danger"
            plain
            size="default"
            class="abort-btn"
            :loading="loading"
            @click="handleAbort"
          >
            中止闭关
          </el-button>
        </template>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useCultivationRetreat } from '../../composables/useCultivationRetreat.js'
import RetreatCountdownRing from './RetreatCountdownRing.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  todoItem: {
    type: Object,
    default: null,
  },
  realmName: {
    type: String,
    default: '凡人入道',
  },
})

const emit = defineEmits(['update:modelValue', 'completed', 'aborted', 'open-catalog', 'encounter'])

const {
  activeRetreat,
  remainingSeconds,
  totalSeconds,
  isFocusing,
  isCompleted,
  canComplete,
  loading,
  fetchActive,
  startRetreat,
  completeRetreat,
  abortRetreat,
} = useCultivationRetreat()

const modalContainer = ref(null)
const selectedDuration = ref(25)
const markTodoComplete = ref(true)
const isFullscreen = ref(false)

const boundTodoTitle = computed(() => {
  return props.todoItem?.title || activeRetreat.value?.todo?.title || null
})

watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen) {
      await fetchActive()
    }
  },
  { immediate: true }
)

function toggleFullscreen() {
  if (!modalContainer.value) return
  if (!document.fullscreenElement) {
    if (modalContainer.value.requestFullscreen) {
      modalContainer.value.requestFullscreen()
      isFullscreen.value = true
    }
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen()
      isFullscreen.value = false
    }
  }
}

async function handleStart() {
  try {
    const res = await startRetreat({
      targetDuration: selectedDuration.value,
      todoId: props.todoItem?.id || null,
    })
    ElMessage.success('闭关入定开始，请收摄心神')
  } catch (err) {
    ElMessage.error(err?.message || '开启闭关失败')
  }
}

async function handleComplete() {
  try {
    const res = await completeRetreat({
      markTodoComplete: markTodoComplete.value,
    })
    ElMessage.success(`出关大吉！斩获修为 +${res.exp_gained}，灵石 +${res.coins_gained}`)
    emit('completed', res)
    if (res.encounter_result) {
      emit('encounter', res.encounter_result)
    }
    emit('update:modelValue', false)
  } catch (err) {
    ElMessage.error(err?.message || '结算失败')
  }
}

async function handleAbort() {
  try {
    await ElMessageBox.confirm(
      '心神未固而强行破关，可能无法获得全部修行机缘，确定中止吗？',
      '破关确认',
      {
        confirmButtonText: '确定中止',
        cancelButtonText: '继续修行',
        type: 'warning',
      }
    )
    const res = await abortRetreat()
    ElMessage.warning('闭关已中止')
    emit('aborted', res)
    emit('update:modelValue', false)
  } catch (action) {
    // cancelled by user
  }
}
</script>

<style scoped>
.retreat-modal-body {
  background: radial-gradient(circle at 50% 20%, #1e293b 0%, #0f172a 100%);
  color: #f8fafc;
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.fullscreen-mode {
  position: fixed;
  inset: 0;
  z-index: 9999;
  border-radius: 0;
  height: 100vh;
  justify-content: center;
}

.retreat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.retreat-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.realm-badge {
  font-size: 0.75rem;
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
  padding: 2px 8px;
  border-radius: 6px;
}

.retreat-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
  color: #f1f5f9;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.icon-action-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
}

.bound-todo-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 10px 14px;
}

.bound-icon {
  font-size: 1.2rem;
}

.bound-info {
  display: flex;
  flex-direction: column;
}

.bound-label {
  font-size: 0.75rem;
  color: #94a3b8;
}

.bound-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: #e2e8f0;
}

.ring-wrapper {
  margin: 10px 0;
}

.preset-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-size: 0.85rem;
  color: #94a3b8;
}

.duration-presets {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.preset-chip {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  border-radius: 8px;
  padding: 10px 6px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
  font-size: 0.85rem;
}

.preset-chip.active {
  background: rgba(56, 189, 248, 0.15);
  border-color: #38bdf8;
  color: #38bdf8;
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
}

.preset-exp {
  font-size: 0.7rem;
  color: #94a3b8;
}

.focus-progress-info {
  text-align: center;
}

.dao-quote {
  font-size: 0.9rem;
  font-style: italic;
  color: #94a3b8;
  margin: 0;
}

.todo-sync-option {
  display: flex;
  justify-content: center;
  margin-top: -6px;
}

.retreat-footer-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.retreat-cta {
  width: 100%;
  height: 48px;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 1px;
}

.abort-btn {
  width: 100%;
}
</style>
