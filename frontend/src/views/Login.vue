<template>
  <div class="login-container">
    <section class="login-brand" aria-label="LifeQuest 产品介绍">
      <span class="auth-eyebrow">PERSONAL PROGRESS SYSTEM</span>
      <div class="auth-brand-mark" aria-hidden="true">
        <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M24 5v38M5 24h38" opacity="0.28" />
          <circle cx="24" cy="24" r="15" />
          <path d="m17 25 5 5 10-12" />
        </svg>
      </div>
      <h2>把生活拆成可完成的下一步。</h2>
      <p>用任务、目标和奖励，把每天的微小进步积累成自己的长期节奏。</p>
      <div class="auth-momentum">
        <div class="auth-momentum-head">
          <span>今日行动力</span>
          <strong>+12 XP</strong>
        </div>
        <div class="auth-momentum-bar"><span></span></div>
        <div class="auth-momentum-foot">
          <span>持续前进</span>
          <span>生活 · 目标 · 奖励</span>
        </div>
      </div>
      <div class="auth-feature-list">
        <span><i></i>让计划变得更轻</span>
        <span><i></i>让完成值得被奖励</span>
      </div>
    </section>
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">LifeQuest</h1>
        <p class="login-subtitle">生活冒险家</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-button"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <p>
          还没有账号？
          <router-link to="/register" class="register-link">
            立即注册
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
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 个字符', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.login(form)
    ElMessage.success('登录成功')
  } catch (error) {
    ElMessage.error(
      error.response
        ? `[${error.response.status}] ${error.response.data?.detail || JSON.stringify(error.response.data)}`
        : `[Network] ${error.message} | API: ${import.meta.env.VITE_API_BASE_URL || '/api'}`
    )
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  background:
    radial-gradient(circle at 18% 20%, rgba(14, 165, 233, 0.2), transparent 30%),
    radial-gradient(circle at 82% 78%, rgba(16, 185, 129, 0.12), transparent 28%),
    var(--color-bg);
  padding: var(--spacing-xl);
}

.login-brand {
  display: flex;
  flex: 0 1 480px;
  flex-direction: column;
  justify-content: center;
  min-height: 480px;
  padding: 40px;
  overflow: hidden;
  position: relative;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 28px;
  background:
    radial-gradient(circle at 90% 10%, rgba(110, 231, 183, 0.35), transparent 28%),
    linear-gradient(145deg, #123b5d 0%, #0a6c94 58%, #0ea5e9 100%);
  color: #fff;
  box-shadow: var(--shadow-xl);
}

.login-brand::after {
  content: '';
  width: 220px;
  height: 220px;
  position: absolute;
  right: -100px;
  bottom: -110px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  box-shadow: 0 0 0 18px rgba(255, 255, 255, 0.04), 0 0 0 38px rgba(255, 255, 255, 0.03);
}

.auth-eyebrow {
  margin-bottom: 30px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

.auth-brand-mark {
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

.auth-brand-mark svg {
  width: 38px;
  height: 38px;
}

.login-brand h2 {
  max-width: 360px;
  color: #fff;
  font-family: var(--font-family-display);
  font-size: clamp(1.7rem, 1.35rem + 0.7vw, 2.3rem);
  line-height: 1.12;
}

.login-brand > p {
  max-width: 350px;
  margin-top: 14px;
  color: rgba(255, 255, 255, 0.76);
  font-size: var(--font-size-sm);
  line-height: 1.7;
}

.auth-momentum {
  max-width: 350px;
  margin-top: 30px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 16px;
  background: rgba(7, 40, 66, 0.24);
}

.auth-momentum-head,
.auth-momentum-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.auth-momentum-head {
  color: rgba(255, 255, 255, 0.76);
  font-size: var(--font-size-xs);
}

.auth-momentum-head strong {
  color: #a7f3d0;
  font-family: var(--font-family-display);
  font-size: var(--font-size-lg);
}

.auth-momentum-bar {
  height: 6px;
  margin: 13px 0 10px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
}

.auth-momentum-bar span {
  display: block;
  width: 68%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6ee7b7, #38bdf8);
}

.auth-momentum-foot {
  color: rgba(255, 255, 255, 0.56);
  font-size: 10px;
}

.auth-feature-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 18px;
  margin-top: 22px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 11px;
}

.auth-feature-list span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.auth-feature-list i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6ee7b7;
  box-shadow: 0 0 0 4px rgba(110, 231, 183, 0.12);
}

.login-card {
  background: var(--color-card);
  border-radius: 20px;
  padding: var(--spacing-2xl);
  width: 100%;
  max-width: 420px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.login-header {
  text-align: center;
  margin-bottom: var(--spacing-2xl);
}

.login-title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: var(--spacing-sm);
}

.login-subtitle {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
}

.login-form {
  margin-bottom: var(--spacing-lg);
}

.login-button {
  width: 100%;
  height: 48px;
  font-size: var(--font-size-lg);
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  border-color: transparent;
}

.login-footer {
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.register-link {
  color: var(--color-primary);
  font-weight: 500;
}

.register-link:hover {
  color: var(--color-primary-light);
  text-decoration: underline;
}

@media (max-width: 899px) {
  .login-brand {
    display: none;
  }

  .login-card {
    max-width: 420px;
  }
}

@media (max-width: 767px) {
  .login-container {
    padding: var(--spacing-md);
  }

  .login-card {
    padding: var(--spacing-xl);
    border-radius: 18px;
  }
}
</style>
