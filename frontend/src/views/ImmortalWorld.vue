<template>
  <main class="immortal-page">
    <header class="immortal-header">
      <p class="immortal-kicker">飞升之后</p>
      <h1>仙界 · 第 {{ overview?.stage ?? 1 }} 阶</h1>
      <p>仙元与仙石由日常行动结算，阶段目标达成后可推进。</p>
    </header>

    <AppState v-if="loading && !overview" state="loading" title="正在读取仙界状态…" />
    <AppState v-else-if="error && !overview" state="error" :title="error">
      <template #actions>
        <AppButton variant="secondary" @click="load">重试</AppButton>
      </template>
    </AppState>

    <template v-else-if="overview">
      <section class="immortal-surface" aria-labelledby="immortal-state-title">
        <h2 id="immortal-state-title">仙界状态</h2>
        <div class="immortal-figures">
          <div><span>仙元</span><strong>{{ overview.essence }}</strong></div>
          <div><span>仙石</span><strong>{{ overview.immortal_stones }}</strong></div>
          <div><span>当前阶层</span><strong>第 {{ overview.stage }} 阶</strong></div>
        </div>
        <div v-if="goal" class="immortal-goal">
          <div class="immortal-row">
            <small class="immortal-muted">阶段目标</small>
            <small class="immortal-muted">{{ goal.current }} / {{ goal.required }}</small>
          </div>
          <div class="immortal-goal-track" role="progressbar" :aria-valuenow="goalPercent" aria-valuemin="0" aria-valuemax="100" aria-label="阶段目标进度">
            <span :style="{ width: goalPercent + '%' }"></span>
          </div>
        </div>
        <p v-if="stageMessage" class="immortal-muted" role="status">{{ stageMessage }}</p>
        <p v-if="error" class="immortal-muted" role="alert">{{ error }}</p>
        <div class="immortal-row">
          <button type="button" class="immortal-primary" :disabled="advancing || !canAdvance" :aria-disabled="!canAdvance" @click="advance">
            {{ advancing ? '推进中…' : canAdvance ? '推进仙界阶段' : '目标未达成' }}
          </button>
          <router-link class="immortal-link" to="/immortal/activities">查看仙界活动 →</router-link>
        </div>
      </section>

      <section v-if="overview.regions?.length" class="immortal-surface" aria-labelledby="immortal-regions-title">
        <h2 id="immortal-regions-title">可见区域</h2>
        <ul class="immortal-list">
          <li v-for="region in overview.regions" :key="region.key">
            <span>{{ region.name }}</span>
            <small>{{ region.unlocked ? '已开放' : '未解锁' }}</small>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { immortalService } from '../services/immortal'
import { getErrorMessage } from '../utils/errorMessage'
import AppState from '../components/ui/AppState.vue'
import AppButton from '../components/ui/AppButton.vue'

const overview = ref(null)
const error = ref('')
const loading = ref(false)
const advancing = ref(false)
const stageMessage = ref('')

const goal = computed(() => overview.value?.stage_goals?.[0] || null)
const goalPercent = computed(() => {
  if (!goal.value?.required) return 0
  return Math.min(100, Math.round((Number(goal.value.current) / Number(goal.value.required)) * 100))
})
const canAdvance = computed(() => Boolean(goal.value) && Number(goal.value.current) >= Number(goal.value.required))

async function load() {
  loading.value = true
  error.value = ''
  try {
    overview.value = await immortalService.getOverview()
  } catch (cause) {
    error.value = getErrorMessage(cause)
  } finally {
    loading.value = false
  }
}

async function advance() {
  if (advancing.value || !canAdvance.value) return
  advancing.value = true
  error.value = ''
  try {
    await immortalService.advanceStage(`stage:${overview.value.stage}:${Date.now()}`)
    stageMessage.value = '阶段推进成功。'
    await load()
  } catch (cause) {
    error.value = getErrorMessage(cause)
  } finally {
    advancing.value = false
  }
}

onMounted(load)
</script>
