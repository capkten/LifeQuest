<template>
  <button type="button" class="cultivation-map-node" :aria-label="nodeLabel" :disabled="isLocked" @click="$emit('select', node)">
    <span class="cultivation-map-node__name">{{ node?.name || 'Unknown node' }}</span>
    <span>{{ node?.description || 'No description available.' }}</span>
    <small v-if="isLocked">Locked</small>
    <small v-else-if="node?.required_realm">Requires {{ node.required_realm }}</small>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ node: { type: Object, default: null }, locked: Boolean })
defineEmits(['select'])
const isLocked = computed(() => props.locked || props.node?.locked || props.node?.is_locked || props.node?.is_hidden)
const nodeLabel = computed(() => `${props.node?.name || 'World node'}${isLocked.value ? ' (Locked)' : ''}`)
</script>
