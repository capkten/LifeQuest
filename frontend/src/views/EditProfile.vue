<template>
  <div class="edit-profile-page">
    <h1 class="page-title">编辑资料</h1>

    <div class="edit-profile-card">
      <!-- Avatar section -->
      <div class="avatar-section">
        <div class="avatar-wrapper" @click="triggerFileInput" :class="{ 'avatar-loading': avatarUploading }">
          <img v-if="avatarPreview || serverAvatarSrc" :src="avatarPreview || serverAvatarSrc" alt="用户头像" class="avatar-img" />
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="avatar-placeholder">
            <circle cx="12" cy="8" r="4" />
            <path d="M20 21a8 8 0 1 0-16 0" />
          </svg>
          <div class="avatar-overlay">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            <span>点击更换头像</span>
          </div>
          <div v-if="avatarUploading" class="avatar-spinner"></div>
        </div>
        <input ref="fileInput" type="file" accept="image/*" class="file-input" @change="handleAvatarChange" />
      </div>

      <!-- Form fields -->
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
            placeholder="请输入邮箱"
          />
        </div>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <button class="btn btn-cancel" @click="goBack">取消</button>
        <button class="btn btn-save" @click="handleSave" :disabled="saving">
          <span v-if="saving" class="btn-spinner"></span>
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <!-- Toasts -->
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

  // Validate file type
  if (!file.type.startsWith('image/')) {
    showError('请选择图片文件')
    return
  }

  // Validate file size (max 5MB)
  if (file.size > 5 * 1024 * 1024) {
    showError('图片大小不能超过 5MB')
    return
  }

  // Show preview immediately
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
    // Reset file input so the same file can be selected again
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

  // Basic email validation
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
    const message = err.response?.data?.detail || '更新失败，请重试'
    showError(message)
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
  padding: var(--spacing-xl);
  max-width: 600px;
  margin: 0 auto;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 var(--spacing-xl) 0;
}

.edit-profile-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--spacing-xl);
}

/* Avatar */
.avatar-section {
  display: flex;
  justify-content: center;
  margin-bottom: var(--spacing-xl);
}

.avatar-wrapper {
  width: 120px;
  height: 120px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  position: relative;
  cursor: pointer;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 60px;
  height: 60px;
  color: #fff;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.avatar-overlay svg {
  width: 24px;
  height: 24px;
  color: #fff;
}

.avatar-overlay span {
  font-size: var(--font-size-xs);
  color: #fff;
  white-space: nowrap;
}

.avatar-spinner {
  position: absolute;
  inset: 0;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: var(--radius-full);
  animation: spin 0.8s linear infinite;
}

.avatar-loading {
  pointer-events: none;
}

.file-input {
  display: none;
}

/* Form */
.form-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.form-input {
  padding: var(--spacing-md);
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  color: var(--color-text);
  outline: none;
  transition: border-color 0.2s ease;
}

.form-input:focus {
  border-color: var(--color-primary);
}

.form-input::placeholder {
  color: var(--color-text-tertiary);
}

/* Actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}

.btn {
  padding: var(--spacing-md) var(--spacing-xl);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
  border-color: var(--color-border);
}

.btn-cancel:hover:not(:disabled) {
  background: var(--color-border);
}

.btn-save {
  background: var(--color-primary);
  color: #fff;
}

.btn-save:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: var(--radius-full);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Toasts */
.toast {
  position: fixed;
  top: var(--spacing-xl);
  left: 50%;
  transform: translateX(-50%);
  padding: var(--spacing-md) var(--spacing-xl);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  z-index: 1000;
  animation: slideDown 0.3s ease;
}

.toast-success {
  background: var(--color-success);
  color: #fff;
}

.toast-error {
  background: var(--color-error);
  color: #fff;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

/* Responsive */
@media (max-width: 767px) {
  .edit-profile-page {
    padding: var(--spacing-md);
  }

  .edit-profile-card {
    padding: var(--spacing-lg);
  }

  .avatar-wrapper {
    width: 100px;
    height: 100px;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
