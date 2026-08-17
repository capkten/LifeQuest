<template>
  <section class="cultivation-status-bar stitch-surface" aria-labelledby="cultivation-status-title" aria-live="polite">
    <div v-if="loading" class="cultivation-status-bar__skeleton" aria-hidden="true"></div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert">
      <span>{{ errorMessage }}</span>
      <button type="button" class="cultivation-action" @click="$emit('retry')">Retry</button>
    </div>
    <template v-else-if="overview">
      <div class="cultivation-status-bar__heading">
        <span class="cultivation-eyebrow">Cultivation</span>
        <h2 id="cultivation-status-title">{{ overview.realm_key }} · Stage {{ overview.minor_stage }}</h2>
      </div>
      <div class="cultivation-status-bar__metrics">
        <span><strong>{{ overview.cultivation }}</strong> cultivation</span>
        <span><strong>{{ overview.spirit_stones }}</strong> spirit stones</span>
        <span><strong>{{ overview.merit }}</strong> merit</span>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ overview: { type: Object, default: null }, loading: Boolean, error: { type: [Object, String], default: null } })
defineEmits(['retry'])
const errorMessage = computed(() => props.error?.message || 'Cultivation data could not be loaded.')
</script>
