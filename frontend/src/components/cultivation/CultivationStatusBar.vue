<template>
  <section class="cultivation-status-bar stitch-surface" aria-labelledby="cultivation-status-title" aria-live="polite">
    <div v-if="loading" class="cultivation-status-bar__skeleton" aria-hidden="true"></div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert">
      <span>{{ errorMessage }}</span>
      <button type="button" class="cultivation-action" @click="$emit('retry')">重试</button>
    </div>
    <template v-else-if="overview">
      <div class="cultivation-status-bar__heading">
        <span class="cultivation-eyebrow">修炼状态</span>
        <h2 id="cultivation-status-title">{{ realmLabel }} · 第{{ overview.minor_stage }}阶段</h2>
      </div>
      <div class="cultivation-status-bar__metrics">
        <span><strong>{{ overview.cultivation }}</strong> {{ resourceLabel('cultivation') }}</span>
        <span><strong>{{ overview.spirit_stones }}</strong> {{ resourceLabel('spirit_stones') }}</span>
        <span><strong>{{ overview.merit }}</strong> {{ resourceLabel('merit') }}</span>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { getErrorMessage } from '../../utils/errorMessage'
import { labelRealm, labelResource } from '../../utils/displayLabels'

const props = defineProps({ overview: { type: Object, default: null }, loading: Boolean, error: { type: [Object, String], default: null } })
defineEmits(['retry'])
const realmLabel = computed(() => props.overview?.realm_label || labelRealm(props.overview?.realm_key))
const resourceLabel = (key) => props.overview?.[`${key}_label`] || labelResource(key)
const errorMessage = computed(() => getErrorMessage(props.error, '修炼数据暂时无法读取。'))
</script>
