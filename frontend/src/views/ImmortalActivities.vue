<template>
  <main class="immortal-page"><header><p>仙界循环</p><h1>仙界活动</h1></header><p v-if="error" role="alert">{{ error }}</p><button type="button" :disabled="running" @click="run">执行一次仙界修行</button><p v-if="message" role="status">{{ message }}</p></main>
</template>
<script setup>
import { ref } from 'vue'
import { immortalService } from '../services/immortal'
import { getErrorMessage } from '../utils/errorMessage'
const running = ref(false), error = ref(''), message = ref('')
async function run() { if (running.value) return; running.value = true; error.value = ''; try { await immortalService.runActivity('daily-cultivation', `activity:${Date.now()}`); message.value = '活动已记录，奖励由服务器结算。' } catch (cause) { error.value = getErrorMessage(cause) } finally { running.value = false } }
</script>
<style scoped>.immortal-page { display: grid; gap: 24px; padding: 24px; }</style>
