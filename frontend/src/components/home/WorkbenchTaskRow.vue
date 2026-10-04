<template>
  <div class="workbench-task" :class="{ 'is-complete': task.status === 'completed' }">
    <button
      type="button"
      class="complete-task"
      :disabled="busy || task.status === 'completed'"
      :aria-label="`${task.status === 'completed' ? '已完成' : '完成'} ${task.title}`"
      @click="$emit('complete', task)"
    >
      <span v-if="pending" aria-hidden="true">…</span>
      <span v-else-if="task.status === 'completed'" aria-hidden="true">✓</span>
      <span v-else class="unchecked" aria-hidden="true"></span>
    </button>
    <div class="task-copy">
      <span class="task-title">{{ task.title }}</span>
      <small v-if="task.deadline">{{ deadlineLabel }}</small>
      <small v-else>未设置截止时间</small>
    </div>
    <span v-if="task.status === 'completed'" class="status-label">已完成</span>
    <span v-else-if="task.status === 'in_progress'" class="status-label">进行中</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatChinaDateTime } from '../../utils/dateTime'

const props = defineProps({
  task: { type: Object, required: true },
  busy: { type: Boolean, default: false },
  pending: { type: Boolean, default: false }
})
defineEmits(['complete'])

const deadlineLabel = computed(() => {
  const deadline = formatChinaDateTime(props.task.deadline, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
  })
  return deadline ? `${deadline} 截止（中国时间）` : ''
})
</script>

<style scoped>
.workbench-task { display: flex; align-items: center; gap: 10px; min-width: 0; padding: 10px 0; }
.complete-task { display: grid; place-items: center; flex: 0 0 44px; width: 44px; height: 44px; border: 1px solid var(--color-border); border-radius: 12px; background: var(--color-card); color: var(--color-primary); font-size: 22px; cursor: pointer; }
.complete-task:disabled { cursor: default; }
.complete-task:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 3px; }
.unchecked { width: 18px; height: 18px; border: 2px solid currentColor; border-radius: 50%; }
.task-copy { display: grid; gap: 4px; flex: 1; min-width: 0; }
.task-title { color: var(--color-text); overflow-wrap: anywhere; font-weight: 600; line-height: 1.5; }
.task-copy small { color: var(--color-text-secondary); font-size: 12px; }
.status-label { color: var(--color-text-secondary); font-size: 12px; flex-shrink: 0; }
.is-complete .task-title { text-decoration: line-through; color: var(--color-text-secondary); }
.is-complete .complete-task { background: var(--color-bg); }
@media (max-width: 480px) { .complete-task { flex-basis: 48px; width: 48px; height: 48px; } .status-label { display: none; } }
</style>
