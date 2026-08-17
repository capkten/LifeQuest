<template>
  <div class="sects-page">
    <header class="sects-page__header">
      <div><p class="cultivation-eyebrow">SECT COMPARISON</p><h1>宗门选择</h1><p>比较传承、任务偏好与入门条件。</p></div>
    </header>

    <section class="sects-filters cultivation-surface" aria-labelledby="sect-filter-title">
      <div class="cultivation-section-heading"><h2 id="sect-filter-title">比较筛选</h2><span>{{ filteredSects.length }} 个结果</span></div>
      <div class="sects-filter-grid">
        <label>星级<select v-model="filters.star" @change="load"><option :value="null">全部星级</option><option v-for="star in 9" :key="star" :value="star">{{ star }} 星</option></select></label>
        <label>类型<select v-model="filters.kind" @change="load"><option :value="null">普通与特殊</option><option value="normal">普通</option><option value="special">特殊</option><option value="hidden">隐藏</option></select></label>
        <label>任务偏好<input v-model.trim="filters.task_preference" placeholder="例如 discipline-1" @change="load"></label>
      </div>
    </section>

    <div v-if="loading" class="cultivation-state">正在读取宗门...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert"><span>{{ errorMessage }}</span><button type="button" class="cultivation-action" @click="load">重试</button></div>
    <p v-else-if="!filteredSects.length" class="cultivation-state">暂无符合条件的宗门。</p>
    <section v-else class="sect-list" aria-label="宗门比较结果">
      <article v-for="sect in filteredSects" :key="sect.id || sect.sect_key" class="sect-card cultivation-surface" :class="{ 'sect-card--special': sect.kind === 'special' }">
        <div class="sect-card__heading"><div><span class="sect-card__legacy-icon" aria-hidden="true">{{ sect.kind === 'special' ? '✦' : '◈' }}</span><h2>{{ sect.name }}</h2></div><span class="sect-card__star">{{ sect.star }} 星</span></div>
        <dl class="sect-card__details"><div><dt>类型</dt><dd>{{ kindLabel(sect.kind) }}</dd></div><div><dt>核心传承</dt><dd>{{ sect.core_legacy || '传承资料待服务器返回' }}</dd></div><div><dt>固定 NPC</dt><dd>{{ fixedNpcs(sect).join('、') }}</dd></div><div><dt>任务偏好</dt><dd>{{ sect.task_preference || '未设定' }}</dd></div><div><dt>入门境界</dt><dd>{{ sect.entry_realm || '服务器确认' }}</dd></div><div><dt>试炼条件</dt><dd>{{ trialLabel(sect) }}</dd></div></dl>
        <div class="sect-card__actions"><span v-if="sect.joined" class="sect-card__joined" role="status">已加入</span><span v-else class="sect-card__eligibility">{{ eligibilityMessage(sect) }}</span><button type="button" class="cultivation-action" :disabled="busyId === sect.sect_key || sect.joined || !canJoin(sect)" @click="join(sect)">{{ busyId === sect.sect_key ? '确认中...' : '加入宗门' }}</button></div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { cultivationService } from '../services/cultivation'

const filters = reactive({ star: null, kind: null, task_preference: null })
const sects = ref([]); const loading = ref(false); const error = ref(null); const busyId = ref(null)
const filteredSects = computed(() => sects.value.filter((sect) => filters.task_preference ? sect.task_preference === filters.task_preference : true).filter((sect) => filters.kind !== 'hidden' || sect.visible === true))
const errorMessage = computed(() => error.value?.response?.data?.detail || error.value?.message || '宗门暂时无法读取。')

async function load() { loading.value = true; error.value = null; try { const response = await cultivationService.getSects(filters); sects.value = Array.isArray(response) ? response.filter((sect) => sect.kind !== 'hidden' || sect.visible === true) : [] } catch (requestError) { error.value = requestError } finally { loading.value = false } }
function kindLabel(kind) { return ({ normal: '普通', special: '特殊', hidden: '隐藏' })[kind] || kind || '未知' }
function fixedNpcs(sect) { return (sect.fixed_npcs || sect.npcs || [sect.sect_master, sect.transmission_elder, sect.trial_envoy]).filter(Boolean).slice(0, 3).map((npc) => typeof npc === 'string' ? npc : npc.name).filter(Boolean).concat(['宗主', '传功长老', '试炼使者']).slice(0, 3) }
function trialLabel(sect) { return sect.trial_confirmed === true || sect.trial_available === true ? '已满足' : sect.trial_condition || '等待服务器确认' }
function canJoin(sect) { return sect.can_join === true && sect.realm_confirmed === true && sect.messenger_contacted === true && (sect.trial_confirmed === true || sect.trial_available === true) }
function eligibilityMessage(sect) { return canJoin(sect) ? '境界、使者接触与试炼条件已确认' : '等待服务器确认境界、使者接触与试炼条件' }
async function join(sect) { if (!canJoin(sect)) return; busyId.value = sect.sect_key; error.value = null; try { const result = await cultivationService.joinSect(sect.id || sect.sect_key); sects.value = sects.value.map((item) => ({ ...item, joined: item.sect_key === result.sect_key })) } catch (requestError) { error.value = requestError } finally { busyId.value = null } }
onMounted(load)
</script>

<style scoped>
.sects-page,.sect-list{display:grid;gap:var(--page-gap)}.sects-page__header h1{margin:4px 0;font-family:var(--font-family-display)}.sects-page__header p:not(.cultivation-eyebrow){margin:0;color:var(--color-text-secondary)}.cultivation-eyebrow{margin:0;color:var(--color-primary-dark);font-size:11px;font-weight:800;letter-spacing:.14em}.cultivation-surface{display:grid;gap:var(--spacing-md);padding:var(--surface-padding);border:1px solid var(--color-border);border-radius:var(--surface-radius);background:var(--color-card);box-shadow:var(--shadow-sm)}.sects-filter-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--spacing-md)}label{display:grid;gap:6px;color:var(--color-text-secondary);font-size:var(--font-size-sm);font-weight:700}select,input{min-height:var(--touch-target-min);padding:8px;border:1px solid var(--color-border);border-radius:var(--radius-md);background:var(--color-card);color:var(--color-text)}.sect-card{border-left:4px solid var(--color-border)}.sect-card--special{border-left-color:var(--color-primary)}.sect-card__heading,.sect-card__heading>div,.sect-card__actions{display:flex;align-items:center;justify-content:space-between;gap:12px}.sect-card__heading h2{display:inline;margin:0;font-size:1.1rem}.sect-card__legacy-icon{display:inline-grid;place-items:center;width:28px;height:28px;margin-right:8px;border:1px solid var(--color-border-strong);border-radius:50%;color:var(--color-primary-dark)}.sect-card__star{font-weight:800;color:var(--color-primary-dark)}.sect-card__details{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0}.sect-card__details div{padding-top:8px;border-top:1px solid var(--color-border)}dt{color:var(--color-text-secondary);font-size:var(--font-size-sm)}dd{margin:3px 0 0;font-weight:700}.sect-card__eligibility{color:var(--color-text-secondary);font-size:var(--font-size-sm)}.sect-card__joined{color:var(--color-success-dark);font-weight:800}@media(max-width:767px){.sects-filter-grid,.sect-card__details{grid-template-columns:1fr}.sect-card__actions{align-items:stretch;flex-direction:column}.sect-card__actions .cultivation-action{width:100%}}
</style>
