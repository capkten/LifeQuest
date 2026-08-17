<template>
  <div class="world-page">
    <header class="world-page__header"><div><p class="cultivation-eyebrow">WORLD MAP</p><h1>仙界地图</h1><p>选择节点查看进入条件与当前进度。</p></div></header>
    <div v-if="loading" class="cultivation-state">正在读取地图...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert"><span>地图暂时无法读取。</span><button type="button" class="cultivation-action" @click="load">重试</button></div>
    <div v-else-if="!nodes.length" class="cultivation-state">暂无可探索节点。</div>
    <section v-else class="world-layout">
      <div class="world-node-list" role="listbox" aria-label="世界节点">
        <MapNode v-for="node in nodes" :key="node.node_key" :node="node" :status="nodeStatus(node)" :locked="nodeStatus(node) === 'locked'" :selected="selectedNode?.node_key === node.node_key" @select="selectNode" />
      </div>
      <article v-if="selectedNode" class="world-detail cultivation-surface" aria-labelledby="world-detail-title">
        <div class="world-detail__status"><span aria-hidden="true">{{ statusIcon(nodeStatus(selectedNode)) }}</span>{{ statusLabel(nodeStatus(selectedNode)) }}</div>
        <h2 id="world-detail-title">{{ selectedNode.name }}</h2>
        <p>{{ selectedNode.description || '这个节点的详细记录尚未建立。' }}</p>
        <dl><div><dt>节点状态</dt><dd>{{ statusLabel(nodeStatus(selectedNode)) }}</dd></div><div><dt>解锁条件</dt><dd>{{ selectedNode.required_realm || '无需额外境界' }}</dd></div></dl>
      </article>
      <p v-else class="world-detail cultivation-surface">选择一个节点查看详情。</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useCultivationStore } from '../stores/cultivation'
import { cultivationService } from '../services/cultivation'
import MapNode from '../components/cultivation/MapNode.vue'

const store = useCultivationStore()
const nodes = ref([])
const selectedNode = ref(null)
const loading = ref(false)
const error = ref(null)
const overview = computed(() => store.overview)
const realmOrder = ['qi_refining', 'foundation', 'golden_core', 'nascent_soul', 'spirit_transformation', 'void_refining', 'body_combination', 'great_vehicle', 'tribulation', 'ascended']

async function load() {
  loading.value = true; error.value = null
  try {
    if (!overview.value) await store.loadOverview()
    const response = await cultivationService.getWorld()
    nodes.value = Array.isArray(response) ? response : (response?.nodes || [])
    selectedNode.value = currentNode(nodes.value) || nodes.value[0] || null
  } catch (requestError) { error.value = requestError } finally { loading.value = false }
}

function selectNode(node) { if (nodeStatus(node) !== 'locked') selectedNode.value = node }
function nodeStatus(node) {
  if (node?.is_hidden || node?.locked || node?.is_locked) return 'locked'
  const orderedNodes = [...nodes.value].sort((left, right) => left.sort_order - right.sort_order)
  const current = currentNode(orderedNodes)
  const currentRealm = currentRealmIndex()
  const requiredRealm = realmIndex(node?.required_realm)
  if (requiredRealm > currentRealm) return 'locked'
  if (current?.node_key === node?.node_key) return 'current'
  return orderedNodes.indexOf(node) < orderedNodes.indexOf(current) ? 'completed' : 'available'
}
function currentNode(nodeList = nodes.value) {
  const currentRealm = currentRealmIndex()
  return [...nodeList]
    .sort((left, right) => left.sort_order - right.sort_order)
    .find((node) => !node.is_hidden && realmIndex(node.required_realm) === currentRealm) ||
    [...nodeList].sort((left, right) => left.sort_order - right.sort_order).find((node) => !node.is_hidden && realmIndex(node.required_realm) <= currentRealm)
}
function currentRealmIndex() { return realmIndex(overview.value?.realm_key || overview.value?.realm?.key) }
function realmIndex(realm) {
  if (!realm) return 0
  const index = realmOrder.indexOf(realm)
  return index === -1 ? 0 : index
}
function statusLabel(status) { return ({ current: '当前所在', available: '可进入', completed: '已完成', locked: '已锁定' })[status] || '可进入' }
function statusIcon(status) { return ({ current: '●', available: '○', completed: '✓', locked: '锁' })[status] || '○' }
onMounted(load)
</script>

<style scoped>
.world-page { display: grid; gap: var(--page-gap); }
.world-page__header h1 { margin: 4px 0; color: var(--color-text); font-family: var(--font-family-display); }
.world-page__header p:not(.cultivation-eyebrow) { margin: 0; color: var(--color-text-secondary); }
.cultivation-eyebrow { margin: 0; color: var(--color-primary-dark); font-size: 11px; font-weight: 800; letter-spacing: .14em; }
.world-layout { display: grid; grid-template-columns: minmax(220px, 4fr) minmax(0, 8fr); gap: var(--page-gap); align-items: start; }
.world-node-list { display: grid; gap: 10px; min-width: 0; }
.world-detail { min-height: 260px; align-content: start; }
.world-detail h2 { margin: 0; color: var(--color-text); }
.world-detail p { margin: 0; line-height: 1.7; color: var(--color-text-secondary); }
.world-detail__status { color: var(--color-primary-dark); font-size: var(--font-size-sm); font-weight: 800; }
.world-detail dl { display: grid; gap: 10px; margin: 0; }
.world-detail dl div { display: flex; justify-content: space-between; gap: 16px; padding-top: 10px; border-top: 1px solid var(--color-border); }
.world-detail dt { color: var(--color-text-secondary); }.world-detail dd { margin: 0; font-weight: 700; color: var(--color-text); text-align: right; }
@media (max-width: 767px) { .world-layout { grid-template-columns: 1fr; } .world-detail { min-height: 180px; } }
</style>
