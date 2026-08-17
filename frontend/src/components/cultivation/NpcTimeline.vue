<template>
  <section class="cultivation-npc-timeline stitch-surface" aria-labelledby="npc-timeline-title">
    <h2 id="npc-timeline-title">NPC timeline</h2>
    <ol v-if="items.length" class="cultivation-npc-timeline__list">
      <li v-for="item in items" :key="item.id || item.name">
        <strong>{{ item.name }}</strong>
        <span>{{ item.role || item.description || 'Relationship record' }}</span>
      </li>
    </ol>
    <p v-else class="cultivation-empty-state">No relationship records yet.</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ npcs: { type: Array, default: () => [] }, events: { type: Array, default: () => [] } })
const items = computed(() => [...props.npcs, ...props.events])
</script>
