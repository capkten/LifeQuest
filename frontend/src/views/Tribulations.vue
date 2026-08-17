<template>
  <div class="tribulations-page">
    <header class="tribulations-header"><div><p class="cultivation-eyebrow">CULTIVATION / TRIBULATION</p><h1>渡劫准备</h1><p>所有判定由服务器执行，先确认风险，再决定是否开始。</p></div></header>
    <div v-if="loading && !preview" class="cultivation-state" aria-live="polite">正在读取渡劫状态...</div>
    <div v-else-if="error && !preview" class="cultivation-state cultivation-state--error" role="alert"><span>{{ errorMessage }}</span><button type="button" class="cultivation-action" @click="load">重试</button></div>
    <template v-else>
      <section class="tribulations-layout">
        <div class="tribulations-main">
          <section class="tribulation-surface" aria-labelledby="current-realm-title"><div class="tribulation-heading"><h2 id="current-realm-title">当前境界</h2><strong>{{ realmLabel }}</strong></div><p class="tribulation-cultivation">当前小境界修为：<strong>{{ overview.cultivation }}</strong></p><p class="tribulation-warning">失败损失：{{ preview.failure_loss }} 点修为（{{ preview.failure_loss_percent }}%）。不会降低境界名称或删除功法、装备、格子、宗门记录和 NPC 关系。</p></section>
      <TribulationProbability :preview="preview" :loading="loading" :error="error" :attempting="attempting" @attempt="attempt" @retry="syncAndLoad" />
        </div>
        <aside class="tribulations-side">
          <section class="tribulation-surface" aria-labelledby="readiness-title"><div class="tribulation-heading"><h2 id="readiness-title">渡劫准备度</h2><strong>{{ preview.readiness_score }}/100</strong></div><dl class="readiness-list"><div v-for="item in readinessItems" :key="item.key"><dt>{{ item.label }}</dt><dd>{{ preview.readiness_breakdown[item.key] }}</dd></div></dl></section>
          <section class="tribulation-surface" aria-labelledby="pill-title"><div class="tribulation-heading"><h2 id="pill-title">渡劫丹</h2><span>每颗 +5%</span></div><label for="pill-count">本次使用数量（最多 15 颗）</label><input id="pill-count" v-model.number="pillCount" type="number" min="0" max="15" step="1" :disabled="attempting" aria-describedby="pill-help"><p id="pill-help" class="tribulation-help">数量变化后，服务端会重新计算预览。</p></section>
        </aside>
      </section>
      <section v-if="result" class="tribulation-result" :class="result.success ? 'tribulation-result--success' : 'tribulation-result--failure'" role="status" aria-live="polite"><strong>{{ result.success ? '渡劫成功' : '渡劫失败' }}</strong><span>{{ result.success ? (result.terminal ? '已完成渡劫并进入飞升终点状态。' : `已进入${result.target_realm}初期。`) : `当前境界保留，损失 ${result.cultivation_loss} 点修为。` }}</span><small>结果日志：{{ result.log_id || '已记录' }} · {{ result.cooldown_until ? '次日可再次尝试' : '现在可再次尝试' }}</small></section>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import TribulationProbability from '../components/cultivation/TribulationProbability.vue'
import { cultivationService } from '../services/cultivation'
import { useCultivationStore } from '../stores/cultivation'

const preview = ref(null), overview = ref(null), result = ref(null), error = ref(null), loading = ref(false), attempting = ref(false), pillCount = ref(0)
const cultivationStore = useCultivationStore()
let previewRequestId = 0
let previewController = null
const readinessItems = [{ key: 'mind_state', label: '心境状态' }, { key: 'habit', label: '最近 7 天习惯' }, { key: 'task_quality', label: '最近 7 天任务质量' }, { key: 'trial', label: '渡劫试炼质量' }, { key: 'compatibility', label: '功法宗门契合度' }]
const realmLabel = computed(() => `${overview.value?.realm_key || '未知境界'} ${overview.value?.minor_stage || ''}`.trim())
const errorMessage = computed(() => error.value?.message || '渡劫状态暂时无法读取。')

async function loadPreview() {
  const requestId = ++previewRequestId
  previewController?.abort()
  previewController = new AbortController()
  error.value = null
  try {
    const nextPreview = await cultivationService.getTribulationPreview(pillCount.value, { signal: previewController.signal, skipErrorToast: true })
    if (requestId === previewRequestId) { preview.value = nextPreview; error.value = null }
  } catch (cause) {
    if (cause?.code !== 'ERR_CANCELED' && cause?.name !== 'CanceledError' && requestId === previewRequestId) error.value = cause
  }
}
async function load() {
  loading.value = true; error.value = null
  try { overview.value = await cultivationService.getOverview(); await loadPreview() } catch (cause) { error.value = cause } finally { loading.value = false }
}
async function syncAndLoad() {
  let syncError = null
  try { await cultivationStore.refresh() } catch (cause) { syncError = cause }
  await load()
  if (syncError) error.value = syncError
}
async function attempt() {
  if (attempting.value || preview.value?.cooldown_until) return
  attempting.value = true; error.value = null
  try {
    result.value = await cultivationService.attemptTribulation({ pill_count: pillCount.value })
    await syncAndLoad()
  } catch (cause) { error.value = cause } finally { attempting.value = false }
}
watch(pillCount, (value) => { const bounded = Math.max(0, Math.min(15, Number(value) || 0)); if (bounded !== value) pillCount.value = bounded; if (!attempting.value) loadPreview() })
onMounted(load)
onBeforeUnmount(() => previewController?.abort())
</script>

<style scoped>
.tribulations-page { display: grid; gap: var(--page-gap); }
.tribulations-header h1 { margin: 4px 0; color: var(--color-text); font-family: var(--font-family-display); }
.tribulations-header p { margin: 0; color: var(--color-text-secondary); }
.cultivation-eyebrow { color: var(--color-primary-dark) !important; font-size: 11px; font-weight: 800; letter-spacing: .14em; }
.tribulations-layout { display: grid; grid-template-columns: minmax(0, 7fr) minmax(280px, 5fr); gap: var(--page-gap); align-items: start; }
.tribulations-main, .tribulations-side { display: grid; gap: var(--page-gap); min-width: 0; }
.tribulation-surface { display: grid; gap: var(--spacing-md); padding: var(--surface-padding); border: 1px solid var(--color-border); border-radius: var(--surface-radius); background: var(--color-card); box-shadow: var(--shadow-sm); }
.tribulation-heading { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.tribulation-heading h2 { margin: 0; color: var(--color-text); font-size: 1.05rem; }
.tribulation-heading strong { color: var(--color-primary-dark); }
.tribulation-warning, .tribulation-help { margin: 0; color: var(--color-text-secondary); line-height: 1.7; }
.readiness-list { display: grid; gap: 12px; margin: 0; }
.readiness-list div { display: flex; justify-content: space-between; gap: 12px; }
.readiness-list dt { color: var(--color-text-secondary); }
.readiness-list dd { margin: 0; color: var(--color-text); font-weight: 700; }
label { color: var(--color-text); font-weight: 600; }
input { min-height: var(--touch-target-min); padding: 9px 10px; border: 1px solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text); background: var(--color-card); font: inherit; }
.tribulation-result { display: grid; gap: 5px; padding: var(--surface-padding); border-left: 4px solid var(--color-primary); background: var(--color-card); box-shadow: var(--shadow-sm); }
.tribulation-result--success { border-left-color: var(--color-success); }
.tribulation-result--failure { border-left-color: var(--color-warning); }
.tribulation-result span, .tribulation-result small { color: var(--color-text-secondary); }
@media (max-width: 767px) { .tribulations-layout { grid-template-columns: 1fr; } }
</style>
