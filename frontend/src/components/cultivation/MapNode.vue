<template>
  <button
    type="button"
    class="cultivation-map-node"
    :class="`cultivation-map-node--${status}`"
    role="option"
    :aria-label="nodeLabel"
    :aria-selected="selected"
    :disabled="isLocked"
    @click="$emit('select', node)"
  >
    <span class="cultivation-map-node__icon" aria-hidden="true">{{ statusIcon }}</span>
    <span class="cultivation-map-node__copy">
      <span class="cultivation-map-node__name">{{ node?.name || 'Unknown node' }}</span>
      <span>{{ node?.description || 'No description available.' }}</span>
    </span>
    <small>{{ statusLabel }}</small>
    <small v-if="isLocked && node?.required_realm">解锁条件：{{ node.required_realm }}</small>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  node: { type: Object, default: null },
  locked: Boolean,
  selected: Boolean,
  status: { type: String, default: 'available' },
})
defineEmits(['select'])
const isLocked = computed(() => props.locked || props.node?.locked || props.node?.is_locked || props.node?.is_hidden)
const status = computed(() => isLocked.value ? 'locked' : props.status)
const statusIcon = computed(() => ({ current: '●', available: '○', completed: '✓', locked: '锁' }[status.value] || '○'))
const statusLabel = computed(() => ({ current: '当前所在', available: '可进入', completed: '已完成', locked: '已锁定' }[status.value] || '可进入'))
const nodeLabel = computed(() => `${props.node?.name || 'World node'}，${statusLabel.value}`)
</script>
