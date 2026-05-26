<template>
  <div class="app-layout">
    <Sidebar />
    <div class="app-main">
      <Header :title="pageTitle" />
      <main class="app-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const route = useRoute()

const pageTitle = computed(() => {
  const titles = {
    Home: 'Home',
    Tasks: 'Tasks',
    Goals: 'Goals',
    Notes: 'Notes',
    Shop: 'Shop',
    Backpack: 'Backpack',
    Profile: 'Profile'
  }
  return titles[route.name] || 'LifeQuest'
})
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.app-main {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
}

.app-content {
  flex: 1;
  overflow-y: auto;
}
</style>
