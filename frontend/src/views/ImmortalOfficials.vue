<template>
  <main class="immortal-page">
    <header class="immortal-header">
      <p class="immortal-kicker">仙界治理</p>
      <h1>仙官委托</h1>
      <p>接取仙官委托可获得仙界资源，委托结果由服务器结算。</p>
    </header>

    <AppState v-if="loading && !overview" state="loading" title="正在读取仙官状态…" />
    <AppState v-else-if="error && !overview" state="error" :title="error">
      <template #actions>
        <AppButton variant="secondary" @click="load">重试</AppButton>
      </template>
    </AppState>

    <template v-else-if="overview">
      <section class="immortal-surface" aria-labelledby="immortal-officials-title">
        <h2 id="immortal-officials-title">当前可见仙官</h2>
        <p v-if="!overview.officials?.length" class="immortal-muted">当前暂无可接委托，新的仙官会随阶段推进解锁。</p>
        <ul v-else class="immortal-list">
          <li v-for="official in overview.officials" :key="official.id || official.key">
            <span>{{ official.name }}</span>
            <button
              type="button"
              class="immortal-primary"
              :disabled="busy || official.unlocked !== true"
              :aria-disabled="official.unlocked !== true"
              @click="commission(official)"
            >{{ busy ? '处理中…' : official.unlocked === true ? '接取委托' : '未解锁' }}</button>
          </li>
        </ul>
        <p v-if="message" class="immortal-muted" role="status">{{ message }}</p>
        <p v-if="error" class="immortal-muted" role="alert">{{ error }}</p>
      </section>
    </template>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { immortalService } from '../services/immortal'
import { getErrorMessage } from '../utils/errorMessage'
import AppState from '../components/ui/AppState.vue'
import AppButton from '../components/ui/AppButton.vue'

const overview = ref(null)
const loading = ref(false)
const error = ref('')
const message = ref('')
const busy = ref(false)

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

async function commission(official) {
  if (busy.value || official?.unlocked !== true) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    await immortalService.commission(official.key, `commission:${official.key}:${Date.now()}`)
    message.value = '仙官委托已完成，奖励由服务器结算。'
    await load()
  } catch (cause) {
    error.value = getErrorMessage(cause)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>
