<template>
  <button
    type="button"
    class="cultivation-map-node"
    :class="`cultivation-map-node--${status}`"
    role="option"
    :aria-label="nodeLabel"
    :aria-selected="selected"
    :aria-disabled="isLocked"
    @click="$emit('select', node)"
  >
    <span class="cultivation-map-node__icon" aria-hidden="true">{{ statusIcon }}</span>
    <span class="cultivation-map-node__copy">
      <span class="cultivation-map-node__name">{{ node?.name || '未知节点' }}</span>
      <span>{{ node?.description || '暂无节点描述。' }}</span>
    </span>
    <small>{{ statusLabel }}</small>
    <small v-if="isLocked && (node?.required_realm || node?.required_realm_label)">解锁条件：{{ realmLabel }}</small>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { labelFromServer, labelRealm, labelStatus } from '../../utils/displayLabels'

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
const statusLabel = computed(() => labelFromServer(props.node, 'status_label', status.value, labelStatus))
const realmLabel = computed(() => labelFromServer(props.node, 'required_realm_label', props.node?.required_realm, labelRealm))
const nodeLabel = computed(() => `${props.node?.name || '未知节点'}，${statusLabel.value}`)
</script>
