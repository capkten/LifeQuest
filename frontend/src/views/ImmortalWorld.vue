<template>
  <main class="immortal-page">
    <header><p>飞升之后</p><h1>仙界世界</h1><button type="button" @click="load">重试</button></header>
    <p v-if="error" role="alert">{{ error }}</p>
    <section v-else-if="overview" class="immortal-card">
      <h2>{{ overview.realm_key }} · 第 {{ overview.stage }} 阶</h2>
      <dl><div><dt>仙元</dt><dd>{{ overview.essence }}</dd></div><div><dt>仙石</dt><dd>{{ overview.immortal_stones }}</dd></div></dl>
      <p>区域、仙官与阶段目标由服务器返回。</p>
      <router-link to="/immortal/activities">查看仙界活动</router-link>
    </section>
    <p v-else>正在读取仙界状态...</p>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { immortalService } from '../services/immortal'
import { getErrorMessage } from '../utils/errorMessage'

const overview = ref(null)
const error = ref('')
async function load() { error.value = ''; try { overview.value = await immortalService.getOverview() } catch (cause) { error.value = getErrorMessage(cause) } }
onMounted(load)
</script>

<style scoped>
.immortal-page { display: grid; gap: 24px; padding: 24px; }.immortal-card { display: grid; gap: 16px; padding: 24px; border: 1px solid var(--color-border); border-radius: 16px; background: var(--color-card); } dl { display: flex; gap: 24px; } dt { color: var(--color-text-secondary); } dd { margin: 4px 0 0; font-size: 1.5rem; }
</style>
