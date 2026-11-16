<template>
  <section class="cave-page companions-page">
    <header class="companions-heading"><div><h1>伙伴</h1><p class="cave-muted">山中不只有你一个人。</p></div><nav aria-label="成长导航"><router-link to="/cave/growth" class="cave-link">成长</router-link><router-link to="/cave/codex" class="cave-link">图鉴</router-link></nav></header>
    <p v-if="companionsLoading && !companions" role="status">正在寻一寻同行者…</p>
    <div v-if="companionsError" role="alert"><p>{{ companionsError }}</p><button type="button" class="cave-link" @click="cave.loadCompanions()">重试</button></div>
    <template v-if="companions">
      <article class="dao-child"><span class="xiaoman-mark" aria-hidden="true">满</span><div><h2>小满</h2><p>{{ companions.dao_child.lines.at(-1) || '灯已点好，等你落座。' }}</p><p class="cave-muted">默契 {{ companions.dao_child.familiarity }} / 5 · 只添新话，不添数值加成。</p></div></article>
      <div class="companion-pets">
        <article v-for="pet in companions.pets" :key="pet.key" class="companion-pet" :class="{ 'companion-pet--active': pet.active }">
          <div class="pet-picture"><CavePet :pet="pet.key" :silhouette="!pet.unlocked" /><span v-if="pet.active" class="pet-active">正在随行</span></div><h2>{{ pet.name }}</h2><p>{{ pet.unlocked ? pet.story : pet.hint }}</p><button type="button" :class="pet.unlocked ? 'cave-button' : 'cave-choice'" :aria-pressed="pet.active" :disabled="!pet.unlocked || pet.active || Boolean(companionPending)" @click="cave.activateCompanion(pet.key)">{{ companionPending === pet.key ? '正在相邀…' : !pet.unlocked ? '尚未解锁' : pet.active ? '正在随行' : '邀它随行' }}</button>
        </article>
      </div>
      <section class="companion-note" aria-label="今日山中见闻"><h2>山中见闻</h2><template v-if="companions.daily_note"><p>{{ companions.daily_note.story }}</p><span class="cave-muted">{{ companions.daily_note.companion_name }} · {{ companions.daily_note.date }}</span></template><p v-else class="cave-muted">邀请一位同行者，听它说一段山中的事。每天一则，只留下故事。</p></section>
      <section class="senior-companions" aria-label="同门"><article v-for="senior in companions.seniors" :key="senior.key"><span class="senior-seal" aria-hidden="true">{{ senior.key === 'qingheng' ? '蘅' : '锋' }}</span><div><h2>{{ senior.name }}</h2><p>{{ senior.unlocked ? '山中有人惦念你的近况。' : senior.hint }}</p></div></article></section>
    </template>
  </section>
</template>

<script setup>
import { inject, onMounted } from 'vue'
import CavePet from '../components/cave/CavePet.vue'
const cave = inject('cave')
const { companions, companionsLoading, companionsError, companionPending } = cave
onMounted(() => cave.loadCompanions())
</script>

<style scoped>
.companions-page { max-width: 1000px; margin: 0 auto; }.companions-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 24px; }.companions-heading h1 { font-family: SimSun, STSong, serif; font-size: 30px; letter-spacing: .08em; margin: 0; }.companions-heading p { margin: 10px 0 0; }.companions-heading nav { display: flex; gap: 8px; }.dao-child { display: flex; align-items: center; gap: 20px; padding: 24px; background: #edf2ee; border-radius: 20px 20px 20px 4px; }.dao-child h2 { font-family: SimSun, STSong, serif; font-size: 24px; font-weight: 500; margin: 0 0 12px; }.dao-child p { font-size: 14px; margin: 8px 0 0; }.xiaoman-mark { display: flex; align-items: center; justify-content: center; flex-shrink: 0; width: 56px; height: 72px; border-radius: 28px 28px 8px 8px; background: #d5e5d7; color: #397b67; font-family: SimSun, STSong, serif; font-size: 30px; }.companion-pets { display: grid; gap: 16px; margin: 24px 0; }.companion-pet { min-width: 0; display: flex; flex-direction: column; padding: 24px; border-radius: 12px; background: #f0f4f0; }.pet-picture { display: flex; justify-content: center; align-items: center; position: relative; min-height: 120px; }.pet-active { position: absolute; right: 0; top: 0; color: #397b67; font-size: 12px; }.companion-pet h2 { font-family: SimSun, STSong, serif; font-size: 24px; font-weight: 500; margin: 16px 0 12px; }.companion-pet p { flex: 1; color: #536d62; font-size: 14px; line-height: 1.8; margin: 0 0 20px; }.companion-pet button { width: 100%; }.companion-pet--active { background: #e4eee5; box-shadow: inset 0 2px 0 #397b67; }.companion-note { padding: 8px 4px 24px; }.companion-note h2 { font-family: SimSun, STSong, serif; font-size: 24px; font-weight: 500; }.companion-note p { font-size: 14px; line-height: 1.8; }.senior-companions { display: grid; gap: 16px; }.senior-companions article { display: flex; gap: 20px; align-items: center; padding: 20px; background: #edf2ee; border-radius: 12px; }.senior-companions h2 { font-size: 18px; font-weight: 500; margin: 0 0 8px; }.senior-companions p { font-size: 14px; color: #536d62; margin: 0; }.senior-seal { color: #8c9d8d; font-family: SimSun, STSong, serif; font-size: 32px; }@media(min-width:1000px) { .companion-pets { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px; }.senior-companions { grid-template-columns: repeat(2, minmax(0, 1fr)); }.dao-child { max-width: 700px; } }@media(max-width:390px) { .companions-heading { gap: 8px; }.companions-heading nav { gap: 0; }.dao-child { padding: 20px; gap: 16px; } }
</style>
