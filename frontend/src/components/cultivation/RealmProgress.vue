<template>
  <section class="cultivation-realm-progress stitch-surface" aria-labelledby="realm-progress-title">
    <div v-if="loading" class="cultivation-progress-skeleton" aria-hidden="true"></div>
    <template v-else-if="progress">
      <div class="cultivation-section-heading">
        <div>
          <span class="realm-kicker">当前境界</span>
          <h2 id="realm-progress-title">{{ realmLabel }} · 第{{ progress.minor_stage }}阶段</h2>
        </div>
        <span class="realm-percent">{{ progressPercentLabel }}</span>
      </div>
      <div class="cultivation-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="progressPercent">
        <span :style="{ width: `${progressPercent}%` }"></span>
      </div>
      <p class="realm-meta">
        <strong>{{ progress.cultivation }}</strong> / {{ progress.next_threshold ?? '已达当前上限' }}
        <span>还需 {{ progress.remaining }}</span>
      </p>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { labelFromServer, labelRealm } from '../../utils/displayLabels'

const props = defineProps({ progress: { type: Object, default: null }, loading: Boolean })
const realmLabel = computed(() => labelFromServer(props.progress, 'realm_label', props.progress?.realm_key, labelRealm))
const progressPercent = computed(() => {
  const current = Number(props.progress?.current_threshold ?? 0)
  const next = Number(props.progress?.next_threshold ?? current)
  const cultivation = Number(props.progress?.cultivation ?? current)
  if (next <= current) return 100
  return Math.min(100, Math.max(0, ((cultivation - current) / (next - current)) * 100))
})
const progressPercentLabel = computed(() => `${Math.round(progressPercent.value)}%`)
</script>
