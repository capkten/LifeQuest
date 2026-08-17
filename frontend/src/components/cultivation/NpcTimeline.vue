<template>
  <section class="cultivation-npc-timeline stitch-surface" aria-labelledby="npc-timeline-title">
    <h2 id="npc-timeline-title">NPC timeline</h2>
    <ol v-if="items.length" class="cultivation-npc-timeline__list">
      <li v-for="item in items" :key="item.key">
        <strong>{{ item.label }}</strong>
        <span>{{ item.detail }}</span>
      </li>
    </ol>
    <p v-else class="cultivation-empty-state">No relationship records yet.</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ npcs: { type: Array, default: () => [] }, events: { type: Array, default: () => [] } })
const items = computed(() => [
  ...props.npcs.map((item, index) => normalizeItem(item, 'npc', index, 'Relationship record')),
  ...props.events.map((item, index) => normalizeItem(item, 'event', index, 'Cultivation event')),
])

function normalizeItem(item, source, index, fallbackDetail) {
  const label = item?.name || item?.title || item?.event || item?.type || 'Cultivation record'
  return {
    key: `${source}-${item?.id || item?.event_id || item?.key || index}`,
    label,
    detail: item?.role || item?.description || item?.text || item?.message || fallbackDetail,
  }
}
</script>
