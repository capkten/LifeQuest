<template>
  <div v-if="visible" class="cultivation-reward-toast" role="status" aria-live="polite">
    <strong>{{ title }}</strong>
    <span v-if="reward?.cultivation">+{{ reward.cultivation }} cultivation</span>
    <span v-if="reward?.spirit_stones">+{{ reward.spirit_stones }} spirit stones</span>
    <button type="button" class="cultivation-icon-button" aria-label="Dismiss reward" @click="$emit('dismiss')">×</button>
  </div>
</template>

<script setup>
defineProps({ reward: { type: Object, default: null }, visible: Boolean, title: { type: String, default: 'Reward received' } })
defineEmits(['dismiss'])
</script>
