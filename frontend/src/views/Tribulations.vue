<template>
  <div class="tribulations-page">
    <header class="tribulations-header"><div><p class="cultivation-eyebrow">修炼 · 渡劫</p><p>所有判定由服务器执行，先确认风险，再决定是否开始。</p></div></header>
    <Transition name="toast"><div v-if="errorToast" class="cultivation-state cultivation-state--error" role="alert" aria-live="polite">{{ errorToast }}</div></Transition>
    <AppState v-if="loading && !preview" state="loading" />
    <AppState v-else-if="error && !preview" state="error" :title="errorMessage">
      <template #actions>
        <AppButton variant="secondary" @click="load">重试</AppButton>
      </template>
    </AppState>
    <div v-else-if="!preview" class="cultivation-state" aria-live="polite">正在准备渡劫预览...</div>
    <template v-else>
      <section class="tribulations-layout">
        <div class="tribulations-main">
      <section class="tribulation-surface" aria-labelledby="current-realm-title"><div class="tribulation-heading"><h2 id="current-realm-title">当前境界</h2><strong>{{ realmLabel }}</strong></div><p class="tribulation-cultivation">当前小境界修为：<strong>{{ overview?.cultivation ?? 0 }}</strong></p><p class="tribulation-warning">失败损失：{{ preview.failure_loss }} 点修为（{{ preview.failure_loss_percent }}%）。不会降低境界名称或删除功法、装备、格子、宗门记录和 NPC 关系。</p></section>
      <TribulationProbability :preview="preview" :loading="loading" :error="error" :attempting="attempting" @attempt="attempt" @retry="syncAndLoad" />
        </div>
        <aside class="tribulations-side">
          <section class="tribulation-surface" aria-labelledby="readiness-title"><div class="tribulation-heading"><h2 id="readiness-title">渡劫准备度</h2><strong>{{ preview.readiness_score }}/100</strong></div><dl class="readiness-list"><div v-for="item in readinessItems" :key="item.key"><dt>{{ item.label }}</dt><dd>{{ preview.readiness_breakdown[item.key] }}</dd></div></dl></section>
          <section class="tribulation-surface" aria-labelledby="pill-title"><div class="tribulation-heading"><h2 id="pill-title">渡劫丹</h2><span>每颗 +5%</span></div><label for="pill-count">本次使用数量（最多 15 颗）</label><input id="pill-count" v-model.number="pillCount" type="number" min="0" max="15" step="1" :disabled="attempting" aria-describedby="pill-help"><p id="pill-help" class="tribulation-help">数量变化后，服务端会重新计算预览。</p></section>
        </aside>
      </section>
      <section v-if="result" class="tribulation-result" :class="result.success ? 'tribulation-result--success' : 'tribulation-result--failure'" role="status" aria-live="polite"><strong>{{ result.success ? '渡劫成功' : '渡劫失败' }}</strong><span>{{ result.success ? (result.terminal ? '已完成渡劫并进入飞升终点状态。' : `已进入${resultRealmLabel}初期。`) : `当前境界保留，损失 ${result.cultivation_loss} 点修为。` }}</span><small>结果日志：{{ result.log_id || '已记录' }} · {{ result.cooldown_until ? '次日可再次尝试' : '现在可再次尝试' }}</small></section>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import TribulationProbability from '../components/cultivation/TribulationProbability.vue'
import { cultivationService } from '../services/cultivation'
import { useCultivationStore } from '../stores/cultivation'
import { useToast } from '../composables/useToast'
import { getErrorMessage } from '../utils/errorMessage'
import { labelFromServer, labelRealm } from '../utils/displayLabels'
import { ElMessageBox } from 'element-plus'
import AppState from '../components/ui/AppState.vue'
import AppButton from '../components/ui/AppButton.vue'

const preview = ref(null), overview = ref(null), result = ref(null), error = ref(null), loading = ref(false), attempting = ref(false), pillCount = ref(0)
const { errorToast, showError } = useToast()
const cultivationStore = useCultivationStore()
let previewRequestId = 0
let previewController = null
const readinessItems = [{ key: 'mind_state', label: '心境状态' }, { key: 'habit', label: '最近 7 天习惯' }, { key: 'task_quality', label: '最近 7 天任务质量' }, { key: 'trial', label: '渡劫试炼质量' }, { key: 'compatibility', label: '功法宗门契合度' }]
const realmLabel = computed(() => `${labelFromServer(overview.value, 'realm_label', overview.value?.realm_key, labelRealm)} ${overview.value?.minor_stage || ''}`.trim())
const resultRealmLabel = computed(() => labelFromServer(result.value, 'target_realm_label', result.value?.target_realm, labelRealm))
const errorMessage = computed(() => getErrorMessage(error.value, '渡劫状态暂时无法读取。'))

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
  try { overview.value = await cultivationService.getOverview(); await loadPreview() } catch (cause) { error.value = cause; showError(errorMessage.value) } finally { loading.value = false }
}
async function syncAndLoad() {
  let syncError = null
  try { await cultivationStore.refresh() } catch (cause) { syncError = cause }
  await load()
  if (syncError) error.value = syncError
}
async function attempt() {
  if (attempting.value) return
  if (preview.value?.cooldown_until) { explainBlocked('渡劫冷却中，请等待冷却结束后再试。'); return }
  if (!preview.value?.available) { explainBlocked('渡劫前置条件未满足，请先完成渡劫试炼并达到要求。'); return }
  try {
    await ElMessageBox.confirm(
      `本次使用 ${preview.value.pill_count ?? pillCount.value} 颗渡劫丹，成功概率 ${preview.value.final_probability}% ，失败损失 ${preview.value.failure_loss} 点修为。确认开始渡劫吗？`,
      '确认渡劫',
      { confirmButtonText: '开始渡劫', cancelButtonText: '再想想', type: 'warning' },
    )
  } catch {
    return
  }
  attempting.value = true; error.value = null
  try {
    result.value = await cultivationService.attemptTribulation({ pill_count: pillCount.value })
    await syncAndLoad()
  } catch (cause) { error.value = cause; showError(errorMessage.value) } finally { attempting.value = false }
}
function explainBlocked(message) { showError(message) }
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
.tribulation-surface { display: grid; gap: 12px; padding: clamp(18px, 2.2vw, 26px); border: 0; border-radius: 22px; background: #FFFFFF; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03), 0 18px 40px -30px rgba(15, 23, 42, 0.35); }
.tribulation-heading { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.tribulation-heading h2 { margin: 0; color: var(--color-text); font-size: 15px; font-weight: 650; letter-spacing: -0.01em; }
.tribulation-heading strong { color: var(--rank-1-accent); font-variant-numeric: tabular-nums; }
.tribulation-warning, .tribulation-help { margin: 0; color: var(--home-ink-tertiary); line-height: 1.7; }
.readiness-list { display: grid; gap: 0; margin: 0; }
.readiness-list div { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--home-hairline); }
.readiness-list div:last-child { border-bottom: 0; }
.readiness-list dt { color: var(--home-ink-tertiary); }
.readiness-list dd { margin: 0; color: var(--color-text); font-weight: 600; font-variant-numeric: tabular-nums; }
label { color: var(--color-text); font-weight: 600; font-size: 13.5px; }
input { min-height: var(--touch-target-min); padding: 9px 14px; border: 0; border-radius: 12px; color: var(--color-text); background: var(--home-soft); font: inherit; }
input:focus { background: #FFFFFF; box-shadow: 0 0 0 3px rgba(12, 122, 91, 0.16); outline: none; }
.tribulation-result { display: grid; gap: 5px; padding: 20px 22px; border: 0; border-radius: 18px; background: var(--rank-1-bg); box-shadow: none; }
.tribulation-result--success { background: var(--rank-1-bg); }
.tribulation-result--failure { background: #FDF3E4; }
.tribulation-result span, .tribulation-result small { color: var(--home-ink-tertiary); }
@media (max-width: 767px) { .tribulations-layout { grid-template-columns: 1fr; } }
</style>
