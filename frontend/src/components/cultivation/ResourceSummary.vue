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
import { labelFromServer, labelResource } from '../../utils/displayLabels'

const props = defineProps({ resources: { type: Object, default: () => ({}) }, loading: Boolean })
const resourceItems = computed(() => [
  { key: 'spirit_stones' },
  { key: 'merit' },
  { key: 'contribution' },
  { key: 'mind_state' },
])
const resourceLabel = (item) => labelFromServer(props.resources, `${item.key}_label`, item.key, labelResource)
</script>

<style scoped>
.cultivation-resource-summary h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

/* The four resources read as one band of figures, not four labelled rows. */
.cultivation-resource-summary__list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 8px;
}

.cultivation-resource-summary__list div {
  display: grid;
  gap: 2px;
  justify-content: start;
  padding: 10px 14px;
  border-radius: 14px;
  background: var(--home-soft);
}

.cultivation-resource-summary__list dt {
  color: var(--home-ink-tertiary);
  font-size: 11.5px;
}

.cultivation-resource-summary__list dd {
  color: var(--color-text);
  font-size: 20px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}
</style>
