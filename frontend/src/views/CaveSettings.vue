<template>
  <section class="cave-page cave-settings">
    <h1>洞府设置</h1>
    <p class="cave-muted">把这一小处，调成你喜欢的样子。</p>
    <label><span>入定声音<small>开始、结束与收功时，一声轻响。</small></span><input type="checkbox" :checked="soundEnabled" @change="changeSound" /></label>
    <label><span>完成时轻触感<small>支持的移动设备会轻轻振动一次。</small></span><input type="checkbox" :checked="hapticsEnabled" @change="feedback.setHapticsEnabled($event.target.checked)" /></label>
    <section class="notification-settings" aria-label="入定通知"><h2>入定提醒</h2><p v-if="!notifications.isSupported" class="cave-muted">网页只保留应用内提醒，不请求系统通知。</p><template v-else><label><span>入定通知<small>{{ notifications.platform === 'android' ? '通知栏保留倒计时，结束时提醒你回来。' : '应用运行时发出结束提醒；关闭后不承诺提醒。' }}</small></span><input type="checkbox" :checked="notificationEnabled" @change="changeNotifications" /></label><p class="cave-muted">{{ permission === 'granted' ? '系统已允许通知，仍可能受到省电策略影响。' : permission === 'denied' ? '系统未允许通知，计时与应用内提醒照常。' : '开始入定或点击下方按钮时，才会请求系统允许。' }}</p><button v-if="notificationEnabled && permission !== 'granted'" type="button" class="cave-link" @click="notifications.requestFromGesture()">允许系统通知</button></template></section>
    <section class="notification-settings" aria-label="首次引导"><h2>初到洞府</h2><p class="cave-muted">再听小满说说签、入定与山中的同行者。</p><button type="button" class="cave-link" @click="replayOpen = true">重看首次引导</button></section>
    <el-dialog v-model="replayOpen" title="小满的引导" width="min(560px, calc(100vw - 32px))" align-center><div class="cave-page onboarding-replay"><p>我是小满，替你照看这一小处。</p><p>最近最想推进的一件事？写下来，就会成为今天的任务。洞府会从未完成的事里取三签，你可以换签，也能从签筒里自己选。</p><p>落座后，从 15 分钟开始。完成八成可以收功；提前结束也会收好已过的时间。首次成功收功会遇见一段凡品奇遇，记入图鉴。</p><CavePet pet="white_deer" silhouette /><p>白鹿会在第三次成功入定后与你相逢，不会因重看引导提前解锁。</p><p class="cave-muted">重看只温习说明，不创建任务，也不重置奖励。</p></div><template #footer><button type="button" class="cave-button" @click="replayOpen = false">记下了</button></template></el-dialog>
    <router-link class="cave-link" to="/profile">个人资料与账号</router-link>
  </section>
</template>

<script setup>
import { inject, ref } from 'vue'
import CavePet from '../components/cave/CavePet.vue'
const replayOpen = ref(false)
const feedback = inject('caveFeedback')
const notifications = inject('caveNotifications')
const { soundEnabled, hapticsEnabled } = feedback
const { enabled: notificationEnabled, permission } = notifications
async function changeNotifications(event) {
  await notifications.setEnabled(event.target.checked)
  if (event.target.checked) await notifications.requestFromGesture()
}
async function changeSound(event) {
  feedback.setSoundEnabled(event.target.checked)
  if (event.target.checked) {
    await feedback.unlockFromGesture()
    feedback.play('start')
  }
}
</script>

<style scoped>
.onboarding-replay { line-height: 1.9; }.onboarding-replay > svg { width: 120px; display: block; margin: 20px auto; }
.cave-settings { max-width: 640px; margin: 16px auto; }.cave-settings h1 { font-family: SimSun, STSong, serif; font-size: 30px; }.cave-settings label { display: flex; justify-content: space-between; align-items: center; gap: 24px; min-height: 88px; padding: 16px 0; font-size: 16px; }.cave-settings small { display: block; color: #536d62; font-size: 14px; line-height: 1.6; margin-top: 6px; }.cave-settings input { width: 22px; height: 22px; accent-color: #397b67; flex-shrink: 0; }.cave-settings .cave-link { display: inline-flex; margin-top: 24px; }.notification-settings { margin-top: 24px; }.notification-settings h2 { font-family: SimSun, STSong, serif; font-size: 23px; font-weight: 500; margin-bottom: 16px; }
</style>
