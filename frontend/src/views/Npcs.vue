<template>
  <div class="npcs-page">
    <header class="npcs-page__header"><div><p class="cultivation-eyebrow">RELATIONSHIPS</p><h1>人物关系</h1><p>记录固定核心人物、最近相遇与修炼变化。</p></div></header>
    <form class="npc-meet cultivation-surface" @submit.prevent="meetNpc">
      <div class="cultivation-section-heading"><div><h2>遇见普通弟子</h2><p>输入宗门标识和人口槽位，记录一次真实相遇。</p></div></div>
      <div class="npc-meet__fields">
        <label>宗门标识<input v-model.trim="sectKey" required autocomplete="off" /></label>
        <label>人口槽位<input v-model.number="populationIndex" type="number" min="0" step="1" required /></label>
        <button type="submit" class="cultivation-action" :disabled="meeting">{{ meeting ? '记录中...' : '遇见' }}</button>
      </div>
    </form>
    <div v-if="loading" class="cultivation-state">正在读取关系记录...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert"><span>关系记录暂时无法读取。</span><button type="button" class="cultivation-action" @click="load">重试</button></div>
    <template v-else>
      <section class="npc-population cultivation-surface" aria-labelledby="npc-population-title"><div class="cultivation-section-heading"><h2 id="npc-population-title">人口统计</h2><span>{{ totalCount }} 位记录</span></div><dl><div><dt>固定核心</dt><dd>{{ fixedCore.length }}</dd></div><div><dt>最近遇见</dt><dd>{{ recentlyMet.length }}</dd></div><div><dt>关系事件</dt><dd>{{ events.length }}</dd></div></dl></section>
      <section class="npc-groups">
        <NpcGroup title="固定核心 NPC" :items="fixedCore" empty="暂无固定核心 NPC。" />
        <NpcGroup title="最近遇见" :items="recentlyMet" empty="暂无最近遇见的 NPC。" />
      </section>
      <NpcTimeline :npcs="relationship" :events="events" />
    </template>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from 'vue'
import { cultivationService } from '../services/cultivation'
import NpcTimeline from '../components/cultivation/NpcTimeline.vue'

const relationship = ref({ fixed_core: [], recently_met: [], events: [] })
const loading = ref(false)
const error = ref(null)
const meeting = ref(false)
const sectKey = ref('sect-1-normal-1')
const populationIndex = ref(0)
const fixedCore = computed(() => relationship.value.fixed_core || [])
const recentlyMet = computed(() => relationship.value.recently_met || [])
const events = computed(() => relationship.value.events || [])
const totalCount = computed(() => fixedCore.value.length + recentlyMet.value.length)

const NpcGroup = defineComponent({
  props: { title: String, items: { type: Array, default: () => [] }, empty: String },
  setup(props) { return () => h('section', { class: 'npc-group cultivation-surface' }, [h('div', { class: 'cultivation-section-heading' }, [h('h2', props.title), h('span', `${props.items.length} 位`)]), props.items.length ? h('ul', { class: 'npc-list' }, props.items.map((npc) => h('li', { key: npc.id || npc.name }, [h('strong', npc.name || '未命名 NPC'), h('small', npc.role || npc.description || '关系信息待补充')]))) : h('p', { class: 'cultivation-fixed-state' }, props.empty)]) }
})

async function load() { loading.value = true; error.value = null; try { relationship.value = await cultivationService.getNpcs() || { fixed_core: [], recently_met: [], events: [] } } catch (requestError) { error.value = requestError } finally { loading.value = false } }
async function meetNpc() { meeting.value = true; error.value = null; try { await cultivationService.meetNpc({ sect_key: sectKey.value, population_index: Number(populationIndex.value) }); await load() } catch (requestError) { error.value = requestError } finally { meeting.value = false } }
onMounted(load)
</script>

<style scoped>
.npcs-page { display: grid; gap: var(--page-gap); }.npcs-page__header h1 { margin: 4px 0; color: var(--color-text); font-family: var(--font-family-display); }.npcs-page__header p:not(.cultivation-eyebrow) { margin: 0; color: var(--color-text-secondary); }.cultivation-eyebrow { margin: 0; color: var(--color-primary-dark); font-size: 11px; font-weight: 800; letter-spacing: .14em; }.cultivation-surface { display: grid; gap: var(--spacing-md); padding: var(--surface-padding); border: 1px solid var(--color-border); border-radius: var(--surface-radius); background: var(--color-card); box-shadow: var(--shadow-sm); }.npc-meet__fields { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) auto; gap: var(--spacing-md); align-items: end; }.npc-meet__fields label { display: grid; gap: 6px; color: var(--color-text-secondary); font-size: var(--font-size-sm); }.npc-meet__fields input { min-height: 40px; padding: 8px 10px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); color: var(--color-text); }.npc-population dl { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 0; }.npc-population dl div { padding: 12px; background: var(--color-bg-secondary); border-radius: var(--radius-md); }.npc-population dt { color: var(--color-text-secondary); font-size: var(--font-size-sm); }.npc-population dd { margin: 4px 0 0; color: var(--color-primary-dark); font-size: 1.35rem; font-weight: 800; }.npc-groups { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--page-gap); }.npc-list { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }.npc-list li { display: grid; gap: 4px; padding: 12px; border: 1px solid var(--color-border); border-radius: var(--radius-md); }.npc-list small { color: var(--color-text-secondary); }@media (max-width: 767px) { .npc-meet__fields, .npc-population dl, .npc-groups { grid-template-columns: 1fr; } }
</style>
