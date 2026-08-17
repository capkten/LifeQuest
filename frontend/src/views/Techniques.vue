<template>
  <div class="techniques-page">
    <header><p class="cultivation-eyebrow">TECHNIQUE LOADOUT</p><h1>功法配置</h1><p>购买格子并配置已学会的功法。</p></header>
    <div v-if="loading" class="cultivation-state">正在读取功法...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert"><span>{{ errorMessage }}</span><button type="button" class="cultivation-action" :disabled="busy" @click="load">重试</button></div>
    <template v-else>
      <TechniqueSlotGrid :slots="displaySlots" :busy="busy" @select="selectSlot" />
      <section class="techniques-library cultivation-surface" aria-labelledby="technique-library-title">
        <div class="cultivation-section-heading"><h2 id="technique-library-title">功法库</h2><span>{{ techniques.length }} 部</span></div>
        <p v-if="!techniques.length" class="cultivation-state">暂无已学功法，功法库为空。</p>
        <ul v-else class="technique-list">
          <li v-for="technique in techniques" :key="technique.id" :class="{ 'technique-card--conflict': conflicts(technique).length, 'technique-card--locked': !technique.learned || technique.realm_confirmed === false }">
            <div><h3>{{ technique.name }}</h3><p>{{ technique.description || '暂无描述' }}</p></div>
            <dl><div><dt>需要境界</dt><dd>{{ technique.required_realm || '无' }}</dd></div><div><dt>灵石</dt><dd>{{ technique.spirit_stone_cost }}</dd></div><div><dt>占用格数</dt><dd>{{ technique.slot_count }}</dd></div><div><dt>状态</dt><dd>{{ statusLabel(technique) }}</dd></div></dl>
            <button type="button" class="cultivation-action" :disabled="busy || !selectedSlot || !technique.learned || technique.realm_confirmed === false || conflicts(technique).length" @click="equip(technique)">{{ conflicts(technique).length ? '⚠ 冲突' : '配置到选中格' }}</button>
          </li>
        </ul>
      </section>
      <section v-if="selectedSlot" class="purchase-panel cultivation-surface" aria-labelledby="purchase-title">
        <div class="cultivation-section-heading"><h2 id="purchase-title">购买确认</h2><span>{{ slotLabel(selectedSlot.slot_type) }}</span></div>
        <p>目标格子：{{ slotLabel(selectedSlot.slot_type) }}第 {{ selectedSlot.slot_index + 1 }} 格</p><p>需要境界：{{ selectedSlot.required_realm }} · 灵石：{{ selectedSlot.price }} · 购买后余额：{{ selectedSlot.balance }}</p>
        <button type="button" class="cultivation-action" :disabled="busy || selectedSlot.purchased" @click="purchase">{{ selectedSlot.purchased ? '已购买' : '购买格子' }}</button>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import TechniqueSlotGrid from '../components/cultivation/TechniqueSlotGrid.vue'
import { cultivationService } from '../services/cultivation'

const slotTypes = ['main', 'auxiliary', 'mind', 'body']
const prices = [0, 100, 300, 800, 2000, 5000, 12000]
const techniques = ref([]); const slots = ref([]); const loadout = ref({}); const loading = ref(false); const error = ref(null); const busy = ref(false); const selectedSlot = ref(null)
const errorMessage = computed(() => error.value?.response?.data?.detail || error.value?.message || '功法暂时无法读取。')
const displaySlots = computed(() => slotTypes.flatMap((type) => { const owned = slots.value.filter((slot) => slot.slot_type === type); const nextIndex = owned.length; const next = { slot_type: type, slot_index: nextIndex, technique_id: null, purchased: false, price: prices[nextIndex] ?? prices.at(-1) * (2 ** (nextIndex - prices.length + 1)), balance: '服务器返回后显示', required_realm: owned.at(-1)?.required_realm || '服务器确认', isNext: true }; return [...owned.map((slot) => ({ ...slot, purchased: true, isNext: false })), next] }))
async function load() { loading.value = true; error.value = null; try { applyLibrary(await cultivationService.getTechniques()) } catch (requestError) { error.value = requestError } finally { loading.value = false } }
function applyLibrary(response) { techniques.value = response?.techniques || []; slots.value = response?.slots || []; loadout.value = response?.slot_assignments || response?.loadout || {} }
function slotLabel(type) { return ({ main: '主修', auxiliary: '辅修', mind: '心法', body: '身法' })[type] || type }
function selectSlot(slot) { selectedSlot.value = slot }
function conflicts(technique) { return Object.entries(loadout.value).filter(([type, ids]) => type !== selectedSlot.value?.slot_type && (Array.isArray(ids) ? ids : [ids]).includes(technique.id)).map(([type]) => type) }
function statusLabel(technique) { if (!technique.learned) return '未学会'; if (technique.realm_confirmed === false) return '境界不足'; if (conflicts(technique).length) return '⚠ 冲突'; return '可配置' }
async function purchase() { if (!selectedSlot.value?.isNext) return; busy.value = true; error.value = null; try { const result = await cultivationService.purchaseSlot(selectedSlot.value.slot_type); slots.value = [...slots.value, result]; selectedSlot.value = displaySlots.value.find((slot) => slot.slot_type === result.slot_type && slot.isNext) } catch (requestError) { error.value = requestError } finally { busy.value = false } }
async function equip(technique) { if (!selectedSlot.value?.purchased || !technique.learned || technique.realm_confirmed === false) return; busy.value = true; error.value = null; try { const assignments = Object.fromEntries(slotTypes.map((type) => [type, Array.isArray(loadout.value[type]) ? [...loadout.value[type]] : loadout.value[type] ? [loadout.value[type]] : []])); assignments[selectedSlot.value.slot_type][selectedSlot.value.slot_index] = technique.id; applyLibrary(await cultivationService.updateLoadout(assignments)) } catch (requestError) { error.value = requestError } finally { busy.value = false } }
onMounted(load)
</script>

<style scoped>
.techniques-page,.technique-list{display:grid;gap:var(--page-gap)}header h1{margin:4px 0}header p:not(.cultivation-eyebrow){margin:0;color:var(--color-text-secondary)}.cultivation-eyebrow{margin:0;color:var(--color-primary-dark);font-size:11px;font-weight:800;letter-spacing:.14em}.cultivation-surface{display:grid;gap:var(--spacing-md);padding:var(--surface-padding);border:1px solid var(--color-border);border-radius:var(--surface-radius);background:var(--color-card);box-shadow:var(--shadow-sm)}.technique-list{margin:0;padding:0;list-style:none}.technique-list li{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(250px,1fr) auto;gap:var(--spacing-md);align-items:center;padding:var(--spacing-md);border:1px solid var(--color-border);border-left:4px solid var(--color-border);border-radius:var(--radius-md)}.technique-list li.technique-card--conflict{border-color:var(--color-error);border-left-color:var(--color-error)}.technique-list li.technique-card--locked{border-style:dashed}h3{margin:0}li p{margin:4px 0 0;color:var(--color-text-secondary)}dl{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:0}dt{color:var(--color-text-secondary);font-size:var(--font-size-sm)}dd{margin:2px 0 0;font-weight:700}.purchase-panel p{margin:0;color:var(--color-text-secondary)}@media(max-width:767px){.technique-list li{grid-template-columns:1fr}.technique-list .cultivation-action{width:100%}}
</style>
