<template>
  <button type="button" class="cultivation-map-node" :aria-label="node?.name || 'World node'" :disabled="node?.is_hidden" @click="$emit('select', node)">
    <span class="cultivation-map-node__name">{{ node?.name || 'Unknown node' }}</span>
    <span>{{ node?.description || 'No description available.' }}</span>
    <small v-if="node?.required_realm">Requires {{ node.required_realm }}</small>
  </button>
</template>

<script setup>
defineProps({ node: { type: Object, default: null } })
defineEmits(['select'])
</script>
