<template>
  <div class="techniques-page">
    <header><p class="cultivation-eyebrow">功法配置</p><h1>功法配置</h1><p>购买格子并配置已学会的功法。</p></header>
    <Transition name="toast"><div v-if="errorToast" class="cultivation-state cultivation-state--error" role="alert" aria-live="polite">{{ errorToast }}</div></Transition>
    <div v-if="loading" class="cultivation-state">正在读取功法...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert"><span>{{ error }}</span><button type="button" class="cultivation-action" :disabled="busy" @click="load">重试</button></div>
    <template v-else>
      <TechniqueSlotGrid :slots="displaySlots" :busy="busy" @select="selectSlot" />
      <section class="techniques-library cultivation-surface" aria-labelledby="technique-library-title">
        <div class="cultivation-section-heading"><h2 id="technique-library-title">功法库</h2><span>{{ techniques.length }} 部</span></div>
        <p v-if="!techniques.length" class="cultivation-state">暂无已学功法，功法库为空。</p>
        <ul v-else class="technique-list">
          <li v-for="technique in techniques" :key="technique.id" :class="{ 'technique-card--conflict': conflicts(technique).length, 'technique-card--locked': !technique.learned || technique.realm_confirmed === false }">
            <div><h3>{{ technique.name }}</h3><p>{{ technique.description || '暂无描述' }}</p></div>
            <dl><div><dt>功法类型</dt><dd>{{ techniqueTypeLabel(technique) }}</dd></div><div><dt>需要境界</dt><dd>{{ requiredRealmLabel(technique) }}</dd></div><div><dt>灵石</dt><dd>{{ technique.spirit_stone_cost }}</dd></div><div><dt>占用格数</dt><dd>{{ technique.slot_count }}</dd></div><div><dt>状态</dt><dd>{{ statusLabel(technique) }}</dd></div></dl>
            <button v-if="!technique.learned" type="button" class="cultivation-action" :disabled="busy" :aria-disabled="isLearnBlocked(technique)" @click="learn(technique)">{{ technique.realm_confirmed === false ? '境界不足' : spiritStones < technique.spirit_stone_cost ? '灵石不足' : '学习' }}</button>
            <button v-else type="button" class="cultivation-action" :disabled="busy" :aria-disabled="isEquipBlocked(technique)" @click="equip(technique)">{{ conflicts(technique).length ? '⚠ 冲突' : hasRequiredSlots(technique) ? '配置到选中格' : '连续格子不足' }}</button>
          </li>
        </ul>
      </section>
      <section v-if="selectedSlot" ref="purchasePanel" tabindex="-1" class="purchase-panel cultivation-surface" aria-labelledby="purchase-title">
        <div class="cultivation-section-heading"><h2 id="purchase-title">购买确认</h2><span>{{ slotLabel(selectedSlot.slot_type) }}</span></div>
        <p>当前灵石：{{ spiritStones }}</p><p>目标格子：{{ slotLabel(selectedSlot.slot_type) }}第 {{ selectedSlot.slot_index + 1 }} 格</p><p>需要境界：{{ requiredRealmLabel(selectedSlot) }} · 灵石：{{ selectedSlot.price }} · 购买后余额：{{ selectedSlot.balance }}</p>
        <p v-if="selectedSlot.can_purchase === false" class="cultivation-state cultivation-state--error" role="alert">{{ purchaseLockMessage }}</p>
        <p v-if="purchaseFeedback" class="cultivation-state cultivation-state--action" role="alert" aria-live="polite">{{ purchaseFeedback }}</p>
        <button type="button" class="cultivation-action" :disabled="busy" :aria-disabled="selectedSlot.purchased || selectedSlot.can_purchase === false" @click="purchase">{{ selectedSlot.purchased ? '已购买' : selectedSlot.can_purchase === false ? '暂不可购买' : '购买格子' }}</button>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import TechniqueSlotGrid from '../components/cultivation/TechniqueSlotGrid.vue'
import { cultivationService } from '../services/cultivation'
import { useToast } from '../composables/useToast'
import { getErrorMessage } from '../utils/errorMessage'
import { labelFromServer, labelRealm, labelSlotType, labelTechniqueType } from '../utils/displayLabels'

const slotTypes = ['main', 'auxiliary', 'mind', 'movement', 'body']
const { errorToast, showError } = useToast()
const techniques = ref([]); const slots = ref([]); const loadout = ref({}); const spiritStones = ref(0); const nextSlotPurchases = ref({}); const loading = ref(false); const error = ref(null); const busy = ref(false); const selectedSlot = ref(null); const purchaseFeedback = ref(null); const purchasePanel = ref(null)
const purchaseLockMessage = computed(() => {
  const slot = selectedSlot.value
  if (!slot) return '请先选择要购买的功法格子。'
  if (!slot.isNext || slot.purchased) return '该格子已经购买，请选择购买下一格。'
  if (slot.realm_confirmed === false) return `境界不足：需要达到${requiredRealmLabel(slot)}。`
  if (slot.can_purchase === false && Number.isFinite(slot.price) && spiritStones.value < slot.price) return `灵石不足：需要${slot.price}枚，当前仅有${spiritStones.value}枚。`
  return '当前购买条件尚未同步，请刷新后再试。'
})
const displaySlots = computed(() => slotTypes.flatMap((type) => { const owned = slots.value.filter((slot) => slot.slot_type === type).sort((a, b) => a.slot_index - b.slot_index); const preview = nextSlotPurchases.value[type]; const next = { slot_type: type, slot_index: preview?.next_slot_index ?? owned.length, technique_id: null, purchased: false, price: preview?.price, balance: preview?.post_purchase_balance, required_realm: preview?.required_realm, required_realm_label: labelFromServer(preview, 'required_realm_label', preview?.required_realm, labelRealm), realm_confirmed: preview?.realm_confirmed, isNext: true, can_purchase: preview?.can_purchase }; return [...owned.map((slot) => ({ ...slot, purchased: true, isNext: false })), next] }))
async function load() { loading.value = true; error.value = null; purchaseFeedback.value = null; try { applyLibrary(await cultivationService.getTechniques()) } catch (requestError) { error.value = getErrorMessage(requestError) } finally { loading.value = false } }
function applyLibrary(response) { techniques.value = response?.techniques || []; slots.value = response?.slots || []; loadout.value = response?.slot_assignments || response?.loadout || {}; spiritStones.value = response?.spirit_stones ?? 0; nextSlotPurchases.value = response?.next_slot_purchases || {} }
function slotLabel(type) { return labelSlotType(type) }
function techniqueTypeLabel(technique) { return labelFromServer(technique, 'technique_type_label', technique?.technique_type, labelTechniqueType) }
function requiredRealmLabel(record) { return labelFromServer(record, 'required_realm_label', record?.required_realm, labelRealm) }
function selectSlot(slot) {
  selectedSlot.value = slot
  purchaseFeedback.value = slot.isNext
    ? slot.can_purchase === true
      ? `已选择${slotLabel(slot.slot_type)}第${slot.slot_index + 1}格，请确认购买。`
      : purchaseLockMessage.value
    : `已选择${slotLabel(slot.slot_type)}第${slot.slot_index + 1}格。`
  nextTick(() => {
    if (!slot.isNext || !purchasePanel.value) return
    purchasePanel.value.scrollIntoView({ behavior: 'auto', block: 'center' })
    purchasePanel.value.focus({ preventScroll: true })
  })
}
function conflicts(technique) { return Object.entries(loadout.value).filter(([type, ids]) => type !== selectedSlot.value?.slot_type && (Array.isArray(ids) ? ids : [ids]).includes(technique.id)).map(([type]) => type) }
function selectedTypeSlots() { return slots.value.filter((slot) => slot.slot_type === selectedSlot.value?.slot_type).sort((a, b) => a.slot_index - b.slot_index) }
function requiredSlots(technique) { const owned = selectedTypeSlots(); const start = selectedSlot.value?.slot_index ?? -1; return owned.slice(start, start + technique.slot_count).filter((slot, offset) => slot.slot_index === start + offset) }
function hasRequiredSlots(technique) { return Boolean(selectedSlot.value?.purchased && requiredSlots(technique).length === technique.slot_count) }
function statusLabel(technique) { return labelFromServer(technique, 'status_label', technique?.status, () => { if (!technique.learned) return '未学会'; if (technique.realm_confirmed === false) return '境界不足'; if (conflicts(technique).length) return '⚠ 冲突'; if (!hasRequiredSlots(technique)) return '连续格子不足'; return '可配置' }) }
function explainBlocked(message) { showError(message) }
function explainPurchaseBlocked(message) { purchaseFeedback.value = message; showError(message) }
function isLearnBlocked(technique) { return Boolean(technique.learned || technique.realm_confirmed === false || spiritStones.value < technique.spirit_stone_cost) }
function isEquipBlocked(technique) { return Boolean(!selectedSlot.value || !selectedSlot.value.purchased || technique.realm_confirmed === false || conflicts(technique).length || !hasRequiredSlots(technique)) }
async function purchase() {
  const slot = selectedSlot.value
  if (busy.value) { explainPurchaseBlocked('上一笔购买仍在处理中，请稍候。'); return }
  if (!slot?.isNext || slot.purchased) { explainPurchaseBlocked('请先选择要购买的功法格子。'); return }
  if (slot.can_purchase !== true) { explainPurchaseBlocked(purchaseLockMessage.value); return }
  busy.value = true; purchaseFeedback.value = null
  try {
    await cultivationService.purchaseSlot(slot.slot_type)
    applyLibrary(await cultivationService.getTechniques())
    selectedSlot.value = displaySlots.value.find((candidate) => candidate.slot_type === slot.slot_type && candidate.isNext)
    purchaseFeedback.value = '格子购买成功，已刷新下一格购买条件。'
  } catch (requestError) {
    const message = getErrorMessage(requestError)
    explainPurchaseBlocked(message)
  } finally { busy.value = false }
}
async function learn(technique) { if (technique.learned) { explainBlocked('该功法已经学会。'); return } if (technique.realm_confirmed === false) { explainBlocked('境界不足：请先提升境界后再学习。'); return } if (spiritStones.value < technique.spirit_stone_cost) { explainBlocked('灵石不足：请先完成任务获得灵石后再学习。'); return } busy.value = true; error.value = null; try { await cultivationService.learnTechnique(technique.technique_key); applyLibrary(await cultivationService.getTechniques()) } catch (requestError) { const message = getErrorMessage(requestError); error.value = message; showError(message) } finally { busy.value = false } }
async function equip(technique) { if (!selectedSlot.value?.purchased) { explainBlocked('请先选择已购买的功法格子。'); return } if (technique.realm_confirmed === false) { explainBlocked('境界不足：请先提升境界后再配置。'); return } if (conflicts(technique).length) { explainBlocked('功法冲突：请先移除其他类型中的重复配置。'); return } if (!hasRequiredSlots(technique)) { explainBlocked('连续格子不足：请先购买足够的连续格子。'); return } busy.value = true; error.value = null; try { const assignments = Object.fromEntries(slotTypes.map((type) => { const count = slots.value.filter((slot) => slot.slot_type === type).length; const current = Array.isArray(loadout.value[type]) ? loadout.value[type] : [loadout.value[type]]; return [type, Array.from({ length: count }, (_, index) => current[index] ?? null)] })); for (const slot of requiredSlots(technique)) assignments[selectedSlot.value.slot_type][slot.slot_index] = technique.id; applyLibrary(await cultivationService.updateLoadout(assignments)) } catch (requestError) { const message = getErrorMessage(requestError); error.value = message; showError(message) } finally { busy.value = false } }
onMounted(load)
</script>

<style scoped>
.techniques-page,.technique-list{display:grid;gap:var(--page-gap)}header h1{margin:4px 0}header p:not(.cultivation-eyebrow){margin:0;color:var(--color-text-secondary)}.cultivation-eyebrow{margin:0;color:var(--color-primary-dark);font-size:11px;font-weight:800;letter-spacing:.14em}.cultivation-surface{display:grid;gap:var(--spacing-md);padding:var(--surface-padding);border:1px solid var(--color-border);border-radius:var(--surface-radius);background:var(--color-card);box-shadow:var(--shadow-sm)}.technique-list{margin:0;padding:0;list-style:none}.technique-list li{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(250px,1fr) auto;gap:var(--spacing-md);align-items:center;padding:var(--spacing-md);border:1px solid var(--color-border);border-left:4px solid var(--color-border);border-radius:var(--radius-md)}.technique-list li.technique-card--conflict{border-color:var(--color-error);border-left-color:var(--color-error)}.technique-list li.technique-card--locked{border-style:dashed}h3{margin:0}li p{margin:4px 0 0;color:var(--color-text-secondary)}dl{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:0}dt{color:var(--color-text-secondary);font-size:var(--font-size-sm)}dd{margin:2px 0 0;font-weight:700}.purchase-panel p{margin:0;color:var(--color-text-secondary)}.purchase-panel .cultivation-state{margin:0}.purchase-panel .cultivation-state--action{border:1px solid var(--color-warning);background:var(--color-bg-secondary);color:var(--color-text)}@media(max-width:767px){.technique-list li{grid-template-columns:1fr}.technique-list .cultivation-action{width:100%}}
</style>
