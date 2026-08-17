<template>
  <section class="cultivation-npc-timeline stitch-surface" aria-labelledby="npc-timeline-title">
    <h2 id="npc-timeline-title">关系时间线</h2>
    <ol v-if="items.length" class="cultivation-npc-timeline__list">
      <li v-for="item in items" :key="item.key">
        <strong>{{ item.label }}</strong>
        <span>{{ item.detail }}</span>
        <time v-if="item.date" :datetime="item.date">{{ item.date }}</time>
      </li>
    </ol>
    <p v-else class="cultivation-empty-state">暂无关系事件</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ npcs: { type: [Array, Object], default: () => [] }, events: { type: Array, default: () => [] } })
const items = computed(() => {
  const relationship = Array.isArray(props.npcs)
    ? { fixed_core: props.npcs, recently_met: [], events: props.events }
    : props.npcs || {}

  return [
    ...toArray(relationship.fixed_core).map((item, index) => normalizeItem(item, 'core', index, 'NPC record')),
    ...toArray(relationship.recently_met).map((item, index) => normalizeItem(item, 'recent', index, 'NPC record')),
    ...toArray(relationship.events).map((item, index) => normalizeItem(item, 'event', index, 'Cultivation event')),
  ]
})

function toArray(value) {
  return Array.isArray(value) ? value : []
}

function normalizeItem(item, source, index, fallbackDetail) {
  const label = firstText(item?.name, item?.title, item?.event, item?.event_key, item?.type, item?.kind) || (source === 'event' ? 'Cultivation event ' : 'NPC record ') + (index + 1)
  return {
    key: source + '-' + index + '-' + (item?.id || item?.event_id || item?.key || 'record'),
    label,
    detail: firstText(item?.role, item?.description, item?.text, item?.summary, item?.message) || fallbackDetail,
    date: firstText(item?.date, item?.created_at, item?.occurred_at),
  }
}

function firstText(...values) {
  return values.find((value) => typeof value === 'string' && value.trim())?.trim() || ''
}
</script>
