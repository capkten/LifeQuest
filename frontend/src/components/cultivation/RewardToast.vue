<template>
  <div v-if="visible" class="cultivation-reward-toast" role="status" aria-live="polite">
    <strong>{{ title }}</strong>
    <span v-if="reward?.cultivation">+{{ reward.cultivation }} {{ resourceLabel('cultivation') }}</span>
    <span v-if="reward?.spirit_stones">+{{ reward.spirit_stones }} {{ resourceLabel('spirit_stones') }}</span>
    <button type="button" class="cultivation-icon-button" aria-label="关闭奖励提示" @click="$emit('dismiss')"><Close /></button>
  </div>
</template>

<script setup>
import { Close } from '@element-plus/icons-vue'
import { labelFromServer, labelResource } from '../../utils/displayLabels'

const props = defineProps({ reward: { type: Object, default: null }, visible: Boolean, title: { type: String, default: '获得奖励' } })
defineEmits(['dismiss'])
const resourceLabel = (key) => labelFromServer(props.reward, `${key}_label`, key, labelResource)
</script>
