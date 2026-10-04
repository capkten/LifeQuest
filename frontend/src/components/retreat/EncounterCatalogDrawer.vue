<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="val => emit('update:modelValue', val)"
    title="万象机缘录 · 顿悟图鉴"
    size="460px"
    direction="rtl"
    class="encounter-catalog-drawer"
  >
    <div class="catalog-body">
      <!-- Progress Banner -->
      <div class="catalog-summary-card">
        <div class="summary-top">
          <span class="summary-title">机缘共鸣总览</span>
          <span class="summary-count">{{ unlockedCount }} / {{ totalCount }}</span>
        </div>
        <el-progress
          :percentage="unlockPercentage"
          :color="progressColor"
          :stroke-width="8"
          :show-text="false"
        />
        <span class="summary-hint">
          修仙之人于洞府静定之中，神游天地，自有机缘福报随行入定。
        </span>
      </div>

      <!-- Encounter Grid / Cards -->
      <div v-loading="loading" class="encounter-list">
        <div
          v-for="item in catalog"
          :key="item.id"
          class="encounter-card"
          :class="{ 'is-unlocked': item.unlocked, 'is-locked': !item.unlocked }"
        >
          <!-- Unlocked Encounter -->
          <template v-if="item.unlocked">
            <div class="card-header">
              <span class="encounter-title">{{ item.title }}</span>
              <span class="rarity-badge" :class="`rarity-${item.rarity}`">
                {{ rarityLabel(item.rarity) }}
              </span>
            </div>
            <p class="story-excerpt">{{ item.story_text }}</p>
            <div class="card-footer">
              <span class="resonance-count">
                已结缘 {{ item.unlock_count }} 次
              </span>
              <span class="realm-pill">
                第 {{ item.min_realm_level }} 境
              </span>
            </div>
          </template>

          <!-- Locked Encounter -->
          <template v-else>
            <div class="card-header locked-header">
              <span class="encounter-title locked-title">🔒 冥蒙幽微</span>
              <span class="rarity-badge locked-rarity">未知</span>
            </div>
            <p class="locked-hint">
              灵识未开，机缘尚未显化。<br />
              需达第 {{ item.min_realm_level }} 境以上，潜心入定偶得。
            </p>
          </template>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useCultivationRetreat } from '../../composables/useCultivationRetreat.js'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const { catalog, loading, fetchCatalog } = useCultivationRetreat()

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      fetchCatalog()
    }
  },
  { immediate: true }
)

const totalCount = computed(() => catalog.value?.length || 0)
const unlockedCount = computed(() => catalog.value?.filter(i => i.unlocked)?.length || 0)
const unlockPercentage = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((unlockedCount.value / totalCount.value) * 100)
})

const progressColor = '#38bdf8'

function rarityLabel(rarity) {
  const map = {
    common: '凡缘',
    uncommon: '福源',
    rare: '奇缘',
    epic: '仙缘',
    legendary: '造化',
  }
  return map[rarity] || '机缘'
}
</script>

<style scoped>
.catalog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.catalog-summary-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-title {
  font-weight: 600;
  color: #f1f5f9;
}

.summary-count {
  font-family: monospace;
  font-size: 1.1rem;
  color: #38bdf8;
  font-weight: 700;
}

.summary-hint {
  font-size: 0.8rem;
  color: #94a3b8;
  line-height: 1.5;
}

.encounter-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  padding-right: 4px;
}

.encounter-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 14px 16px;
  transition: all 0.2s ease;
}

.encounter-card.is-unlocked {
  border-color: rgba(56, 189, 248, 0.25);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.encounter-card.is-locked {
  opacity: 0.55;
  background: rgba(15, 23, 42, 0.4);
  border-style: dashed;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.encounter-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #e2e8f0;
}

.rarity-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.rarity-common {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}

.rarity-uncommon {
  background: rgba(52, 211, 153, 0.15);
  color: #34d399;
}

.rarity-rare {
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
}

.rarity-epic {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
}

.rarity-legendary {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}

.story-excerpt {
  font-size: 0.85rem;
  color: #cbd5e1;
  line-height: 1.6;
  margin: 0 0 10px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
}

.resonance-count {
  color: #38bdf8;
}

.realm-pill {
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.04);
  padding: 2px 6px;
  border-radius: 4px;
}

.locked-title {
  color: #64748b;
}

.locked-hint {
  font-size: 0.8rem;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}
</style>
