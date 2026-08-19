<template>
  <div class="cultivation-page">
    <header class="cultivation-page__header">
      <div>
        <p class="cultivation-eyebrow">修炼</p>
        <h1>修炼总览</h1>
        <p>{{ realmLabel }} · 把今日行动转化为稳定的修为积累。</p>
      </div>
      <router-link class="cultivation-action" to="/todos">前往今日任务</router-link>
    </header>

    <div v-if="loading" class="cultivation-state cultivation-state--loading" aria-live="polite">正在读取修炼状态...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert">
      <span>修炼状态暂时无法读取。</span>
      <button type="button" class="cultivation-action" @click="load">重试</button>
    </div>
    <template v-else>
      <section class="cultivation-overview-grid">
        <div class="cultivation-primary-column">
          <RealmProgress :progress="progress" />
          <section class="cultivation-surface cultivation-today" aria-labelledby="today-title">
            <div class="cultivation-section-heading"><h2 id="today-title">今日修炼</h2><span>{{ todayItems.length }} 项</span></div>
            <ul v-if="todayItems.length" class="cultivation-list">
              <li v-for="item in todayItems" :key="item.id || item.title || item.label">
                <span class="cultivation-list__marker" aria-hidden="true">{{ item.completed ? '✓' : '○' }}</span>
                <span><strong>{{ item.title || item.label || '今日修炼' }}</strong><small>{{ item.description || item.detail || '完成日常行动以获得修为。' }}</small></span>
              </li>
            </ul>
            <p v-else class="cultivation-fixed-state">今天还没有安排修炼行动。</p>
          </section>
        </div>
        <aside class="cultivation-secondary-column">
          <ResourceSummary :resources="resources" />
          <section class="cultivation-surface" aria-labelledby="rewards-title">
            <div class="cultivation-section-heading"><h2 id="rewards-title">最近奖励</h2><span>{{ recentRewards.length }} 条</span></div>
            <ul v-if="recentRewards.length" class="cultivation-list cultivation-list--compact">
              <li v-for="reward in recentRewards" :key="reward.id || reward.log_id || reward.label">
                <span><strong>{{ reward.label || reward.title || '修炼奖励' }}</strong><small>{{ reward.description || reward.detail || (reward.cultivation ? `+${reward.cultivation} 修为` : '已获得') }}</small></span>
              </li>
            </ul>
            <p v-else class="cultivation-fixed-state">暂无最近奖励。</p>
          </section>
        </aside>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useCultivationStore } from '../stores/cultivation'
import RealmProgress from '../components/cultivation/RealmProgress.vue'
import ResourceSummary from '../components/cultivation/ResourceSummary.vue'
import { labelFromServer, labelRealm } from '../utils/displayLabels'

const store = useCultivationStore()
const overview = computed(() => store.overview)
const loading = computed(() => store.loading)
const error = computed(() => store.error)
const realm = computed(() => overview.value?.realm || { key: overview.value?.realm_key, minor_stage: overview.value?.minor_stage })
const realmLabel = computed(() => `${labelFromServer(overview.value, 'realm_label', realm.value?.key, () => labelFromServer(realm.value, 'realm_label', realm.value?.key, labelRealm))} ${realm.value?.minor_stage || ''}`.trim())
const progress = computed(() => overview.value?.next_stage || overview.value?.progress)
const resources = computed(() => projectResources(overview.value))
const todayItems = computed(() => toArray(overview.value?.today))
const recentRewards = computed(() => toArray(overview.value?.recent_rewards))

function projectResources(overview) {
  const nestedResources = overview?.resources && typeof overview.resources === 'object' && !Array.isArray(overview.resources)
    ? overview.resources
    : {}
  const resourceKeys = ['cultivation', 'spirit_stones', 'merit', 'contribution', 'mind_state']

  return resourceKeys.reduce((projected, key) => {
    const value = overview?.[key] ?? nestedResources[key]
    const labelKey = `${key}_label`
    const label = overview?.[labelKey] ?? nestedResources[labelKey]
    if (value !== undefined) projected[key] = value
    if (label !== undefined) projected[labelKey] = label
    return projected
  }, { ...nestedResources })
}

function toArray(value) {
  return Array.isArray(value) ? value : []
}

async function load() {
  await store.loadOverview().catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.cultivation-page { display: grid; gap: var(--page-gap); }
.cultivation-page__header { display: flex; align-items: end; justify-content: space-between; gap: 16px; }
.cultivation-page__header h1 { margin: 4px 0; color: var(--color-text); font-family: var(--font-family-display); }
.cultivation-page__header p { margin: 0; color: var(--color-text-secondary); }
.cultivation-eyebrow { color: var(--color-primary-dark) !important; font-size: 11px; font-weight: 800; letter-spacing: .14em; }
.cultivation-overview-grid { display: grid; grid-template-columns: minmax(0, 7fr) minmax(280px, 5fr); gap: var(--page-gap); align-items: start; }
.cultivation-primary-column, .cultivation-secondary-column { display: grid; gap: var(--page-gap); min-width: 0; }
.cultivation-surface { display: grid; gap: var(--spacing-md); padding: var(--surface-padding); border: 1px solid var(--color-border); border-radius: var(--surface-radius); background: var(--color-card); box-shadow: var(--shadow-sm); }
.cultivation-section-heading { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.cultivation-section-heading h2 { margin: 0; color: var(--color-text); font-size: 1.05rem; }
.cultivation-section-heading span { color: var(--color-text-secondary); font-size: var(--font-size-sm); }
.cultivation-list { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
.cultivation-list li { display: flex; gap: 10px; align-items: flex-start; padding: 12px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg-secondary); }
.cultivation-list__marker { color: var(--color-success); font-weight: 800; }
.cultivation-list strong, .cultivation-list small { display: block; }
.cultivation-list small { margin-top: 4px; color: var(--color-text-secondary); }
.cultivation-fixed-state, .cultivation-state { min-height: 64px; display: grid; place-items: center; margin: 0; color: var(--color-text-secondary); }
.cultivation-state { padding: var(--surface-padding); border: 1px solid var(--color-border); border-radius: var(--surface-radius); background: var(--color-card); }
.cultivation-state--error { color: var(--color-error-dark); }
.cultivation-state--error .cultivation-action { color: #fff; }
@media (max-width: 767px) { .cultivation-page__header, .cultivation-overview-grid { grid-template-columns: 1fr; display: grid; } .cultivation-page__header .cultivation-action { width: 100%; } }
</style>
