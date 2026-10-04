<template>
  <div class="retreat-countdown-ring-container" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg
      :width="size"
      :height="size"
      :viewBox="`0 0 ${size} ${size}`"
      class="ring-svg"
      :class="{ 'breathing-glow': isFocusing }"
    >
      <defs>
        <linearGradient id="retreatRingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#38bdf8" />
          <stop offset="50%" stop-color="#4fd1c5" />
          <stop offset="100%" stop-color="#10b981" />
        </linearGradient>
        <filter id="inkGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      <!-- Background track -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        stroke="rgba(255, 255, 255, 0.08)"
        :stroke-width="strokeWidth"
        fill="transparent"
      />

      <!-- Animated progress ring -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        stroke="url(#retreatRingGradient)"
        :stroke-width="strokeWidth"
        fill="transparent"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        filter="url(#inkGlow)"
        class="progress-circle"
      />
    </svg>

    <!-- Center content -->
    <div class="ring-center-content">
      <div class="focus-time-display">{{ remainingFormatted }}</div>
      <div class="focus-status-subtext">
        <span v-if="isFocusing" class="status-badge pulse-dot">
          <span class="dot"></span>
          凝神入定中
        </span>
        <span v-else-if="remainingSeconds <= 0 && totalSeconds > 0" class="status-badge complete-text">
          功德圆满
        </span>
        <span v-else class="status-badge idle-text">
          静候入定
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  remainingSeconds: {
    type: Number,
    default: 0,
  },
  totalSeconds: {
    type: Number,
    default: 1500,
  },
  isFocusing: {
    type: Boolean,
    default: false,
  },
  size: {
    type: Number,
    default: 260,
  },
  strokeWidth: {
    type: Number,
    default: 8,
  },
})

const center = computed(() => props.size / 2)
const radius = computed(() => (props.size - props.strokeWidth) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)

const progressRatio = computed(() => {
  if (props.totalSeconds <= 0) return 0
  const elapsed = props.totalSeconds - props.remainingSeconds
  return Math.min(1, Math.max(0, elapsed / props.totalSeconds))
})

const dashOffset = computed(() => {
  return circumference.value * (1 - progressRatio.value)
})

const remainingFormatted = computed(() => {
  const mins = Math.floor(props.remainingSeconds / 60)
  const secs = props.remainingSeconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
})
</script>

<style scoped>
.retreat-countdown-ring-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
}

.ring-svg {
  transform: rotate(-90deg);
  overflow: visible;
  transition: filter 0.8s ease;
}

.progress-circle {
  transition: stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.breathing-glow {
  animation: breathingPulse 4s infinite ease-in-out;
}

@keyframes breathingPulse {
  0%, 100% {
    filter: drop-shadow(0 0 10px rgba(79, 209, 197, 0.25));
  }
  50% {
    filter: drop-shadow(0 0 24px rgba(79, 209, 197, 0.6));
  }
}

.ring-center-content {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  pointer-events: none;
}

.focus-time-display {
  font-family: 'Cinzel', 'Courier New', monospace;
  font-size: 3rem;
  font-weight: 700;
  letter-spacing: 2px;
  color: #f1f5f9;
  text-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
}

.focus-status-subtext {
  margin-top: 8px;
  font-size: 0.9rem;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 0.8rem;
}

.pulse-dot {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.pulse-dot .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 8px #38bdf8;
  animation: dotFlash 1.5s infinite ease-in-out;
}

@keyframes dotFlash {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.complete-text {
  color: #10b981;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.idle-text {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.1);
}
</style>
