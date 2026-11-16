<template>
  <section class="cave-page letters-page">
    <header class="letters-heading"><div><h1>同门书信</h1><p class="cave-muted">有人记得，你在山中走过的路。</p></div><router-link to="/cave/growth" class="cave-link">成长</router-link></header>
    <template v-if="route.params.id">
      <router-link to="/cave/letters" class="cave-link">全部书信</router-link>
      <p v-if="letterLoading" role="status">正在拆开这封信…</p>
      <div v-if="letterError" role="alert"><p>{{ letterError }}</p><button type="button" class="cave-link" @click="openLetter(route.params.id)">重试</button></div>
      <article v-if="letter?.id === route.params.id" class="opened-letter">
        <p class="letter-date">{{ dateText(letter.delivered_at) }} · {{ letter.senior_name }}</p><h2>{{ letter.title }}</h2><p class="letter-body">{{ letter.body }}</p>
        <section class="letter-trial" aria-label="本周试炼"><h3>{{ letter.trial.title }}</h3><p>{{ letter.trial.description }}</p><p class="cave-muted">{{ letter.trial.current }} / {{ letter.trial.target }}</p><p class="cave-muted">读信不代表接受试炼，暂不也没有惩罚。</p><div class="trial-actions" v-if="letter.trial.status === 'available'"><button type="button" class="cave-button" :disabled="!letter.trial.can_accept || Boolean(letterPending)" @click="cave.acceptLetter(letter.id)">{{ letterPending?.action === 'accept' ? '正在接受…' : '接受试炼' }}</button><button type="button" class="cave-link" :disabled="Boolean(letterPending)" @click="cave.declineLetter(letter.id)">{{ letterPending?.action === 'decline' ? '正在收好…' : '暂不' }}</button></div><template v-else><p class="trial-state">{{ trialStateText }}</p><button v-if="letter.trial.status === 'ready'" type="button" class="cave-button" :disabled="Boolean(letterPending)" @click="cave.claimLetter(letter.id)">{{ letterPending?.action === 'claim' ? '正在收取…' : '领取见闻' }}</button></template></section>
        <section v-if="letter.trial.status === 'completed' && letter.trial.reward" class="trial-story" aria-label="试炼见闻"><span class="cave-muted">已记入图鉴</span><h3>{{ letter.trial.reward.name }}</h3><p>{{ letter.trial.reward.story }}</p><router-link to="/cave/codex" class="cave-link">翻开图鉴</router-link></section>
      </article>
    </template>
    <template v-else>
      <p v-if="lettersLoading && !letters" role="status">正在取来案上的信…</p>
      <div v-if="lettersError" role="alert"><p>{{ lettersError }}</p><button type="button" class="cave-link" @click="cave.loadLetters()">重试</button></div>
      <div v-if="letters && !letters.letters.length" class="letters-empty"><span class="letter-envelope" aria-hidden="true">书</span><h2>还没有来信</h2><p>来山中的第七天，青蘅会捎来第一封信；第十四天，砺锋也会写来。</p><p class="cave-muted">以后每周一早上八点，案上会有新的问候。试炼可以接受，也可以暂不，没有惩罚。</p></div>
      <div v-else-if="letters" class="letters-list"><article v-for="item in letters.letters" :key="item.id"><span class="letter-envelope" aria-hidden="true">{{ item.senior_key === 'qingheng' ? '蘅' : '锋' }}</span><div><span class="letter-date">{{ dateText(item.delivered_at) }}<span v-if="item.status === 'unread'" class="letter-unread">未拆</span></span><h2><router-link :to="`/cave/letters/${item.id}`">{{ item.title }}</router-link></h2><p class="cave-muted">{{ item.senior_name }}</p></div></article></div>
    </template>
  </section>
</template>

<script setup>
import { computed, inject, watch } from 'vue'
import { useRoute } from 'vue-router'
const cave = inject('cave')
const route = useRoute()
const { letters, lettersLoading, lettersError, letter, letterLoading, letterError, letterPending } = cave
const trialStateText = computed(() => ({ accepted: '本周试炼已接下，完成后回来收功。', ready: '试炼已完成，可以领取这份见闻。', declined: '这次先放在案上，下周会有新的试炼。', completed: '这份见闻已经收好。' }[letter.value?.trial?.status] || '这封信已收好。'))
function dateText(value) {
  return new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: 'numeric', day: 'numeric' }).format(new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`))
}
async function openLetter(id) {
  const result = await cave.loadLetter(id)
  if (result?.status === 'unread' && route.params.id === id) await cave.readLetter(id)
}
watch(() => route.params.id, id => { if (id) openLetter(id); else cave.loadLetters() }, { immediate: true })
</script>

<style scoped>
.letters-page { max-width: 860px; margin: 0 auto; }.letters-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; }.letters-heading h1 { font-family: SimSun, STSong, serif; font-size: 30px; letter-spacing: .08em; margin: 0; }.letters-heading p { margin: 10px 0 0; }.letters-empty { max-width: 560px; margin: 48px auto; text-align: center; }.letter-envelope { display: inline-flex; justify-content: center; align-items: center; width: 96px; height: 72px; background: #e6eee5; color: #789484; border-radius: 4px 4px 20px 4px; font-family: SimSun, STSong, serif; font-size: 32px; }.letters-empty h2 { font-family: SimSun, STSong, serif; font-size: 26px; font-weight: 500; margin: 28px 0 20px; }.letters-empty p { font-size: 14px; line-height: 1.9; }.letters-empty .cave-muted { margin-top: 24px; }.letters-list { display: grid; gap: 16px; }.letters-list article { display: flex; gap: 24px; align-items: center; background: #edf2ee; border-radius: 4px 20px 20px 4px; padding: 24px; }.letters-list .letter-envelope { flex-shrink: 0; width: 64px; height: 80px; }.letters-list h2 { font-family: SimSun, STSong, serif; font-size: 22px; line-height: 1.6; font-weight: 500; margin: 10px 0; }.letters-list h2 a { color: #24443d; text-decoration: none; }.letters-list h2 a:hover { text-decoration: underline; text-underline-offset: 4px; }.letter-date { color: #536d62; font-size: 12px; }.letter-unread { margin-left: 16px; color: #397b67; }.opened-letter { padding: 24px 0; max-width: 680px; margin: 0 auto; }.opened-letter > h2 { font-family: SimSun, STSong, serif; font-size: 28px; line-height: 1.6; font-weight: 500; margin: 20px 0 32px; }.opened-letter .letter-body { white-space: pre-line; font-family: SimSun, STSong, serif; font-size: 19px; line-height: 2; overflow-wrap: anywhere; }.letter-trial { padding: 24px; margin-top: 40px; background: #edf2ee; border-radius: 20px 20px 20px 4px; }.letter-trial h3 { font-family: SimSun, STSong, serif; font-size: 22px; line-height: 1.6; font-weight: 500; margin: 0 0 16px; }.letter-trial p { font-size: 14px; }.trial-actions { display: flex; align-items: center; gap: 16px; margin-top: 20px; }.trial-actions .cave-button { min-width: 132px; }.trial-state { color: #397b67; }.trial-story { margin-top: 32px; padding: 0 4px; }.trial-story h3 { font-family: SimSun, STSong, serif; font-size: 25px; font-weight: 500; margin: 16px 0; }.trial-story p { font-size: 16px; line-height: 1.9; }.trial-story .cave-link { padding-left: 0; }.letters-list article > div { min-width: 0; }@media(max-width:390px) { .letters-list article { padding: 20px; gap: 16px; }.letters-list .letter-envelope { width: 40px; height: 64px; font-size: 26px; }.letters-list h2 { font-size: 20px; }.opened-letter > h2 { font-size: 25px; }.letter-trial { padding: 20px; } }@media(min-width:1000px) { .letters-empty { margin-top: 88px; } }
</style>
