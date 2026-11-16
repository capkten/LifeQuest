<template>
  <section class="cave-page codex-page">
    <header class="codex-heading"><div><h1>图鉴</h1><p class="cave-muted">曾经相逢，都在这里。</p></div><nav aria-label="成长导航"><router-link to="/cave/growth" class="cave-link">成长</router-link><router-link to="/cave/companions" class="cave-link">伙伴</router-link></nav></header>
    <p v-if="codexLoading && !codex" role="status">正在展开放在山中的册页…</p>
    <div v-if="codexError" role="alert"><p>{{ codexError }}</p><button type="button" class="cave-link" @click="cave.loadCodex()">重试</button></div>
    <template v-if="codex">
      <div class="codex-categories" role="group" aria-label="图鉴分类"><button v-for="category in codex.categories" :key="category.key" type="button" class="cave-choice" :aria-pressed="selectedCategory === category.key" @click="selectedCategory = category.key">{{ category.name }} <span>{{ category.unlocked }} / {{ category.total }}</span></button></div>
      <p v-if="!currentCategory?.entries.length" class="codex-empty">这一页，还在等一段新的故事。</p>
      <div v-else class="codex-entries">
        <article v-for="entry in currentCategory.entries" :key="entry.key" class="codex-entry" :class="{ 'codex-entry--locked': !entry.unlocked }">
          <CavePet v-if="selectedCategory === 'pets'" :pet="entry.key" :silhouette="!entry.unlocked" /><span v-else-if="!entry.unlocked" class="codex-silhouette" aria-hidden="true">❧</span>
          <div><span class="codex-rarity">{{ entry.unlocked ? rarityLabels[entry.rarity?.toLowerCase()] || entry.rarity || '相逢' : '未解锁' }}</span><h2>{{ entry.unlocked ? entry.name : '尚未相逢' }}</h2><p>{{ entry.unlocked ? entry.story : entry.hint }}</p><p v-if="entry.unlocked" class="codex-date">{{ entry.first_unlocked_at ? `${dateText(entry.first_unlocked_at)} 初次相逢` : '已记入册页' }} · 结缘 {{ entry.unlock_count }} 次</p></div>
        </article>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import CavePet from '../components/cave/CavePet.vue'
const cave = inject('cave')
const { codex, codexLoading, codexError } = cave
const selectedCategory = ref('encounters')
const currentCategory = computed(() => codex.value?.categories.find(category => category.key === selectedCategory.value))
const rarityLabels = { common: '凡品', uncommon: '良品', rare: '稀有', epic: '史诗', legendary: '传说' }
function dateText(value) {
  return new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: 'numeric', day: 'numeric' }).format(new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`))
}
onMounted(() => cave.loadCodex())
</script>

<style scoped>
.codex-page { max-width: 1000px; margin: 0 auto; }.codex-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 24px; }.codex-heading h1 { font-family: SimSun, STSong, serif; font-size: 30px; letter-spacing: .08em; margin: 0; }.codex-heading p { margin: 10px 0 0; }.codex-heading nav { display: flex; gap: 8px; }.codex-categories { display: flex; gap: 8px; overflow-x: auto; padding: 4px 4px 12px; margin: -4px -4px 16px; }.codex-categories button { flex-shrink: 0; padding: 10px 16px; }.codex-categories span { display: block; font-size: 12px; margin-top: 6px; opacity: .8; }.codex-entries { display: grid; gap: 16px; }.codex-entry { display: flex; align-items: flex-start; gap: 20px; padding: 24px; background: #edf2ee; border-radius: 12px; min-width: 0; }.codex-entry > div { min-width: 0; }.codex-entry :deep(.cave-pet) { flex-shrink: 0; width: 90px; height: 75px; }.codex-entry h2 { font-family: SimSun, STSong, serif; font-size: 23px; font-weight: 500; margin: 8px 0 12px; line-height: 1.5; }.codex-entry p { font-size: 14px; line-height: 1.8; margin: 0; overflow-wrap: anywhere; }.codex-rarity { font-size: 12px; color: #78531c; }.codex-entry .codex-date { font-size: 12px; margin-top: 16px; color: #536d62; }.codex-entry--locked { background: #f0f4f0; }.codex-entry--locked h2,.codex-entry--locked .codex-rarity { color: #536d62; }.codex-silhouette { color: #a6b7a7; font-size: 48px; line-height: 1; flex-shrink: 0; }.codex-empty { padding: 48px 16px; text-align: center; color: #536d62; font-size: 14px; }@media(min-width:1000px) { .codex-categories { gap: 12px; }.codex-categories button { min-width: 120px; }.codex-entries { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; } }@media(max-width:390px) { .codex-entry { padding: 20px; gap: 12px; }.codex-entry :deep(.cave-pet) { width: 64px; height: 54px; }.codex-heading { gap: 8px; }.codex-heading nav { gap: 0; } }
</style>
