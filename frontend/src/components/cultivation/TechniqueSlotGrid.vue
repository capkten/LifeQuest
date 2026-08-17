<template>
  <section class="cultivation-technique-slot-grid stitch-surface" aria-labelledby="technique-slot-title" :aria-busy="busy || loading">
    <h2 id="technique-slot-title">Technique slots</h2>
    <div v-if="loading" class="cultivation-slot-grid" aria-hidden="true"><span v-for="index in 4" :key="index" class="cultivation-slot cultivation-slot--skeleton"></span></div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert">
      <span>{{ errorMessage }}</span>
      <button type="button" class="cultivation-action" :disabled="busy" @click="$emit('retry')">Retry</button>
    </div>
    <p v-else-if="!slots.length" class="cultivation-empty-state">No technique slots available.</p>
    <div v-else class="cultivation-slot-grid">
      <button v-for="slot in slots" :key="`${slot.slot_type}-${slot.slot_index}`" type="button" class="cultivation-slot" :aria-label="`${slot.slot_type} slot ${slot.slot_index + 1}`" :disabled="busy" @click="$emit('select', slot)">
        <span>{{ slot.slot_type }}</span>
        <strong>{{ slot.technique_id ? 'Equipped' : 'Empty' }}</strong>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ slots: { type: Array, default: () => [] }, loading: Boolean, busy: Boolean, error: { type: [Object, String], default: null } })
defineEmits(['select', 'retry'])
const errorMessage = computed(() => props.error?.message || 'Technique slots could not be loaded.')
</script>
