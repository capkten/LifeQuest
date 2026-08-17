<template>
  <div class="techniques-page">
    <header class="techniques-page__header"><div><p class="cultivation-eyebrow">TECHNIQUE LOADOUT</p><h1>功法配置</h1><p>购买格子并配置已学会的功法。</p></div></header>
    <div v-if="loading" class="cultivation-state">正在读取功法...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert"><span>{{ errorMessage }}</span><button type="button" class="cultivation-action" @click="load">重试</button></div>
    <template v-else>
      <TechniqueSlotGrid :slots="displaySlots" :busy="busy" @select="selectSlot" />
      <section class="techniques-library cultivation-surface" aria-labelledby="technique-library-title"><div class="cultivation-section-heading"><h2 id="technique-library-title">功法库</h2><span>{{ techniques.length }} 部</span></div><ul class="technique-list"><li v-for="technique in techniques" :key="technique.id" :class="{ 'technique-card--conflict': conflicts(technique).length }"><div><h3>{{ technique.name }}</h3><p>{{ technique.description || '暂无描述' }}</p></div><dl><div><dt>需要境界</dt><dd>{{ technique.required_realm || '无' }}</dd></div><div><dt>灵石</dt><dd>{{ technique.spirit_stone_cost }}</dd></div><div><dt>占用格数</dt><dd>{{ technique.slot_count }}</dd></div><div><dt>状态</dt><dd>{{ conflicts(technique).length ? '⚠ 冲突' : technique.learned ? '可配置' : '未学会' }}</dd></div></dl><button type="button" class="cultivation-action" :disabled="busy || !technique.learned || !selectedSlot" @click="equip(technique)">{{ conflicts(technique).length ? '配置并处理冲突' : '配置到选中格' }}</button></li></ul></section>
      <section v-if="selectedSlot" class="purchase-panel cultivation-surface" aria-labelledby="purchase-title"><div class="cultivation-section-heading"><h2 id="purchase-title">购买确认</h2><span>{{ slotLabel(selectedSlot.slot_type) }}</span></div><p>目标格子：{{ slotLabel(selectedSlot.slot_type) }}第 {{ selectedSlot.slot_index + 1 }} 格</p><p>需要境界：{{ selectedSlot.required_realm || '服务器确认' }} · 灵石：{{ selectedSlot.price }} · 购买后余额：{{ selectedSlot.balance }}</p><button type="button" class="cultivation-action" :disabled="busy || selectedSlot.purchased" @click="purchase">{{ selectedSlot.purchased ? '已购买' : '购买格子' }}</button></section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import TechniqueSlotGrid from '../components/cultivation/TechniqueSlotGrid.vue'
import { cultivationService } from '../services/cultivation'

const slotTypes = ['main', 'auxiliary', 'mind', 'body']; const prices = [0, 100, 300, 800, 2000, 5000, 12000]
const techniques = ref([]); const slots = ref([]); const loadout = ref({ main: null, auxiliary: null, mind: null, body: null }); const loading = ref(false); const error = ref(null); const busy = ref(false); const selectedSlot = ref(null)
const errorMessage = computed(() => error.value?.response?.data?.detail || error.value?.message || '功法暂时无法读取。')
const displaySlots = computed(() => slotTypes.map((type) => { const current = slots.value.find((slot) => slot.slot_type === type); const index = current?.slot_index || 0; const price = current?.price ?? prices[index + 1] ?? 0; return { slot_type: type, slot_index: index, technique_id: loadout.value[type], purchased: Boolean(current), price, balance: current?.balance ?? '服务器返回后显示', required_realm: current?.required_realm || '服务器确认', techniqueName: techniques.value.find((item) => item.id === loadout.value[type])?.name, conflict: false } }))
async function load() { loading.value = true; error.value = null; try { const response = await cultivationService.getTechniques(); applyLibrary(response) } catch (requestError) { error.value = requestError } finally { loading.value = false } }
function applyLibrary(response) { techniques.value = response?.techniques || []; slots.value = response?.slots || []; loadout.value = { ...loadout.value, ...(response?.loadout || {}) } }
function slotLabel(type) { return ({ main: '主修', auxiliary: '辅修', mind: '心法', body: '身法' })[type] || type }
function selectSlot(slot) { selectedSlot.value = displaySlots.value.find((item) => item.slot_type === slot.slot_type) || slot }
function conflicts(technique) { return slotTypes.filter((type) => type !== selectedSlot.value?.slot_type && loadout.value[type] === technique.id) }
async function purchase() { if (!selectedSlot.value) return; busy.value = true; error.value = null; try { const result = await cultivationService.purchaseSlot(selectedSlot.value.slot_type); slots.value = slots.value.filter((slot) => slot.slot_type !== selectedSlot.value.slot_type).concat({ ...selectedSlot.value, ...result, purchased: true }); selectedSlot.value = displaySlots.value.find((slot) => slot.slot_type === selectedSlot.value.slot_type) } catch (requestError) { error.value = requestError } finally { busy.value = false } }
async function equip(technique) { if (!selectedSlot.value) return; busy.value = true; error.value = null; try { const response = await cultivationService.updateLoadout({ ...loadout.value, [selectedSlot.value.slot_type]: technique.id }); applyLibrary(response) } catch (requestError) { error.value = requestError } finally { busy.value = false } }
onMounted(load)
</script>

<style scoped>
.techniques-page,.technique-list{display:grid;gap:var(--page-gap)}.techniques-page__header h1{margin:4px 0;font-family:var(--font-family-display)}.techniques-page__header p:not(.cultivation-eyebrow){margin:0;color:var(--color-text-secondary)}.cultivation-eyebrow{margin:0;color:var(--color-primary-dark);font-size:11px;font-weight:800;letter-spacing:.14em}.cultivation-surface{display:grid;gap:var(--spacing-md);padding:var(--surface-padding);border:1px solid var(--color-border);border-radius:var(--surface-radius);background:var(--color-card);box-shadow:var(--shadow-sm)}.technique-list{margin:0;padding:0;list-style:none}.technique-list li{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(250px,1fr) auto;gap:var(--spacing-md);align-items:center;padding:var(--spacing-md);border:1px solid var(--color-border);border-left:4px solid var(--color-border);border-radius:var(--radius-md)}.technique-list li.technique-card--conflict{border-color:var(--color-error);border-left-color:var(--color-error)}h3{margin:0}li p{margin:4px 0 0;color:var(--color-text-secondary)}dl{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:0}dt{color:var(--color-text-secondary);font-size:var(--font-size-sm)}dd{margin:2px 0 0;font-weight:700}.purchase-panel p{margin:0;color:var(--color-text-secondary)}@media(max-width:767px){.technique-list li{grid-template-columns:1fr}.technique-list .cultivation-action{width:100%}}
</style>
