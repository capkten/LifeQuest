<template>
  <section class="cultivation-technique-slot-grid stitch-surface" aria-labelledby="technique-slot-title" :aria-busy="busy || loading">
    <h2 id="technique-slot-title">功法格子</h2>
    <div v-if="loading" class="cultivation-slot-grid" aria-hidden="true"><span v-for="type in slotTypes" :key="type" class="cultivation-slot cultivation-slot--skeleton"></span></div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert">
      <span>{{ errorMessage }}</span>
      <button type="button" class="cultivation-action" :disabled="busy" @click="$emit('retry')">重试</button>
    </div>
    <div v-else class="cultivation-slot-grid">
      <button v-for="slot in visibleSlots" :key="`${slot.slot_type}-${slot.slot_index}`" type="button" class="cultivation-slot" :class="{ 'cultivation-slot--conflict': slot.conflict, 'cultivation-slot--next': slot.isNext }" :aria-label="`${slotLabel(slot.slot_type)}第${slot.slot_index + 1}格`" :disabled="busy" @click="$emit('select', slot)">
        <span class="cultivation-slot__type">{{ slotLabel(slot.slot_type) }}</span>
        <strong>{{ slot.isNext ? '购买下一格' : (slot.techniqueName || (slot.technique_id ? '已装备' : '空置')) }}</strong>
        <span v-if="slot.conflict" class="cultivation-slot__conflict">⚠ 冲突</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { getErrorMessage } from '../../utils/errorMessage'
import { labelSlotType } from '../../utils/displayLabels'

const props = defineProps({
  slots: { type: Array, default: () => [] },
  slotTypes: { type: Array, default: () => ['main', 'auxiliary', 'mind', 'movement', 'body'] },
  loading: Boolean,
  busy: Boolean,
  error: { type: [Object, String], default: null },
})
defineEmits(['select', 'retry'])
const errorMessage = computed(() => getErrorMessage(props.error, '暂无可用功法格子。'))
const visibleSlots = computed(() => props.slotTypes.flatMap((slotType) => props.slots.filter((slot) => slot.slot_type === slotType)))
function slotLabel(slotType) { return labelSlotType(slotType) }
</script>
