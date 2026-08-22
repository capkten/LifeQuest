<template>
  <main class="immortal-page">
    <header><p>仙界治理</p><h1>仙官委托</h1></header>
    <p v-if="error" role="alert">{{ error }}</p>
    <section v-else-if="overview" class="official-card">
      <h2>当前可见仙官</h2>
      <p v-if="!overview.officials?.length">当前暂无可接委托，新的仙官会随阶段推进解锁。</p>
      <ul v-else><li v-for="official in overview.officials" :key="official.id || official.key"><span>{{ official.name }}</span><button type="button" :disabled="busy" :aria-disabled="official.unlocked !== true" @click="commission(official)">接取委托</button></li></ul>
      <p v-if="message" role="status">{{ message }}</p>
    </section>
    <p v-else>正在读取仙官状态...</p>
  </main>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { immortalService } from '../services/immortal'
import { getErrorMessage } from '../utils/errorMessage'
const overview = ref(null), error = ref(''), message = ref(''), busy = ref(false)
async function load() { try { overview.value = await immortalService.getOverview() } catch (cause) { error.value = getErrorMessage(cause) } }
async function commission(official) { if (busy.value || official.unlocked !== true) return; busy.value = true; error.value = ''; try { await immortalService.commission(official.key, `commission:${official.key}:${Date.now()}`); message.value = '仙官委托已完成，奖励由服务器结算。'; await load() } catch (cause) { error.value = getErrorMessage(cause) } finally { busy.value = false } }
onMounted(load)
</script>
<style scoped>.immortal-page { display: grid; gap: 24px; padding: 24px; }.official-card { padding: 24px; border: 1px solid var(--color-border); border-radius: 16px; background: var(--color-card); }</style>
