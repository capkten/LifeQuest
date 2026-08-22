<template>
  <main class="immortal-page">
    <header><p>飞升之后</p><h1>仙界世界</h1><button type="button" @click="load">重试</button></header>
    <p v-if="error" role="alert">{{ error }}</p>
    <section v-else-if="overview" class="immortal-card">
      <h2>{{ overview.realm_key }} · 第 {{ overview.stage }} 阶</h2>
      <dl><div><dt>仙元</dt><dd>{{ overview.essence }}</dd></div><div><dt>仙石</dt><dd>{{ overview.immortal_stones }}</dd></div></dl>
      <p>区域、仙官与阶段目标由服务器返回。</p>
      <p v-if="stageMessage" role="status">{{ stageMessage }}</p>
      <button type="button" :disabled="advancing" :aria-disabled="!canAdvance" @click="advance">推进仙界阶段</button>
      <router-link to="/immortal/activities">查看仙界活动</router-link>
    </section>
    <p v-else>正在读取仙界状态...</p>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { immortalService } from '../services/immortal'
import { getErrorMessage } from '../utils/errorMessage'

const overview = ref(null)
const error = ref(''), advancing = ref(false), stageMessage = ref('')
const canAdvance = computed(() => Number(overview.value?.stage_goals?.[0]?.current) >= Number(overview.value?.stage_goals?.[0]?.required))
async function load() { error.value = ''; try { overview.value = await immortalService.getOverview() } catch (cause) { error.value = getErrorMessage(cause) } }
async function advance() { if (advancing.value || !canAdvance.value) return; advancing.value = true; error.value = ''; try { await immortalService.advanceStage(`stage:${overview.value.stage}:${Date.now()}`); stageMessage.value = '阶段推进成功。'; await load() } catch (cause) { error.value = getErrorMessage(cause) } finally { advancing.value = false } }
onMounted(load)
</script>

<style scoped>
.immortal-page { display: grid; gap: 24px; padding: 24px; }.immortal-card { display: grid; gap: 16px; padding: 24px; border: 1px solid var(--color-border); border-radius: 16px; background: var(--color-card); } dl { display: flex; gap: 24px; } dt { color: var(--color-text-secondary); } dd { margin: 4px 0 0; font-size: 1.5rem; }
</style>
