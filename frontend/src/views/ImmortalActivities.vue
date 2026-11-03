<template>
  <main class="immortal-page">
    <header class="immortal-header">
      <p class="immortal-kicker">仙界循环</p>
      <h1>仙界活动</h1>
      <p>每次修行都会由服务器结算仙元与仙石。</p>
    </header>

    <AppState v-if="loading && !overview" state="loading" title="正在读取仙界活动…" />
    <AppState v-else-if="error && !overview" state="error" :title="error">
      <template #actions>
        <AppButton variant="secondary" @click="load">重试</AppButton>
      </template>
    </AppState>

    <template v-else>
      <section class="immortal-surface" aria-labelledby="immortal-activities-title">
        <h2 id="immortal-activities-title">可执行活动</h2>
        <p v-if="!activities.length" class="immortal-muted">当前阶段暂无可执行的仙界活动。</p>
        <ul v-else class="immortal-list">
          <li v-for="activity in activities" :key="activity.id">
            <span>{{ activity.label }}</span>
            <button
              type="button"
              class="immortal-primary"
              :disabled="running || activity.unlocked !== true"
              :aria-disabled="activity.unlocked !== true"
              @click="run(activity)"
            >{{ running ? '处理中…' : activity.unlocked === true ? '执行一次' : '未解锁' }}</button>
          </li>
        </ul>
        <p v-if="message" class="immortal-muted" role="status">{{ message }}</p>
        <p v-if="error" class="immortal-muted" role="alert">{{ error }}</p>
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
const loading = ref(false)
const running = ref(false)
const error = ref('')
const message = ref('')

const activities = computed(() => overview.value?.activities || [])

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

async function run(activity) {
  if (running.value || activity?.unlocked !== true) return
  running.value = true
  error.value = ''
  message.value = ''
  try {
    await immortalService.runActivity(activity.id, `activity:${activity.id}:${Date.now()}`)
    message.value = '活动已记录，奖励由服务器结算。'
    await load()
  } catch (cause) {
    error.value = getErrorMessage(cause)
  } finally {
    running.value = false
  }
}

onMounted(load)
</script>
