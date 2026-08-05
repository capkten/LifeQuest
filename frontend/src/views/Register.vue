<template>
  <div class="register-container">
    <section class="register-brand" aria-label="LifeQuest 产品介绍">
      <span class="auth-eyebrow">START YOUR NEXT CHAPTER</span>
      <div class="auth-brand-mark" aria-hidden="true">
        <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M24 5v38M5 24h38" opacity="0.28" />
          <circle cx="24" cy="24" r="15" />
          <path d="M24 14v20M14 24h20" />
        </svg>
      </div>
      <h2>从一个小目标开始，建立自己的节奏。</h2>
      <p>记录行动，获得反馈，再把每一次完成变成下一次出发的动力。</p>
      <div class="register-brand-points">
        <span><i></i>任务与目标一处管理</span>
        <span><i></i>完成后获得真实奖励</span>
      </div>
    </section>
    <div class="register-card">
      <div class="register-header">
        <h1 class="register-title">LifeQuest</h1>
        <p class="register-subtitle">创建新账号</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="register-form"
        @submit.prevent="handleRegister"
      >
        <el-form-item prop="username" label="用户名">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            aria-label="用户名"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="email" label="邮箱">
          <el-input
            v-model="form.email"
            type="email"
            placeholder="邮箱"
            aria-label="邮箱"
            size="large"
            prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item prop="password" label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            aria-label="密码"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item prop="confirmPassword" label="确认密码">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="确认密码"
            aria-label="确认密码"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="register-button"
            :loading="loading"
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-footer">
        <p>
          已有账号？
          <router-link to="/login" class="login-link">
            立即登录
          </router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

async function handleRegister() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.register({
      username: form.username,
      email: form.email,
      password: form.password
    })
    ElMessage.success('注册成功，请登录')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  background:
    radial-gradient(circle at 18% 20%, rgba(14, 165, 233, 0.2), transparent 30%),
    radial-gradient(circle at 82% 78%, rgba(16, 185, 129, 0.12), transparent 28%),
    var(--color-bg);
  padding: max(var(--spacing-xl), var(--safe-area-top)) var(--spacing-xl) max(var(--spacing-xl), var(--safe-area-bottom));
}

.register-brand {
  display: flex;
  flex: 0 1 480px;
  flex-direction: column;
  justify-content: center;
  min-height: 480px;
  padding: 40px;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 28px;
  background:
    radial-gradient(circle at 90% 10%, rgba(110, 231, 183, 0.35), transparent 28%),
    linear-gradient(145deg, #123b5d 0%, #0a6c94 58%, #0ea5e9 100%);
  color: #fff;
  box-shadow: var(--shadow-xl);
}

.register-brand .auth-eyebrow {
  margin-bottom: 30px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

.register-brand .auth-brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin-bottom: 22px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.12);
  color: #a7f3d0;
}

.register-brand .auth-brand-mark svg {
  width: 38px;
  height: 38px;
}

.register-brand h2 {
  max-width: 360px;
  color: #fff;
  font-family: var(--font-family-display);
  font-size: clamp(1.7rem, 1.35rem + 0.7vw, 2.3rem);
  line-height: 1.12;
}

.register-brand > p {
  max-width: 350px;
  margin-top: 14px;
  color: rgba(255, 255, 255, 0.76);
  font-size: var(--font-size-sm);
  line-height: 1.7;
}

.register-brand-points {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 30px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 11px;
}

.register-brand-points span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.register-brand-points i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6ee7b7;
  box-shadow: 0 0 0 4px rgba(110, 231, 183, 0.12);
}

.register-card {
  background: var(--color-card);
  border-radius: var(--surface-radius);
  padding: var(--spacing-2xl);
  width: 100%;
  max-width: 420px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.register-header {
  text-align: center;
  margin-bottom: var(--spacing-2xl);
}

.register-title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: var(--spacing-sm);
}

.register-subtitle {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
}

.register-form {
  margin-bottom: var(--spacing-lg);
}

.register-button {
  width: 100%;
  min-height: var(--touch-target-min);
  height: auto;
  font-size: var(--font-size-lg);
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  border-color: transparent;
}

.register-footer {
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.login-link {
  color: var(--color-primary);
  font-weight: 500;
}

.login-link:hover {
  color: var(--color-primary-light);
  text-decoration: underline;
}

@media (max-width: 899px) {
  .register-brand {
    display: none;
  }
}

@media (max-width: 767px) {
  .register-container {
    align-items: flex-start;
    padding: calc(var(--spacing-md) + var(--safe-area-top)) var(--spacing-md) calc(var(--spacing-md) + var(--safe-area-bottom));
  }

  .register-card {
    margin-top: 8vh;
    padding: var(--spacing-xl);
    border-radius: var(--surface-radius-sm);
  }
}
</style>
