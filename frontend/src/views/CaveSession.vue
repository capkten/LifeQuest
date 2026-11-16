<template>
  <section class="cave-page session-page">
    <header class="session-heading"><span>入定</span><button type="button" class="cave-link" @click="router.push('/')">最小化，继续浏览</button></header>
    <p v-if="loading && !session" role="status">正在找回这一段安静的时间…</p>
    <template v-if="session">
      <CaveScene :mode="mode" :companion="session.companion_snapshot?.key || ''" focusing />
      <p v-if="session.companion_snapshot" class="cave-muted">正在随行：{{ session.companion_snapshot.name }}</p>
      <div class="session-clock"><span class="cave-muted">剩余时间</span><div class="session-timer metric-figure" role="timer" aria-live="off" aria-label="剩余时间">{{ remainingText }}</div></div>
      <h1>{{ session.todo_title || '静坐片刻' }}</h1>
      <p class="cave-muted">小满替你守着灯。离开页面，时间也会继续。</p>
      <p v-if="onboarding?.status === 'pending'" class="cave-muted">这一段，从 15 分钟开始。首次成功收功，会把一段凡品见闻记入图鉴。<button type="button" class="cave-link" :disabled="Boolean(onboardingPending) || offline" @click="cave.skipOnboarding()">跳过引导</button></p>
      <p v-if="onboarding?.status === 'pending'" class="cave-muted">成功收功后，就完成初到洞府的引导。</p>
      <p v-if="onboardingError" role="alert">{{ onboardingError }}</p>
      <p class="session-status" role="status">{{ canComplete ? '这一段已过八成，可以收功，也可以再坐一会儿。' : '慢慢来，满八成后就可以收功。' }}</p>
      <div class="session-actions"><button type="button" class="cave-button" :disabled="!canComplete || Boolean(pendingAction)" @click="finish()">{{ pendingAction === 'settle' ? '正在收功…' : '收功' }}</button><button type="button" class="cave-link" :disabled="Boolean(pendingAction)" @click="earlyOpen = true">提前结束</button></div>
    </template>
    <div v-if="loadError || actionError" role="alert"><p>{{ loadError || actionError }}</p><button type="button" class="cave-link" @click="cave.loadSession(route.params.id)">重试</button></div>
    <el-dialog v-model="earlyOpen" title="这次先到这里" width="min(440px, calc(100vw - 32px))" align-center>
      <div class="cave-page"><p>已经走过的时间，会替你收好。</p><p class="cave-muted">按已过整分钟积累灵气，以 0.25 转为修为；绑定的任务会继续留着。</p></div>
      <template #footer><button type="button" class="cave-link" @click="earlyOpen = false">再坐一会儿</button><button type="button" class="cave-button" :disabled="Boolean(pendingAction)" @click="finish(true)">结束并收好这段时间</button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CaveScene from '../components/cave/CaveScene.vue'

const cave = inject('cave')
const feedback = inject('caveFeedback')
const route = useRoute()
const router = useRouter()
const { activeSession, settledSession, remainingSeconds, canComplete, pendingAction, loading, loadError, actionError, mode, onboarding, onboardingPending, onboardingError, offline } = cave
const session = computed(() => activeSession.value?.id === route.params.id ? activeSession.value : null)
const remainingText = computed(() => `${String(Math.floor(remainingSeconds.value / 60)).padStart(2, '0')}:${String(remainingSeconds.value % 60).padStart(2, '0')}`)
const earlyOpen = ref(false)
watch(() => route.params.id, id => { if (id) cave.loadSession(id) }, { immediate: true })
watch(settledSession, result => { if (result?.id === route.params.id) router.replace(`/cave/return/${result.id}`) })
async function finish(early = false) {
  await feedback.unlockFromGesture()
  const result = await cave.settleSession({ early })
  if (result) {
    earlyOpen.value = false
    if (result.status !== 'pending_settlement') feedback.play(early ? 'end' : 'complete')
    router.replace(`/cave/return/${result.id}`)
  }
}
</script>

<style scoped>
.session-page { max-width: 720px; margin: 0 auto; text-align: center; }.session-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; font-family: SimSun, STSong, serif; font-size: 24px; }.session-heading button { font-family: inherit; font-size: 14px; }.session-page :deep(.cave-scene) { max-width: 540px; margin: 0 auto; height: 240px; }.session-clock { margin-top: 24px; }.session-timer { font-size: clamp(64px, 12vw, 88px); line-height: 1.2; font-variant-numeric: tabular-nums; font-weight: 500; letter-spacing: -.04em; }.session-page h1 { font-family: SimSun, STSong, serif; font-size: 26px; line-height: 1.5; margin: 16px 0 12px; overflow-wrap: anywhere; }.session-status { min-height: 24px; font-size: 14px; color: #536d62; }.session-actions { display: flex; align-items: center; justify-content: center; gap: 24px; margin-top: 24px; }.session-actions .cave-button { min-width: 160px; }@media(max-width: 767px) { .session-page :deep(.cave-scene) { height: 180px; }.session-clock { margin-top: 16px; }.session-page h1 { font-size: 23px; }.session-actions { margin-top: 16px; } }
</style>
