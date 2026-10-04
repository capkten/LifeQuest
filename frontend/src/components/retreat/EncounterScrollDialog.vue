<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="val => emit('update:modelValue', val)"
    :show-close="false"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    class="encounter-scroll-dialog"
    width="520px"
    center
  >
    <div v-if="encounter" class="scroll-wrapper">
      <!-- Top Scroll Roller -->
      <div class="scroll-roller scroll-roller-top">
        <span class="roller-end left"></span>
        <span class="roller-bar"></span>
        <span class="roller-end right"></span>
      </div>

      <!-- Ancient Parchment / Xuan Paper Body -->
      <div class="scroll-parchment-body">
        <!-- Rarity Seal Stamp -->
        <div class="seal-stamp" :class="`seal-${encounter.rarity || 'common'}`">
          {{ rarityText }}
        </div>

        <!-- Scroll Header -->
        <div class="scroll-header">
          <span class="scroll-sub">机缘降临 · 冥冥感应</span>
          <h2 class="scroll-title">{{ encounter.title }}</h2>
        </div>

        <!-- Story Text -->
        <div class="story-content">
          <p class="story-paragraph">
            {{ encounter.story_text }}
          </p>
        </div>

        <!-- Reward Section -->
        <div class="rewards-section">
          <span class="rewards-label">【机缘造化奖励】</span>
          <div class="rewards-tags">
            <span v-if="encounter.reward_payload?.exp" class="reward-pill exp-pill">
              ✨ 修为 +{{ encounter.reward_payload.exp }}
            </span>
            <span v-if="encounter.reward_payload?.coins" class="reward-pill coin-pill">
              💎 灵石 +{{ encounter.reward_payload.coins }}
            </span>
            <span v-if="encounter.reward_payload?.item_name" class="reward-pill item-pill">
              🎁 获赠：{{ encounter.reward_payload.item_name }}
            </span>
          </div>
        </div>

        <!-- Claim Action -->
        <div class="scroll-actions">
          <button class="claim-scroll-btn" @click="handleClaim">
            收纳机缘 · 铭感五内
          </button>
        </div>
      </div>

      <!-- Bottom Scroll Roller -->
      <div class="scroll-roller scroll-roller-bottom">
        <span class="roller-end left"></span>
        <span class="roller-bar"></span>
        <span class="roller-end right"></span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  encounter: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue', 'claim'])

const rarityMap = {
  common: '凡缘',
  uncommon: '福源',
  rare: '奇缘',
  epic: '仙缘',
  legendary: '大造化',
}

const rarityText = computed(() => {
  return rarityMap[props.encounter?.rarity] || '机缘'
})

function handleClaim() {
  emit('claim', props.encounter)
  emit('update:modelValue', false)
}
</script>

<style scoped>
.scroll-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  filter: drop-shadow(0 12px 32px rgba(0, 0, 0, 0.6));
  animation: scrollUnroll 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes scrollUnroll {
  from {
    transform: scaleY(0.6) scaleX(0.9);
    opacity: 0;
  }
  to {
    transform: scaleY(1) scaleX(1);
    opacity: 1;
  }
}

.scroll-roller {
  width: 104%;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 2;
}

.roller-bar {
  flex: 1;
  height: 14px;
  background: linear-gradient(180deg, #78350f 0%, #451a03 100%);
  border-radius: 4px;
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.2);
}

.roller-end {
  width: 16px;
  height: 18px;
  background: linear-gradient(180deg, #d97706 0%, #92400e 100%);
  border-radius: 2px;
}

.scroll-parchment-body {
  position: relative;
  width: 100%;
  background: linear-gradient(180deg, #fdf6e2 0%, #faecd0 50%, #fdf6e2 100%);
  color: #292524;
  padding: 32px 36px 28px;
  box-shadow: inset 0 0 40px rgba(180, 83, 9, 0.15);
  border-left: 2px solid #b45309;
  border-right: 2px solid #b45309;
}

.seal-stamp {
  position: absolute;
  top: 24px;
  right: 28px;
  border: 2px solid #b91c1c;
  color: #b91c1c;
  font-weight: 700;
  font-size: 0.85rem;
  letter-spacing: 2px;
  padding: 4px 8px;
  border-radius: 4px;
  transform: rotate(-12deg);
  opacity: 0.85;
  box-shadow: 0 0 0 1px rgba(185, 28, 28, 0.2);
}

.seal-stamp.seal-epic,
.seal-stamp.seal-legendary {
  border-color: #7c2d12;
  color: #7c2d12;
  background: rgba(220, 38, 38, 0.08);
}

.scroll-header {
  text-align: center;
  margin-bottom: 20px;
}

.scroll-sub {
  font-size: 0.8rem;
  letter-spacing: 3px;
  color: #78350f;
}

.scroll-title {
  margin: 6px 0 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #451a03;
  letter-spacing: 2px;
}

.story-content {
  margin: 16px 0 24px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 8px;
  border: 1px dashed rgba(180, 83, 9, 0.3);
}

.story-paragraph {
  line-height: 1.8;
  font-size: 0.95rem;
  color: #44403c;
  margin: 0;
  text-indent: 2em;
}

.rewards-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
}

.rewards-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #78350f;
}

.rewards-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.reward-pill {
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 600;
}

.exp-pill {
  background: rgba(14, 165, 233, 0.15);
  color: #0369a1;
  border: 1px solid rgba(14, 165, 233, 0.3);
}

.coin-pill {
  background: rgba(245, 158, 11, 0.15);
  color: #b45309;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.item-pill {
  background: rgba(168, 85, 247, 0.15);
  color: #7e22ce;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.scroll-actions {
  display: flex;
  justify-content: center;
}

.claim-scroll-btn {
  background: linear-gradient(180deg, #78350f 0%, #451a03 100%);
  color: #fef3c7;
  border: none;
  border-radius: 6px;
  padding: 10px 28px;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 2px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(69, 26, 3, 0.35);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.claim-scroll-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(69, 26, 3, 0.45);
}

.claim-scroll-btn:active {
  transform: translateY(1px);
}
</style>
