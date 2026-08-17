<template>
  <section class="cultivation-tribulation-probability stitch-surface" aria-labelledby="tribulation-probability-title">
    <h2 id="tribulation-probability-title">Tribulation preview</h2>
    <div v-if="loading" class="cultivation-probability-skeleton" aria-hidden="true"></div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert">
      <span>{{ errorMessage }}</span>
      <button type="button" class="cultivation-action" @click="$emit('retry')">Retry</button>
    </div>
    <template v-else-if="preview">
      <p class="cultivation-probability-value" aria-live="polite">{{ preview.final_probability }}%</p>
      <dl class="cultivation-probability-details">
        <div><dt>Target</dt><dd>{{ preview.target_realm }}</dd></div>
        <div><dt>Base</dt><dd>{{ preview.base_probability }}%</dd></div>
        <div><dt>Readiness</dt><dd>{{ preview.readiness_score }}</dd></div>
        <div><dt>Pill bonus</dt><dd>+{{ preview.pill_bonus }}%</dd></div>
        <div><dt>Failure loss</dt><dd>{{ preview.failure_loss_percent }}%</dd></div>
      </dl>
      <button type="button" class="cultivation-action" :disabled="Boolean(preview.cooldown_until)" @click="$emit('attempt')">Attempt tribulation</button>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ preview: { type: Object, default: null }, loading: Boolean, error: { type: [Object, String], default: null } })
defineEmits(['attempt', 'retry'])
const errorMessage = computed(() => props.error?.message || 'Tribulation preview could not be loaded.')
</script>
