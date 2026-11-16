<template>
  <section class="cave-page growth-page">
    <header class="growth-heading"><div><h1>成长</h1><p class="cave-muted">日有所进，不必急着抵达。</p></div><router-link to="/" class="cave-link">回洞府</router-link></header>
    <p v-if="growthLoading && !growth" role="status">正在翻开山中的记录…</p>
    <div v-if="growthError" role="alert"><p>{{ growthError }}</p><button type="button" class="cave-link" @click="cave.loadGrowth()">重试</button></div>
    <template v-if="growth">
      <div class="growth-overview">
        <article class="growth-realm" aria-label="境界进度"><span class="cave-muted">当前境界</span><h2>{{ growth.realm.realm_label || growth.realm.realm_key }} <span>{{ growth.realm.minor_stage }} 重</span></h2><p class="realm-cultivation metric-figure">{{ growth.realm.cultivation }} <span>修为</span></p><div class="realm-progress" role="progressbar" aria-label="境界进度" :aria-valuenow="realmPercent" aria-valuemin="0" aria-valuemax="100"><span :style="{ width: `${realmPercent}%` }"></span></div><p class="cave-muted">{{ realmPercent }}% · {{ growth.successful_sessions }} 次成功入定</p><router-link to="/cultivation" class="cave-link">查看修炼详情</router-link></article>
        <article v-if="growth.next_unlock" class="growth-next"><CavePet :pet="growth.next_unlock.key" silhouette /><div><span class="cave-muted">下一位同行者</span><h2>{{ growth.next_unlock.name }}</h2><p>{{ growth.next_unlock.current }} / {{ growth.next_unlock.target }} 次成功入定</p><p class="cave-muted">多坐一段时间，就离相逢近一些。</p></div></article>
        <article v-else class="growth-next growth-next--complete"><span class="next-leaf" aria-hidden="true">❧</span><div><h2>一路有同行</h2><p class="cave-muted">已经相逢的伙伴，在这里等你。</p></div></article>
      </div>
      <div class="growth-features"><router-link to="/cave/codex" aria-label="图鉴" class="growth-feature"><h2>图鉴 <span aria-hidden="true">›</span></h2><p class="cave-muted">把曾经相逢的故事，留在册页里。</p><dl><div v-for="category in growth.codex_counts" :key="category.key"><dt>{{ category.name }}</dt><dd>{{ category.unlocked }} / {{ category.total }}</dd></div></dl></router-link><router-link to="/cave/companions" aria-label="伙伴" class="growth-feature"><h2>伙伴 <span aria-hidden="true">›</span></h2><p class="cave-muted">小满守着灯，同行者也会慢慢到来。</p><p class="growth-active-pet">{{ activeCompanion ? `正在随行：${activeCompanion.name}` : '先从和小满相伴开始。' }}</p></router-link></div>
      <router-link to="/cave/letters" class="growth-letters" aria-label="同门书信"><span>同门书信</span><span>山中来信，慢慢读 <span aria-hidden="true">›</span></span></router-link>
      <nav class="growth-entries" aria-label="修行与生活入口"><router-link v-for="entry in entries" :key="entry.to" :to="entry.to">{{ entry.name }}<span aria-hidden="true">›</span></router-link></nav>
    </template>
  </section>
</template>

<script setup>
import { computed, inject, onMounted } from 'vue'
import CavePet from '../components/cave/CavePet.vue'

const cave = inject('cave')
const { growth, growthLoading, growthError } = cave
const activeCompanion = computed(() => growth.value?.companions?.pets.find(pet => pet.active))
const realmPercent = computed(() => {
  const realm = growth.value?.realm
  const stage = realm?.next_stage
  if (!stage || stage.next_threshold == null) return 0
  const start = Number(stage.current_threshold || 0)
  const end = Number(stage.next_threshold)
  return end <= start ? 100 : Math.min(100, Math.max(0, Math.round(((Number(realm.cultivation || 0) - start) / (end - start)) * 100)))
})
const entries = [{ name: '宗门', to: '/sects' }, { name: '功法', to: '/techniques' }, { name: '凡界', to: '/world' }, { name: '仙界', to: '/immortal/world' }, { name: '商城', to: '/shop' }, { name: '背包', to: '/backpack' }]
onMounted(() => cave.loadGrowth())
</script>

<style scoped>
.growth-page { max-width: 1000px; margin: 0 auto; }.growth-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; }.growth-heading h1 { font-family: SimSun, STSong, serif; font-size: 30px; letter-spacing: .08em; margin: 0; }.growth-heading p { margin: 10px 0 0; }.growth-overview { display: grid; gap: 20px; }.growth-realm { padding: 24px; background: #edf2ee; border-radius: 18px 18px 18px 4px; }.growth-realm h2 { font-family: SimSun, STSong, serif; font-size: 32px; font-weight: 500; margin: 16px 0; }.growth-realm h2 span { font-size: 18px; }.realm-cultivation { font-size: 28px; font-variant-numeric: tabular-nums; margin: 16px 0; }.realm-cultivation span { font-size: 14px; }.realm-progress { height: 6px; border-radius: 4px; background: #d6e3d8; overflow: hidden; }.realm-progress span { display: block; height: 100%; background: #397b67; border-radius: inherit; }.growth-realm .cave-link { padding-left: 0; }.growth-next { display: flex; gap: 20px; align-items: center; padding: 12px 8px; }.growth-next h2 { font-family: SimSun, STSong, serif; font-size: 24px; line-height: 1.5; margin: 10px 0; font-weight: 500; }.growth-next > :first-child { flex-shrink: 0; }.growth-next p { font-size: 14px; }.next-leaf { font-size: 72px; color: #87aa99; }.growth-features { display: grid; gap: 16px; margin: 24px 0; }.growth-feature { display: block; padding: 24px; color: inherit; background: #f0f5f0; border-radius: 12px; text-decoration: none; }.growth-feature h2 { display: flex; justify-content: space-between; align-items: baseline; font-family: SimSun, STSong, serif; font-size: 24px; font-weight: 500; margin: 0 0 12px; }.growth-feature h2 span { color: #397b67; }.growth-feature dl { display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0 0; }.growth-feature dl div { display: grid; gap: 6px; }.growth-feature dt { font-size: 12px; color: #536d62; }.growth-feature dd { margin: 0; font-size: 14px; }.growth-active-pet { font-size: 14px; margin-top: 24px; color: #397b67; }.growth-letters { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 60px; padding: 12px 4px; margin-bottom: 16px; color: #397b67; text-decoration: none; font-size: 16px; }.growth-letters > span:last-child { color: #536d62; font-size: 14px; }.growth-entries { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }.growth-entries a { display: flex; justify-content: space-between; align-items: center; min-height: 52px; padding: 12px 16px; color: #536d62; font-size: 14px; text-decoration: none; border-radius: 8px; background: #edf2ee; }@media(min-width:1000px) { .growth-overview { grid-template-columns: 1fr 1fr; gap: 40px; }.growth-realm { padding: 32px; }.growth-next { justify-content: center; }.growth-features { grid-template-columns: 1fr 1fr; gap: 24px; }.growth-entries { grid-template-columns: repeat(3, minmax(0, 1fr)); } }@media(max-width:390px) { .growth-next { gap: 12px; }.growth-next :deep(.cave-pet) { width: 90px; height: 75px; } }
</style>
