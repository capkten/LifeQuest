<template>
  <section class="cave-page return-page" :class="{ 'return-page--encounter': result?.encounter_result }">
    <header><span class="return-label">归来</span><h1>{{ result ? '这一段，已收好' : pendingSettlement ? (pendingSettlement.status === 'blocked' ? '收功需要确认' : '等待联网收功') : '收好这一段时间' }}</h1></header>
    <template v-if="result">
      <div class="return-layout" :class="{ 'return-layout--with-encounter': result.encounter_result }"><div class="return-summary">
      <p class="return-narrative">{{ summary?.narrative || (result.status === 'aborted' ? '先到这里，也很好。未完的事，还在原处等你。' : '灯火未熄，山风正好。歇一会儿，再往前走。') }}</p>
      <div class="return-main"><output class="return-total metric-figure" aria-label="本次修为">+{{ totalReward.cultivation }}</output><span>修为</span></div>
      <p v-if="result.qi_gained !== null && result.qi_gained !== undefined" class="return-conversion">灵气 {{ conversion.qi }} → 修为 {{ conversion.cultivation }}</p><p v-else class="return-conversion">历史闭关，按当时规则结算。</p>
      <dl class="return-resources"><div><dt>灵石</dt><dd>+{{ totalReward.spirit_stones }}</dd></div><div><dt>功德</dt><dd>+{{ totalReward.merit }}</dd></div><div><dt>心境</dt><dd>{{ totalReward.mind_state_delta > 0 ? '+' : '' }}{{ totalReward.mind_state_delta }}</dd></div></dl>
      <p v-if="result.settlement_result?.daily_qi_cap_reached" class="cave-muted">今日灵气已满。这段安静的时间，依然算数。</p>
      <section v-if="result.settlement_result?.task_completed" class="return-task" aria-label="任务奖励"><h2>任务已完成</h2><p>{{ result.todo_title }}</p><p class="cave-muted">任务奖励已合在这次收获里，修为 +{{ result.settlement_result.task_reward?.cultivation || 0 }}，灵石 +{{ result.settlement_result.task_reward?.spirit_stones || 0 }}。</p></section>
      <p v-else-if="result.settlement_result?.task_previously_completed" class="cave-muted">任务此前已完成，这次只收好入定所得。</p>
      <p v-if="summary?.fortune_bonus?.applied" class="return-fortune">今日签「{{ summary.fortune_bonus.title }}」<span>今日首次收功，基础修为加成 10%：+{{ summary.fortune_bonus.bonus_cultivation }} 修为（向下取整）。</span></p>
      </div><div class="return-stories">
      <section v-if="result.encounter_result" class="return-encounter" aria-label="本次奇遇">
        <span class="encounter-rarity">{{ rarityLabels[result.encounter_result.rarity?.toLowerCase()] || '奇遇' }}</span>
        <h2>{{ result.encounter_result.title }}</h2><p>{{ result.encounter_result.story_text }}</p>
        <p class="encounter-reward">{{ result.encounter_result.reward_suppressed ? '故事已记下，本次没有额外资源。' : `奇遇所得：修为 +${summary?.encounter_reward?.cultivation || 0}，灵石 +${summary?.encounter_reward?.spirit_stones || 0}。` }}</p>
        <div v-if="summary?.first_codex_unlock" class="encounter-unlock"><span>首次点亮图鉴</span><button type="button" class="cave-link" @click="catalogOpen = true">翻开图鉴</button></div>
      </section>
      <p v-if="summary?.next_unlock" class="return-unlock">{{ summary.next_unlock.unlocked ? '已达到解锁条件' : '下一位同行者' }} · {{ summary.next_unlock.name }}<span>{{ summary.next_unlock.current }} / {{ summary.next_unlock.target }} 次成功入定</span></p>
      </div></div>
      <section v-if="onboarding?.status === 'completed' && onboarding.completed_session_id === result.id" class="return-onboarding" aria-label="白鹿的预告"><CavePet pet="white_deer" silhouette /><h2>山中，已有一位同行者在等你</h2><p>白鹿还在山中。第三次成功入定后，才能邀它随行。</p><router-link class="cave-link" to="/cave/growth">看看成长</router-link></section>
      <p v-if="onboardingPending" role="status">正在记下初到洞府的这一段…</p>
      <div v-if="onboardingError" role="alert"><p>{{ onboardingError }}</p><button v-if="canFinishOnboarding" type="button" class="cave-link" :disabled="Boolean(onboardingPending)" @click="cave.completeOnboarding(result.id)">重新确认引导</button></div>
      <button v-if="onboarding?.status === 'pending'" type="button" class="cave-link" :disabled="Boolean(onboardingPending)" @click="cave.skipOnboarding()">跳过引导</button>
      <p v-if="actionError" role="alert">{{ actionError }}</p>
      <button type="button" class="cave-button" :disabled="Boolean(pendingAction) || Boolean(onboardingPending)" @click="goHome">{{ pendingAction === 'acknowledge' ? '正在收好…' : '回洞府' }}</button>
    </template>
    <section v-else-if="pendingSettlement" class="return-pending" role="status"><p>这段时间已保存在此设备，联网后会自动确认。</p><p class="cave-muted">{{ pendingSettlement.session.todo_title || '静坐片刻' }}。修为与任务状态以服务端结算为准，这里不会预先发放奖励。</p><p v-if="pendingSettlement.error" :role="pendingSettlement.status === 'blocked' ? 'alert' : undefined">{{ pendingSettlement.error }}</p><button type="button" class="cave-button" :disabled="offline || Boolean(pendingAction)" @click="cave.retryPendingSettlements({ includeBlocked: true })">重新确认收功</button><router-link class="cave-link" to="/">先回洞府</router-link></section>
    <p v-else-if="!actionError && !loadError" role="status">正在收好这段时间…</p>
    <div v-if="!result && !pendingSettlement && (actionError || loadError)" role="alert"><p>{{ actionError || loadError }}</p><button type="button" class="cave-button" :disabled="Boolean(pendingAction)" @click="collect">重新收功</button></div>
    <EncounterCatalogDrawer v-model="catalogOpen" />
  </section>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EncounterCatalogDrawer from '../components/retreat/EncounterCatalogDrawer.vue'
import CavePet from '../components/cave/CavePet.vue'

const cave = inject('cave')
const feedback = inject('caveFeedback')
const route = useRoute()
const router = useRouter()
const catalogOpen = ref(false)
const rarityLabels = { common: '凡品', uncommon: '良品', rare: '稀有', epic: '史诗', legendary: '传说' }
const { settledSession, activeSession, actionError, loadError, pendingAction, pendingSettlements, offline, onboarding, onboardingPending, onboardingError } = cave
const pendingSettlement = computed(() => pendingSettlements.value.find(item => item.id === route.params.id))
const result = computed(() => settledSession.value?.id === route.params.id ? settledSession.value : null)
const canFinishOnboarding = computed(() => onboarding.value?.status === 'pending' && result.value?.status === 'completed' && result.value.target_duration === 15)
let attemptedOnboardingSession = null
watch([result, onboarding], async () => {
  if (!canFinishOnboarding.value || attemptedOnboardingSession === result.value.id) return
  attemptedOnboardingSession = result.value.id
  await cave.completeOnboarding(result.value.id)
}, { immediate: true })
const summary = computed(() => result.value?.return_summary)
const totalReward = computed(() => {
  if (summary.value?.total_reward) return summary.value.total_reward
  const rewards = [result.value?.settlement_result?.retreat_reward || { cultivation: result.value?.exp_gained || 0, spirit_stones: result.value?.coins_gained || 0 }, result.value?.settlement_result?.task_reward]
  return Object.fromEntries(['cultivation', 'spirit_stones', 'merit', 'mind_state_delta'].map(key => [key, rewards.reduce((total, reward) => total + (reward?.[key] || 0), 0)]))
})
const conversion = computed(() => summary.value?.base_conversion || { qi: result.value?.qi_gained ?? 0, cultivation: result.value?.exp_gained || 0 })
async function collect() {
  if (pendingSettlement.value) return
  const session = await cave.loadSession(route.params.id)
  if (!session || result.value || pendingSettlement.value) return
  if (activeSession.value?.id === route.params.id) {
    const settled = await cave.settleSession()
    if (settled?.status === 'completed') feedback.play('complete')
  }
}
async function goHome() {
  if (await cave.acknowledgeReturn(route.params.id)) router.push('/')
}
let viewedSessionId = null
watch(result, session => {
  if (session && viewedSessionId !== session.id) {
    viewedSessionId = session.id
    cave.recordReturnView(session.id)
    if (!onboarding.value && !offline.value) cave.load()
  }
}, { immediate: true })
watch(() => route.params.id, () => { if (!result.value) collect() }, { immediate: true })
</script>

<style scoped>
.return-onboarding { max-width: 30em; margin: 28px auto 12px; padding: 20px; background: #edf2ee; border-radius: 16px; }.return-onboarding > svg { width: 120px; }.return-onboarding h2 { font-family: SimSun, STSong, serif; font-size: 21px; font-weight: 500; }.return-onboarding p { font-size: 14px; line-height: 1.8; }
.return-pending { max-width: 32em; margin: 24px auto; line-height: 1.8; }.return-pending > .cave-link { display: block; margin-top: 16px; }
.return-page { max-width: 640px; margin: 32px auto 0; text-align: center; }.return-label { color: #397b67; font-family: SimSun, STSong, serif; font-size: 16px; letter-spacing: .2em; }.return-page h1 { font-family: SimSun, STSong, serif; font-size: 30px; line-height: 1.5; font-weight: 500; margin: 14px 0 20px; }.return-narrative { max-width: 30em; margin: 0 auto; font-size: 16px; line-height: 1.8; }.return-main { display: flex; justify-content: center; align-items: baseline; gap: 10px; margin-top: 24px; }.return-total { font-size: clamp(64px, 13vw, 96px); line-height: 1.25; font-weight: 500; font-variant-numeric: tabular-nums; letter-spacing: -.04em; }.return-main > span { font-size: 16px; }.return-conversion { margin: 10px 0 24px; font-size: 14px; color: #536d62; }.return-resources { display: flex; justify-content: center; gap: 40px; margin: 0 0 28px; }.return-resources div { display: grid; gap: 8px; }.return-resources dt { font-size: 12px; color: #536d62; }.return-resources dd { margin: 0; font-size: 18px; font-variant-numeric: tabular-nums; }.return-task { text-align: left; padding: 20px; background: #edf2ee; border-radius: 12px; margin: 24px 0; }.return-task h2 { margin: 0; font-size: 16px; font-weight: 500; }.return-task p { margin: 8px 0 0; }.return-fortune { font-size: 14px; color: #78531c; margin: 24px 0; }.return-fortune span, .return-unlock span { display: block; font-size: 12px; margin-top: 6px; }.return-encounter { position: relative; text-align: left; background: #edf2ee; border-radius: 4px 20px 20px 20px; padding: 24px; margin: 28px 0; }.encounter-rarity { color: #78531c; font-size: 12px; }.return-encounter h2 { font-family: SimSun, STSong, serif; font-size: 24px; font-weight: 500; line-height: 1.5; margin: 10px 0 12px; }.return-encounter > p { font-size: 14px; line-height: 1.8; margin: 0; }.return-encounter .encounter-reward { color: #397b67; margin-top: 18px; }.encounter-unlock { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 14px; color: #536d62; font-size: 12px; }
.return-unlock { color: #536d62; font-size: 14px; margin: 28px 0; }.return-page > .cave-button { min-width: 180px; margin-top: 16px; }@media(min-width:1000px) { .return-page--encounter { max-width: 980px; }.return-layout--with-encounter { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 40px; align-items: start; margin-top: 32px; }.return-layout--with-encounter .return-encounter { margin-top: 0; }.return-layout--with-encounter .return-narrative { text-align: left; }.return-layout--with-encounter .return-main { margin-top: 24px; }.return-layout--with-encounter .return-unlock { margin-bottom: 12px; } }
@media(max-width:767px) { .return-page { margin-top: 12px; }.return-page h1 { font-size: 26px; }.return-narrative { font-size: 14px; }.return-resources { gap: 36px; } }
</style>
