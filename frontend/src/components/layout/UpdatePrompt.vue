<template>
  <Teleport to="body">
    <div v-if="update" class="update-overlay" role="dialog" aria-modal="true" aria-labelledby="update-title">
      <section class="update-dialog">
        <p class="update-eyebrow">LifeQuest 更新</p>
        <h2 id="update-title">发现新版本 {{ update.versionName }}</h2>
        <p class="update-copy">{{ update.releaseNotes }}</p>
        <div class="update-actions">
          <button v-if="!update.forceUpdate" type="button" class="update-secondary" @click="dismissUpdate">稍后再说</button>
          <button type="button" class="update-primary" @click="openDownload">立即更新</button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted } from 'vue'
import { Browser } from '@capacitor/browser'
import { useAppUpdate } from '../../composables/useAppUpdate'

const { update, checkForUpdate, dismissUpdate } = useAppUpdate()

async function openDownload() {
  if (update.value?.downloadUrl) await Browser.open({ url: update.value.downloadUrl })
}

onMounted(checkForUpdate)
</script>

<style scoped>
.update-overlay { position: fixed; inset: 0; z-index: 3000; display: grid; place-items: center; padding: 20px; background: rgba(15, 23, 42, .42); }
.update-dialog { width: min(100%, 420px); padding: 24px; border: 1px solid var(--color-border); border-radius: var(--radius-xl); background: var(--color-card); box-shadow: var(--shadow-xl); }
.update-eyebrow { margin: 0 0 6px; color: var(--color-primary-dark); font-size: var(--font-size-xs); font-weight: 700; letter-spacing: .08em; }
.update-dialog h2 { margin: 0; color: var(--color-text); font-size: var(--font-size-xl); }
.update-copy { margin: 12px 0 20px; color: var(--color-text-secondary); }
.update-actions { display: flex; justify-content: flex-end; gap: 8px; }
.update-actions button { min-height: var(--touch-target-min); padding: 10px 16px; border-radius: var(--radius-md); border: 1px solid transparent; font: inherit; font-weight: 700; cursor: pointer; }
.update-primary { background: var(--color-primary); color: #fff; }
.update-secondary { border-color: var(--color-border); background: var(--color-card); color: var(--color-text-secondary); }
</style>
