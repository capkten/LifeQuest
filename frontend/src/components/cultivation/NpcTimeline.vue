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
import { labelEventSummary, labelFromServer, labelNpcRole } from '../../utils/displayLabels'

const props = defineProps({ npcs: { type: [Array, Object], default: () => [] }, events: { type: Array, default: () => [] } })
const items = computed(() => {
  const relationship = Array.isArray(props.npcs)
    ? { fixed_core: props.npcs, recently_met: [], events: props.events }
    : props.npcs || {}

  return [
    ...toArray(relationship.fixed_core).map((item, index) => normalizeItem(item, 'core', index)),
    ...toArray(relationship.recently_met).map((item, index) => normalizeItem(item, 'recent', index)),
    ...toArray(relationship.events).map((item, index) => normalizeItem(item, 'event', index)),
  ]
})

function toArray(value) {
  return Array.isArray(value) ? value : []
}

function normalizeItem(item, source, index) {
  const label = source === 'event'
    ? eventLabel(item)
    : firstText(item?.name, item?.title) || `人物记录${index + 1}`
  const roleLabel = labelFromServer(item, 'role_label', item?.role, labelNpcRole)
  return {
    key: source + '-' + index + '-' + (item?.id || item?.event_id || item?.key || 'record'),
    label,
    detail: source === 'event'
      ? eventDetail(item)
      : roleLabel !== '未知身份' ? roleLabel : firstText(item?.description, item?.text, item?.message) || '人物信息待补充',
    date: firstText(item?.date, item?.created_at, item?.occurred_at),
  }
}

function eventLabel(item) {
  const eventKey = firstText(item?.event_key)
  return labelFromServer(item, 'summary_label', eventKey, () => labelFromServer(
    { summary: firstText(item?.summary) },
    'summary',
    eventKey,
    () => labelEventSummary(eventKey),
  ))
}

function eventDetail(item) {
  const eventKey = firstText(item?.event_key)
  for (const key of ['detail', 'text', 'message']) {
    const detail = labelFromServer(item, key, eventKey, '')
    if (detail) return detail
  }
  return '关系事件记录'
}

function firstText(...values) {
  return values.find((value) => typeof value === 'string' && value.trim())?.trim() || ''
}
</script>
