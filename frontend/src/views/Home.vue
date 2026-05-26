<template>
  <div class="home-container">
    <header class="home-header">
      <h1>LifeQuest</h1>
      <div class="user-info">
        <span v-if="authStore.user">{{ authStore.user.username }}</span>
        <el-button type="danger" @click="handleLogout">退出登录</el-button>
      </div>
    </header>
    <main class="home-main">
      <h2>欢迎回来，冒险家！</h2>
      <p>准备好开始今天的冒险了吗？</p>
    </main>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  padding: var(--spacing-xl);
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-2xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.home-header h1 {
  color: var(--color-primary);
  font-size: var(--font-size-2xl);
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  color: var(--color-text-secondary);
}

.home-main {
  text-align: center;
  padding-top: var(--spacing-2xl);
}

.home-main h2 {
  font-size: var(--font-size-2xl);
  margin-bottom: var(--spacing-md);
  color: var(--color-text);
}

.home-main p {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
}
</style>
