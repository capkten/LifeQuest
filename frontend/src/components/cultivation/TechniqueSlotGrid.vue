<template>
  <section class="cultivation-technique-slot-grid stitch-surface" aria-labelledby="technique-slot-title">
    <h2 id="technique-slot-title">Technique slots</h2>
    <div v-if="loading" class="cultivation-slot-grid" aria-hidden="true"><span v-for="index in 4" :key="index" class="cultivation-slot cultivation-slot--skeleton"></span></div>
    <div v-else class="cultivation-slot-grid">
      <button v-for="slot in slots" :key="`${slot.slot_type}-${slot.slot_index}`" type="button" class="cultivation-slot" :aria-label="`${slot.slot_type} slot ${slot.slot_index + 1}`" @click="$emit('select', slot)">
        <span>{{ slot.slot_type }}</span>
        <strong>{{ slot.technique_id ? 'Equipped' : 'Empty' }}</strong>
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({ slots: { type: Array, default: () => [] }, loading: Boolean })
defineEmits(['select'])
</script>
