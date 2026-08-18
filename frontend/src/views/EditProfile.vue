<template>
  <div class="edit-profile-page">
    <section class="profile-shell">
      <div class="profile-intro">
        <span class="profile-kicker">PROFILE SETTINGS</span>
        <h1 class="page-title">编辑资料</h1>
        <p class="page-copy">更新头像、用户名与邮箱信息，保留现有头像解析、上传和资料保存行为。</p>
      </div>

      <div class="profile-layout">
        <aside class="profile-preview">
          <div
            class="avatar-wrapper"
            @click="triggerFileInput"
            :class="{ 'avatar-loading': avatarUploading }"
            role="button"
            tabindex="0"
            @keydown.enter.prevent="triggerFileInput"
            @keydown.space.prevent="triggerFileInput"
          >
            <img
              v-if="avatarPreview || serverAvatarSrc"
              :src="avatarPreview || serverAvatarSrc"
              alt="用户头像"
              class="avatar-img"
            />
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="avatar-placeholder" aria-hidden="true">
              <circle cx="12" cy="8" r="4" />
              <path d="M20 21a8 8 0 1 0-16 0" />
            </svg>
            <div class="avatar-overlay">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
              <span>点击更换头像</span>
            </div>
            <div v-if="avatarUploading" class="avatar-spinner"></div>
          </div>

          <input ref="fileInput" type="file" accept="image/*" class="file-input" @change="handleAvatarChange" />

          <div class="preview-meta">
            <h2>{{ formData.username || user?.username || '未命名用户' }}</h2>
            <p>{{ formData.email || user?.email || '未设置邮箱' }}</p>
            <div class="preview-pills">
              <span class="preview-pill">支持头像实时预览</span>
              <span class="preview-pill">最大 5MB 图片</span>
            </div>
          </div>
        </aside>

        <section class="form-card">
          <div class="section-heading">
            <div>
              <span class="section-kicker">ACCOUNT INFO</span>
              <h2>基础信息</h2>
            </div>
            <button class="text-button" type="button" @click="goBack">返回资料页</button>
          </div>

          <div class="form-section">
            <div class="form-group">
              <label class="form-label" for="username">用户名</label>
              <input
                id="username"
                v-model="formData.username"
                type="text"
                class="form-input"
                placeholder="请输入用户名"
                maxlength="50"
              />
            </div>

            <div class="form-group">
              <label class="form-label" for="email">邮箱</label>
              <input
                id="email"
                v-model="formData.email"
                type="email"
                class="form-input"
                inputmode="email"
                placeholder="请输入邮箱"
              />
            </div>
          </div>

          <div class="tips-grid">
            <article class="tip-card">
              <span class="tip-card-label">头像</span>
              <p>上传后会立即调用现有接口，并在当前页面显示解析后的头像地址。</p>
            </article>
            <article class="tip-card">
              <span class="tip-card-label">保存</span>
              <p>保存按钮继续沿用原有资料更新逻辑，不更改 API 入参与错误提示来源。</p>
            </article>
          </div>

          <div class="form-actions">
            <button class="btn btn-cancel" type="button" @click="goBack">取消</button>
            <button class="btn btn-save" type="button" @click="handleSave" :disabled="saving">
              <span v-if="saving" class="btn-spinner"></span>
              {{ saving ? '保存中...' : '保存资料' }}
            </button>
          </div>
        </section>
      </div>
    </section>

    <div v-if="successToast" class="toast toast-success">{{ successToast }}</div>
    <div v-if="errorToast" class="toast toast-error">{{ errorToast }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { authService } from '../services/auth'
import { useToast } from '../composables/useToast'
import { useResolvedImage } from '../composables/useResolvedImage'
import { getErrorMessage } from '../utils/errorMessage'

const router = useRouter()
const authStore = useAuthStore()
const { successToast, errorToast, showSuccess, showError } = useToast()

const user = computed(() => authStore.user)
const fileInput = ref(null)
const avatarPreview = ref(null)
const avatarUploading = ref(false)
const serverAvatarSrc = useResolvedImage(computed(() => user.value?.avatar))
const saving = ref(false)

const formData = reactive({
  username: '',
  email: ''
})

onMounted(() => {
  if (authStore.user) {
    formData.username = authStore.user.username || ''
    formData.email = authStore.user.email || ''
  }
})

function triggerFileInput() {
  if (avatarUploading.value) return
  fileInput.value?.click()
}

async function handleAvatarChange(event) {
  const file = event.target.files?.[0]
  if (!file) return

  if (!file.type.startsWith('image/')) {
    showError('请选择图片文件')
    return
  }

  if (file.size > 5 * 1024 * 1024) {
    showError('图片大小不能超过 5MB')
    return
  }

  avatarPreview.value = URL.createObjectURL(file)

  avatarUploading.value = true
  try {
    await authService.uploadAvatar(file)
    await authStore.fetchUser()
    showSuccess('头像上传成功')
  } catch (err) {
    showError('头像上传失败，请重试')
    avatarPreview.value = null
  } finally {
    avatarUploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function handleSave() {
  if (!formData.username.trim()) {
    showError('用户名不能为空')
    return
  }

  if (!formData.email.trim()) {
    showError('邮箱不能为空')
    return
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(formData.email)) {
    showError('请输入有效的邮箱地址')
    return
  }

  saving.value = true
  try {
    await authService.updateProfile({
      username: formData.username.trim(),
      email: formData.email.trim()
    })
    await authStore.fetchUser()
    showSuccess('资料更新成功')
    setTimeout(() => {
      router.push({ name: 'Profile' })
    }, 1000)
  } catch (err) {
    showError(getErrorMessage(err))
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push({ name: 'Profile' })
}
</script>

<style scoped>
.edit-profile-page {
  padding: var(--page-padding-y) var(--page-padding-x);
}

.profile-shell {
  display: grid;
  gap: 18px;
}

.profile-intro,
.profile-preview,
.form-card {
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  background: var(--color-card);
  box-shadow: var(--shadow-sm);
}

.profile-intro {
  padding: var(--surface-padding);
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.18), transparent 28%),
    linear-gradient(135deg, #ffffff 0%, #edf7fb 100%);
}

.profile-kicker,
.section-kicker {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--color-primary-dark);
}

.page-title,
.section-heading h2,
.preview-meta h2 {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-family-display);
}

.page-title {
  margin-top: 8px;
  font-size: clamp(1.75rem, 2vw, 2.4rem);
}

.page-copy {
  margin: 10px 0 0;
  max-width: 620px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.profile-layout {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
  gap: 16px;
}

.profile-preview,
.form-card {
  padding: var(--surface-padding);
}

.profile-preview {
  display: grid;
  gap: 18px;
  align-content: start;
}

.avatar-wrapper {
  width: min(100%, 220px);
  aspect-ratio: 1;
  margin: 0 auto;
  border-radius: 32px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  position: relative;
  cursor: pointer;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  outline: none;
}

.avatar-wrapper:focus-visible {
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.18);
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 72px;
  height: 72px;
  color: #fff;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.56);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  opacity: 0;
  transition: opacity 0.2s ease;
  color: #fff;
  text-align: center;
  padding: 16px;
}

.avatar-wrapper:hover .avatar-overlay,
.avatar-wrapper:focus-visible .avatar-overlay {
  opacity: 1;
}

.avatar-overlay svg {
  width: 24px;
  height: 24px;
}

.avatar-spinner {
  position: absolute;
  inset: 0;
  border: 3px solid rgba(255, 255, 255, 0.25);
  border-top-color: #fff;
  border-radius: inherit;
  animation: spin 0.8s linear infinite;
}

.avatar-loading {
  pointer-events: none;
}

.file-input {
  display: none;
}

.preview-meta {
  display: grid;
  gap: 8px;
  text-align: center;
}

.preview-meta p {
  margin: 0;
  color: var(--color-text-secondary);
}

.preview-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.preview-pill {
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  background: rgba(14, 165, 233, 0.1);
  color: var(--color-primary-dark);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.form-card {
  display: grid;
  gap: 18px;
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
}

.text-button {
  min-height: 40px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(14, 165, 233, 0.15);
  background: transparent;
  color: var(--color-primary-dark);
  cursor: pointer;
  font-weight: 700;
}

.form-section {
  display: grid;
  gap: 16px;
}

.form-group {
  display: grid;
  gap: 8px;
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text);
}

.form-input {
  min-height: 48px;
  padding: 0 16px;
  border-radius: 16px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  color: var(--color-text);
  font: inherit;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.12);
}

.tips-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.tip-card {
  padding: 16px;
  border-radius: 18px;
  background: var(--color-bg-secondary);
  border: 1px solid rgba(14, 165, 233, 0.08);
}

.tip-card-label {
  display: block;
  margin-bottom: 8px;
  color: var(--color-primary-dark);
  font-size: var(--font-size-xs);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.tip-card p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
  font-size: var(--font-size-sm);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn {
  min-height: 46px;
  padding: 0 20px;
  border-radius: 14px;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 700;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: var(--color-bg-secondary);
  border-color: var(--color-border);
  color: var(--color-text);
}

.btn-save {
  background: var(--color-primary);
  color: #fff;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.toast {
  position: fixed;
  top: var(--spacing-lg);
  left: 50%;
  transform: translateX(-50%);
  min-height: 44px;
  padding: 0 18px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: #fff;
  z-index: 1000;
  box-shadow: var(--shadow-lg);
}

.toast-success {
  background: var(--color-success);
}

.toast-error {
  background: var(--color-error);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1023px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }

  .tips-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .edit-profile-page {
    padding: var(--spacing-md);
  }

  .profile-intro,
  .profile-preview,
  .form-card {
    border-radius: 22px;
  }

  .section-heading,
  .form-actions {
    grid-template-columns: 1fr;
    display: grid;
  }

  .btn,
  .text-button {
    width: 100%;
  }

  .toast {
    left: var(--spacing-md);
    right: var(--spacing-md);
    transform: none;
  }
}

@media (min-width: 768px) {
  .edit-profile-page {
    padding: 0;
  }
}
</style>
