<template>
  <section class="cultivation-resource-summary stitch-surface" aria-labelledby="resource-summary-title">
    <h2 id="resource-summary-title">Resources</h2>
    <div v-if="loading" class="cultivation-resource-summary__skeleton" aria-hidden="true"></div>
    <dl v-else class="cultivation-resource-summary__list">
      <div v-for="item in resourceItems" :key="item.key">
        <dt>{{ item.label }}</dt>
        <dd>{{ resources?.[item.key] ?? 0 }}</dd>
      </div>
    </dl>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ resources: { type: Object, default: () => ({}) }, loading: Boolean })
const resourceItems = computed(() => [
  { key: 'spirit_stones', label: 'Spirit stones' },
  { key: 'merit', label: 'Merit' },
  { key: 'contribution', label: 'Contribution' },
  { key: 'mind_state', label: 'Mind state' },
])
</script>
