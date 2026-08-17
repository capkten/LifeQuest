<template>
  <section class="cultivation-realm-progress stitch-surface" aria-labelledby="realm-progress-title">
    <div v-if="loading" class="cultivation-progress-skeleton" aria-hidden="true"></div>
    <template v-else-if="progress">
      <div class="cultivation-section-heading">
        <h2 id="realm-progress-title">Realm progress</h2>
        <span>{{ progress.realm_key }} · Stage {{ progress.minor_stage }}</span>
      </div>
      <div class="cultivation-progress-track" role="progressbar" :aria-valuenow="progress.cultivation" :aria-valuemin="0" :aria-valuemax="progress.next_threshold || progress.cultivation">
        <span :style="{ width: `${progress.percent ?? 0}%` }"></span>
      </div>
      <p>{{ progress.cultivation }} / {{ progress.next_threshold ?? 'Max' }} · {{ progress.remaining }} remaining</p>
    </template>
  </section>
</template>

<script setup>
defineProps({ progress: { type: Object, default: null }, loading: Boolean })
</script>
