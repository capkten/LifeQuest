<template>
  <svg viewBox="0 0 120 100" class="cave-pet" :class="{ 'cave-pet--silhouette': silhouette }" aria-hidden="true" focusable="false">
    <ellipse cx="60" cy="88" rx="42" ry="7" class="pet-shadow" />
    <g v-if="pet === 'white_deer'">
      <path d="M22 75Q17 47 46 48q31-2 38 28l-8 10H25Z" class="pet-deer" /><path d="M73 72q-5-24 6-42 14-4 20 10L87 74" class="pet-deer" />
      <path d="m82 32-9-14m15 12 8-18m-18 11-8 1m23-4 9-1" class="pet-antlers" /><path d="m93 43 9 2m-55 20 12 15" class="pet-detail" /><circle cx="93" cy="40" r="1.6" class="pet-eye" />
    </g>
    <g v-else-if="pet === 'spirit_fox'">
      <path d="M47 77Q4 85 13 43q6 17 33 14Z" class="pet-fox" /><path d="M16 52q-4 13 4 20l14-5q-15-5-18-15" class="pet-light" />
      <path d="M39 79q-2-30 19-35 25 6 33 35l-8 8H42Z" class="pet-fox" /><path d="m48 47-6-31 23 18 23-18-3 34-20 16Z" class="pet-fox" /><path d="m47 48 18 18 20-17-20 7Z" class="pet-light" /><path d="m52 46 7 2m14 0 6-2" class="pet-detail" /><circle cx="65" cy="58" r="2" class="pet-eye" />
    </g>
    <g v-else-if="pet === 'cloud_crane'">
      <path d="M47 60q-15-17-27-12 5 25 35 26 28-4 29-24-17-10-37 10" class="pet-crane" /><path d="M76 54q-16-22-3-34 16-7 24 5l-16 6q-4 8 5 20" class="pet-crane" />
      <path d="m90 25 25 5-25 3Z" class="pet-antler-fill" /><path d="m49 58 18 10-24 1Z" class="pet-wing" /><path d="m54 73-1 14m19-16-4 15m-22 1h16m1 0h14" class="pet-legs" /><circle cx="86" cy="24" r="1.6" class="pet-eye" /><path d="M75 20q7-8 14 0" class="pet-crown" />
    </g>
  </svg>
</template>

<script setup>
defineProps({ pet: { type: String, required: true }, silhouette: { type: Boolean, default: false } })
</script>

<style scoped>
.cave-pet { display: block; width: 120px; height: 100px; color: #536d62; }.pet-shadow { fill: #a6b99e; opacity: .3; }.pet-deer,.pet-light { fill: #f2f0db; }.pet-fox { fill: #b98955; }.pet-crane { fill: #edf0e8; }.pet-wing { fill: #6f8780; }.pet-antlers,.pet-legs { stroke: #a18d6b; stroke-width: 3; fill: none; stroke-linecap: round; }.pet-antler-fill { fill: #a18d6b; }.pet-detail { stroke: #667c6b; stroke-width: 2; fill: none; stroke-linecap: round; }.pet-eye { fill: #344b42; }.pet-crown { fill: none; stroke: #aa8172; stroke-width: 4; }.cave-pet--silhouette { opacity: .22; }.cave-pet--silhouette path,.cave-pet--silhouette circle { fill: currentColor; stroke: currentColor; }.cave-pet--silhouette .pet-shadow { opacity: .1; }
</style>
