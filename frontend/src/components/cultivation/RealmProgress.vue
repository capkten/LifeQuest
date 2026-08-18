<template>
  <section class="cultivation-realm-progress stitch-surface" aria-labelledby="realm-progress-title">
    <div v-if="loading" class="cultivation-progress-skeleton" aria-hidden="true"></div>
    <template v-else-if="progress">
      <div class="cultivation-section-heading">
        <h2 id="realm-progress-title">境界进度</h2>
        <span>{{ realmLabel }} · 第{{ progress.minor_stage }}阶段</span>
      </div>
      <div class="cultivation-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="progressPercent">
        <span :style="{ width: `${progressPercent}%` }"></span>
      </div>
      <p>{{ progress.cultivation }} / {{ progress.next_threshold ?? '已达当前上限' }} · 还需 {{ progress.remaining }}</p>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { labelRealm } from '../../utils/displayLabels'

const props = defineProps({ progress: { type: Object, default: null }, loading: Boolean })
const realmLabel = computed(() => props.progress?.realm_label || labelRealm(props.progress?.realm_key))
const progressPercent = computed(() => {
  const current = Number(props.progress?.current_threshold ?? 0)
  const next = Number(props.progress?.next_threshold ?? current)
  const cultivation = Number(props.progress?.cultivation ?? current)
  if (next <= current) return 100
  return Math.min(100, Math.max(0, ((cultivation - current) / (next - current)) * 100))
})
</script>
