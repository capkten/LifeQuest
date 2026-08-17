<template>
  <section class="tribulation-probability stitch-surface" aria-labelledby="tribulation-probability-title" :aria-busy="operationBusy">
    <div class="tribulation-section-heading">
      <div><p class="tribulation-eyebrow">RISK PREVIEW</p><h2 id="tribulation-probability-title">成功概率</h2></div>
      <span class="tribulation-target">目标：{{ preview?.target_realm || '读取中' }}</span>
    </div>
    <div v-if="loading" class="tribulation-loading" aria-live="polite">正在计算渡劫概率...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert">
      <span>{{ errorMessage }}</span><button type="button" class="cultivation-action" :disabled="loading || operationBusy" @click="$emit('retry')">重试</button>
    </div>
    <template v-else-if="preview">
      <p v-if="!preview.available" class="cultivation-state cultivation-state--locked" role="status">{{ lockReasonLabel }}</p>
      <div class="tribulation-probability-value" aria-live="polite"><strong>{{ preview.final_probability }}%</strong><span>最终成功率</span></div>
      <dl class="tribulation-details">
        <div><dt>基础成功率</dt><dd>{{ preview.base_probability }}%</dd></div>
        <div><dt>准备度加成</dt><dd>{{ signed(preview.readiness_bonus) }}%</dd></div>
        <div><dt>渡劫丹加成</dt><dd>+{{ preview.pill_bonus }}%</dd></div>
        <div><dt>失败损失</dt><dd>{{ preview.failure_loss_percent }}%</dd></div>
        <div><dt>冷却</dt><dd>{{ cooldownLabel }}</dd></div>
      </dl>
      <button v-if="preview.available" type="button" class="cultivation-action tribulation-submit" :disabled="loading || operationBusy" @click="$emit('attempt')">
        <span v-if="operationBusy" aria-hidden="true" class="tribulation-spinner"></span>{{ operationBusy ? '渡劫判定中...' : '开始渡劫' }}
      </button>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ preview: { type: Object, default: null }, loading: Boolean, error: { type: [Object, String], default: null }, attempting: Boolean, submitting: Boolean })
defineEmits(['attempt', 'retry'])
const operationBusy = computed(() => props.loading || props.attempting || props.submitting)
const errorMessage = computed(() => props.error?.response?.data?.detail || props.error?.message || '渡劫预览暂时无法读取。')
const lockReasonLabel = computed(() => ({
  FINAL_MINOR_STAGE_REQUIRED: '尚未达到当前境界的最终小境界阈值。',
  TRIBULATION_COOLDOWN_ACTIVE: '渡劫冷却中，请稍后再试。',
  ASCENDED: '已达飞升终点。',
}[props.preview?.lock_reason] || props.preview?.lock_reason || '当前暂不可渡劫。'))
const cooldownLabel = computed(() => props.preview?.cooldown_until ? `下一次可尝试：${formatCooldown(props.preview.cooldown_until)}` : '现在可尝试')
function formatCooldown(value) {
  return new Date(value).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
}
function signed(value) { return Number(value) > 0 ? `+${value}` : value }
</script>

<style scoped>
.tribulation-probability { display: grid; gap: var(--spacing-md); }
.tribulation-section-heading { display: flex; justify-content: space-between; align-items: start; gap: 12px; }
.tribulation-eyebrow { margin: 0 0 4px; color: var(--color-primary-dark); font-size: 11px; font-weight: 800; letter-spacing: .14em; }
.tribulation-section-heading h2 { margin: 0; color: var(--color-text); font-size: 1.1rem; }
.tribulation-target { color: var(--color-text-secondary); font-size: var(--font-size-sm); }
.tribulation-probability-value { display: grid; gap: 2px; padding: 18px; border: 1px solid var(--color-border); background: var(--color-bg-secondary); text-align: center; }
.tribulation-probability-value strong { color: var(--color-primary-dark); font-size: 2.2rem; line-height: 1; }
.tribulation-probability-value span, .tribulation-loading { color: var(--color-text-secondary); }
.tribulation-details { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 16px; margin: 0; }
.tribulation-details div { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--color-border); padding-bottom: 8px; }
.tribulation-details dt { color: var(--color-text-secondary); }
.tribulation-details dd { margin: 0; color: var(--color-text); font-weight: 700; text-align: right; }
.tribulation-submit { width: 100%; }
.tribulation-spinner { width: 14px; height: 14px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; display: inline-block; vertical-align: -2px; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .tribulation-spinner { animation: none; } }
@media (max-width: 520px) { .tribulation-section-heading { display: grid; } .tribulation-details { grid-template-columns: 1fr; } }
</style>
