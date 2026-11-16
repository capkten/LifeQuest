<template>
  <div class="cave-scene" :class="[`cave-scene--${mode}`, { 'cave-scene--focusing': focusing }]" aria-hidden="true">
    <svg viewBox="0 0 760 340" preserveAspectRatio="xMidYMid slice" focusable="false">
      <rect width="760" height="340" class="scene-wall" />
      <path d="M146 266V133a118 118 0 0 1 236 0v133Z" class="scene-window" />
      <circle cx="302" cy="86" r="25" class="scene-sun" />
      <path d="m146 192 58-65 52 43 57-70 69 97v69H146Z" class="scene-mountain scene-mountain--far" />
      <path d="m146 240 72-63 58 35 54-39 52 54v39H146Z" class="scene-mountain" />
      <path d="M147 222q86-18 235 0M147 245q104-17 235 0" class="scene-mist" />
      <path d="M138 266V133a126 126 0 0 1 252 0v133M127 266h274" class="scene-stone" />
      <path d="M0 284q350-24 760-2v58H0Z" class="scene-floor" />
      <path d="M40 314h156m407-8h107M137 289h48" class="scene-floor-line" />
      <ellipse cx="338" cy="284" rx="76" ry="15" class="scene-mat" />
      <ellipse cx="338" cy="283" rx="60" ry="8" class="scene-mat-ring" />
      <g class="scene-xiaoman">
        <path d="M303 257q-26 4-27 20 29 11 63 4 37 8 64-3-7-16-32-21" class="scene-robe" />
        <path d="M314 219q24-12 47 0l19 47q-36 15-83 0Z" class="scene-robe" />
        <path d="M329 226v34m21-34-12 35" class="scene-robe-fold" />
        <path d="m314 228-14 25 29 9m31-34 14 25-25 10" class="scene-arms" />
        <ellipse cx="338" cy="199" rx="25" ry="28" class="scene-skin" />
        <path d="M313 198q-8-42 27-38 32 0 24 40l-10-18q-18 14-40 11Z" class="scene-hair" />
        <circle cx="340" cy="157" r="10" class="scene-hair" />
        <path d="m323 204 7 1m16 0 7-1m-18 11q4 3 8 0" class="scene-face" />
      </g>
      <g class="scene-table">
        <path d="M448 231h179l-7 11H453Z" class="scene-wood" />
        <path d="m463 242-6 44m149-44 6 44" class="scene-table-legs" />
        <path d="m502 225 56-3 22 8-60 1Z" class="scene-paper" />
        <path d="m517 225 23 1m-15-3 17 1" class="scene-ink" />
        <path d="M472 228v-18m-11 19h23" class="scene-lamp-base" />
        <path d="M456 204q0-28 15-32 17 7 17 32l-3 8h-26Z" class="scene-lantern" />
        <path d="M472 197q-9-8 0-18 10 12 0 18Z" class="scene-flame" />
        <path d="m594 231-8-28h25l-4 28Z" class="scene-wood" />
        <path d="m591 210-4-21m9 19 1-25m4 25 7-21" class="scene-sign-sticks" />
      </g>
      <CavePet v-if="companion" :pet="companion" x="500" y="195" />
      <g v-for="place in Math.min(waitingPlaces, 2)" :key="place" class="scene-empty-mat" :transform="`translate(${companion ? 460 + (place - 1) * 200 : 535 + (place - 1) * 110}, 287)`">
        <ellipse rx="30" ry="8" class="scene-mat" />
        <path d="M-22 0h44" class="scene-mat-ring" />
      </g>
      <path d="M697 0v147m-12-9 12 9 13-12M697 69l-24-19m24 47 26-18" class="scene-branch" />
      <path d="M670 51q-27-27-39 1 19 14 39-1m53 27q9-31 29-13-3 19-29 13" class="scene-leaf" />
      <path d="M0 28q83-8 132-28M666 0q29 40 94 38" class="scene-eaves" />
    </svg>
  </div>
</template>

<script setup>
import CavePet from './CavePet.vue'
defineProps({
  mode: { type: String, default: 'morning' },
  companion: { type: String, default: '' },
  waitingPlaces: { type: Number, default: 0 },
  focusing: { type: Boolean, default: false },
})
</script>

<style scoped>
.cave-scene { --wall: #edf2ee; --sky: #d9e9df; --mountain: #87aa99; --far: #b3c9bc; --floor: #dce6dd; --stone: #b1beb0; --wood: #7c8e79; width: 100%; height: 214px; overflow: hidden; border-radius: 36% 36% 12px 12px / 15% 15% 12px 12px; }
.cave-scene > svg { width: 100%; height: 100%; display: block; }
.scene-wall { fill: var(--wall); }.scene-window { fill: var(--sky); }.scene-sun { fill: #f5e0a7; }
.scene-mountain { fill: var(--mountain); }.scene-mountain--far { fill: var(--far); }.scene-mist { fill: none; stroke: var(--sky); stroke-width: 10; opacity: .65; }
.scene-stone { fill: none; stroke: var(--stone); stroke-width: 12; }.scene-floor { fill: var(--floor); }.scene-floor-line { stroke: var(--stone); opacity: .55; }
.scene-mat { fill: #bcc5a3; }.scene-mat-ring { fill: none; stroke: #919f7a; stroke-width: 2; }
.scene-robe { fill: #6c9f8b; }.scene-robe-fold { stroke: #487967; stroke-width: 2; fill: none; }.scene-arms { stroke: #b9d0bc; stroke-width: 9; stroke-linecap: round; fill: none; }
.scene-skin { fill: #e1c4a3; }.scene-hair { fill: #344b42; }.scene-face { stroke: #344b42; stroke-width: 2; fill: none; stroke-linecap: round; }
.scene-wood { fill: var(--wood); }.scene-table-legs { stroke: var(--wood); stroke-width: 7; }.scene-paper { fill: #f9f7e8; }.scene-ink { stroke: #789484; stroke-width: 1.5; }
.scene-lamp-base { fill: none; stroke: #97794c; stroke-width: 4; }.scene-lantern { fill: #d9b86d; }.scene-flame { fill: #fff0b3; animation: lamplight 4s ease-in-out infinite; }
.scene-sign-sticks { stroke: #b5a17a; stroke-width: 4; }
.scene-branch { stroke: #7c9276; stroke-width: 4; fill: none; }.scene-leaf { fill: #87a084; }.scene-eaves { stroke: #9daa98; stroke-width: 14; fill: none; }
.cave-scene--day { --wall: #e8f0e9; --sky: #c8e6db; --mountain: #729f89; --far: #9fbfad; }
.cave-scene--dusk { --wall: #eee8da; --sky: #eed3ae; --mountain: #959d87; --far: #c2b99f; --floor: #dfdfcb; }
.cave-scene--night { --wall: #263e47; --sky: #1d3543; --mountain: #3c6169; --far: #2d4d5e; --floor: #334b4c; --stone: #48615e; --wood: #617369; }
.cave-scene--night .scene-sun { fill: #e5e6cc; }.cave-scene--night .scene-lantern { fill: #e6b85d; }.cave-scene--night .scene-mist { opacity: .2; }.cave-scene--night .scene-branch,.cave-scene--night .scene-eaves { opacity: .5; }
@keyframes lamplight { 50% { opacity: .65; } }
@media (min-width: 1000px) { .cave-scene { height: 360px; border-radius: 150px 150px 16px 16px; } }
@media (prefers-reduced-motion: reduce) { .scene-flame { animation: none; } }
</style>
