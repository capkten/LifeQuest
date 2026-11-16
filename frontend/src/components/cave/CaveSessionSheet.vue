<template>
  <el-drawer v-model="preparingSession" title="落座入定" direction="btt" size="auto" class="cave-session-drawer">
    <div class="session-draft cave-page">
      <p class="cave-muted">只照看这一段时间，别的事先放一放。</p>
      <section v-if="firstAndroidStart" class="session-notice" aria-label="首次入定提醒"><p>{{ soundEnabled ? 'Android 默认会有一声轻响，也可以安静开始。' : '入定声音已关闭，安静开始也很好。' }}</p><button v-if="soundEnabled" type="button" class="cave-link" @click="feedback.setSoundEnabled(false)">关闭入定声音</button><p>通知需由你允许；不允许也不会影响入定。结束提醒可能受到系统省电策略影响。</p></section>
      <div class="duration-options" role="group" aria-label="入定时长">
        <button v-for="duration in [15, 25, 45, 60, 90]" :key="duration" type="button" class="cave-choice" :aria-pressed="selectedDuration === duration" :disabled="Boolean(pendingAction)" @click="selectedDuration = duration">{{ duration }} 分钟</button>
      </div>
      <label for="session-task">这一段时间，做什么</label>
      <select id="session-task" v-model="taskId" :disabled="Boolean(pendingAction)">
        <option value="">不绑定任务，静坐片刻</option>
        <option v-for="task in taskOptions" :key="task.id" :value="task.id">{{ task.title }}</option>
      </select>
      <p v-if="candidatesLoading" class="cave-muted" role="status">正在取来未完成的事…</p>
      <p v-if="candidatesError" role="alert">{{ candidatesError }} <button type="button" class="cave-link" @click="cave.loadCandidates()">重试</button></p>
      <label class="cave-check"><input v-model="markTodoComplete" type="checkbox" :disabled="!sessionTask || Boolean(pendingAction)" />完成后同时完成任务</label>
      <p class="cave-muted">最多积累 {{ selectedDuration }} 灵气。完成八成即可收功；提前结束也会收好已过的时间。</p>
      <p v-if="actionError" role="alert">{{ actionError }}</p>
      <p v-if="loadError" role="alert">{{ loadError }} <button type="button" class="cave-link" @click="cave.load()">重新连接</button></p>
      <button type="button" class="cave-button" :disabled="starting || Boolean(pendingAction) || !data || offline" @click="start">{{ starting || pendingAction === 'start' ? '正在落座…' : '开始入定' }}</button>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const cave = inject('cave')
const feedback = inject('caveFeedback')
const notifications = inject('caveNotifications')
const { soundEnabled } = feedback
const firstAndroidStart = ref(notifications.platform === 'android' && localStorage.getItem('cave:android-start-notice') !== '1')
const starting = ref(false)
const router = useRouter()
const { data, loadError, preparingSession, sessionTask, markTodoComplete, selectedDuration, pendingAction, actionError, candidates, candidatesLoading, candidatesError, offline } = cave
const taskOptions = computed(() => [...new Map([...(sessionTask.value ? [sessionTask.value] : []), ...candidates.value].map(task => [task.id, task])).values()])
const taskId = computed({ get: () => sessionTask.value?.id || '', set: id => { sessionTask.value = taskOptions.value.find(task => task.id === id) || null } })
watch(preparingSession, open => { if (open) cave.loadCandidates() })
async function start() {
  if (starting.value || pendingAction.value) return
  starting.value = true
  try {
    await feedback.unlockFromGesture()
    if (notifications.isSupported && notifications.enabled.value) await notifications.requestFromGesture()
    const session = await cave.startSession()
    if (session) {
      if (firstAndroidStart.value) {
        try { localStorage.setItem('cave:android-start-notice', '1') } catch {}
        firstAndroidStart.value = false
      }
      preparingSession.value = false
      feedback.play('start')
      router.push(`/cave/session/${session.id}`)
    }
  } finally {
    starting.value = false
  }
}
</script>

<style scoped>
.session-draft { display: grid; gap: 16px; max-width: 620px; margin: 0 auto; padding-bottom: env(safe-area-inset-bottom, 0px); }.session-draft > p { margin: 0; }.session-draft > label { font-size: 16px; }.duration-options { display: flex; flex-wrap: wrap; gap: 8px; }.duration-options button { flex: 1; min-width: 88px; }.session-draft select { width: 100%; min-height: 48px; font-family: inherit; font-size: 16px; padding: 10px; border: 1px solid #bdcfc2; border-radius: 8px; color: #24443d; background: #f7faf8; }.cave-check { display: flex; gap: 10px; align-items: center; min-height: 48px; }.cave-check input { width: 20px; height: 20px; accent-color: #397b67; }.session-notice { padding: 16px; background: #edf2ee; border-radius: 12px; }.session-notice p { font-size: 14px; line-height: 1.7; margin: 0; }.session-notice .cave-link { padding-left: 0; }
</style>
