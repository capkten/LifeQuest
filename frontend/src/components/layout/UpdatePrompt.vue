<template>
  <Teleport to="body">
    <div v-if="update" class="update-overlay" role="dialog" aria-modal="true" aria-labelledby="update-title">
      <section class="update-dialog">
        <p class="update-eyebrow">LifeQuest 更新</p>
        <h2 id="update-title">发现新版本 {{ update.versionName }}</h2>
        <p class="update-copy">{{ update.releaseNotes }}</p>
        <p v-if="updateError" class="update-error" role="alert">{{ updateError }}</p>
        <div v-if="downloading || downloadStatus === 'installing'" class="update-progress" aria-live="polite">
          <div
            class="update-progress-track"
            role="progressbar"
            :aria-valuenow="downloadProgress"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="downloadProgress > 0 ? `下载进度 ${downloadProgress}%` : '正在连接下载服务'"
          >
            <span :style="{ width: `${downloadProgress}%` }"></span>
          </div>
          <p class="update-progress-label">
            {{ downloadStatus === 'installing' ? '下载完成，正在准备安装...' : downloadProgress > 0 ? `下载进度 ${downloadProgress}%` : '正在连接下载服务...' }}
          </p>
        </div>
        <div class="update-actions">
          <button v-if="!update.forceUpdate" type="button" class="update-secondary" @click="dismissUpdate">稍后再说</button>
          <button type="button" class="update-primary" :disabled="downloading || downloadStatus === 'installing'" @click="startUpdate">
            {{ downloadStatus === 'installing' ? '正在安装...' : downloading ? '正在下载...' : '立即更新' }}
          </button>
        </div>
        <button type="button" class="update-github" @click="openGithubDownload">打开 GitHub 下载</button>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted } from 'vue'
import { registerPlugin } from '@capacitor/core'
import { useAppUpdate } from '../../composables/useAppUpdate'

const AppUpdater = registerPlugin('AppUpdater')
const {
  update,
  checkForUpdate,
  dismissUpdate,
  downloading,
  downloadProgress,
  downloadStatus,
  updateError,
  startUpdate,
  openGithubDownload,
} = useAppUpdate(AppUpdater)

onMounted(checkForUpdate)
</script>

<style scoped>
.update-overlay { position: fixed; inset: 0; z-index: 3000; display: grid; place-items: center; padding: 20px; background: rgba(15, 23, 42, .42); }
.update-dialog { width: min(100%, 420px); padding: 24px; border: 1px solid var(--color-border); border-radius: var(--radius-xl); background: var(--color-card); box-shadow: var(--shadow-xl); }
.update-eyebrow { margin: 0 0 6px; color: var(--color-primary-dark); font-size: var(--font-size-xs); font-weight: 700; letter-spacing: .08em; }
.update-dialog h2 { margin: 0; color: var(--color-text); font-size: var(--font-size-xl); }
.update-copy { margin: 12px 0 20px; color: var(--color-text-secondary); }
.update-error { margin: 0 0 16px; color: var(--color-danger, #dc2626); font-size: var(--font-size-sm); }
.update-progress { margin: 0 0 20px; }
.update-progress-track { overflow: hidden; height: 8px; border-radius: 999px; background: var(--color-bg-tertiary); }
.update-progress-track span { display: block; height: 100%; border-radius: inherit; background: var(--color-primary); transition: width 220ms ease; }
.update-progress-label { margin: 8px 0 0; color: var(--color-text-secondary); font-size: var(--font-size-sm); }
.update-actions { display: flex; justify-content: flex-end; gap: 8px; }
.update-actions button { min-height: var(--touch-target-min); padding: 10px 16px; border-radius: var(--radius-md); border: 1px solid transparent; font: inherit; font-weight: 700; cursor: pointer; }
.update-actions button:disabled { opacity: .6; cursor: wait; }
.update-primary { background: var(--color-primary); color: #fff; }
.update-secondary { border-color: var(--color-border); background: var(--color-card); color: var(--color-text-secondary); }
.update-github { display: block; width: 100%; margin-top: 12px; padding: 8px 0; border: 0; background: transparent; color: var(--color-primary-dark); font: inherit; font-size: var(--font-size-sm); font-weight: 700; cursor: pointer; }
</style>
