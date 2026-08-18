<template>
  <section class="cultivation-resource-summary stitch-surface" aria-labelledby="resource-summary-title">
    <h2 id="resource-summary-title">修炼资源</h2>
    <div v-if="loading" class="cultivation-resource-summary__skeleton" aria-hidden="true"></div>
    <dl v-else class="cultivation-resource-summary__list">
      <div v-for="item in resourceItems" :key="item.key">
        <dt>{{ resourceLabel(item) }}</dt>
        <dd>{{ resources?.[item.key] ?? 0 }}</dd>
      </div>
    </dl>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { labelResource } from '../../utils/displayLabels'

const props = defineProps({ resources: { type: Object, default: () => ({}) }, loading: Boolean })
const resourceItems = computed(() => [
  { key: 'spirit_stones' },
  { key: 'merit' },
  { key: 'contribution' },
  { key: 'mind_state' },
])
const resourceLabel = (item) => props.resources?.[`${item.key}_label`] || labelResource(item.key)
</script>
