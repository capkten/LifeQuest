<template>
  <div class="sects-page">
    <header><p class="cultivation-eyebrow">SECT COMPARISON</p><h1>宗门选择</h1><p>比较传承、任务偏好与入门条件。</p></header>
    <section class="sects-filters cultivation-surface" aria-labelledby="sect-filter-title">
      <div class="cultivation-section-heading"><h2 id="sect-filter-title">比较筛选</h2><span>{{ sects.length }} 个结果</span></div>
      <div class="sects-filter-grid">
        <label>星级<select v-model="filters.star" @change="load"><option :value="null">全部星级</option><option v-for="star in 9" :key="star" :value="star">{{ star }} 星</option></select></label>
        <label>类型<select v-model="filters.kind" @change="load"><option :value="null">普通与特殊</option><option value="normal">普通</option><option value="special">特殊</option></select></label>
        <label>任务偏好<input v-model.trim="filters.task_preference" placeholder="例如 discipline-1" @change="load"></label>
      </div>
    </section>
    <div v-if="loading" class="cultivation-state">正在读取宗门...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert"><span>{{ errorMessage() }}</span><button type="button" class="cultivation-action" @click="load">重试</button></div>
    <p v-else-if="!sects.length" class="cultivation-state">暂无符合条件的宗门。</p>
    <section v-else class="sect-list" aria-label="宗门比较结果">
      <article v-for="sect in sects" :key="sect.id || sect.sect_key" class="sect-card cultivation-surface" :class="{ 'sect-card--special': sect.kind === 'special' }">
        <div class="sect-card__heading"><div><span class="sect-card__legacy-icon" aria-hidden="true">{{ sect.kind === 'special' ? '✦' : '◈' }}</span><h2>{{ sect.name }}</h2></div><span>{{ sect.star }} 星</span></div>
        <dl class="sect-card__details"><div><dt>类型</dt><dd>{{ kindLabel(sect.kind) }}</dd></div><div><dt>核心传承</dt><dd>{{ sect.core_legacy || '传承资料待服务器返回' }}</dd></div><div><dt>任务偏好</dt><dd>{{ sect.task_preference || '未设定' }}</dd></div><div><dt>入门境界</dt><dd>{{ sect.entry_realm || '服务器确认' }}</dd></div><div><dt>试炼状态</dt><dd>{{ sect.trial_status || '等待服务器确认' }}</dd></div></dl>
        <div class="sect-card__actions"><span v-if="sect.joined" role="status">已加入</span><span v-else>{{ eligibilityMessage(sect) }}</span><div v-if="!sect.joined" class="sect-card__action-group"><button type="button" class="cultivation-action" :disabled="busyId === sect.sect_key || sect.visible !== true || sect.realm_confirmed !== true || sect.messenger_contacted === true" @click="contactMessenger(sect)">{{ busyId === sect.sect_key ? '处理中...' : sect.messenger_contacted ? '已联系使者' : '联系使者' }}</button><button type="button" class="cultivation-action" :disabled="busyId === sect.sect_key || sect.visible !== true || sect.messenger_contacted !== true || sect.trial_confirmed === true" @click="completeTrial(sect)">{{ sect.trial_confirmed ? '试炼已完成' : '完成试炼' }}</button><button type="button" class="cultivation-action" :disabled="busyId === sect.sect_key || sect.joined || sect.visible !== true || sect.can_join !== true" @click="join(sect)">{{ busyId === sect.sect_key ? '确认中...' : '加入宗门' }}</button></div></div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { cultivationService } from '../services/cultivation'

const filters = reactive({ star: null, kind: null, task_preference: null })
const sects = ref([]); const loading = ref(false); const error = ref(null); const busyId = ref(null)
const errorMessage = () => error.value?.response?.data?.detail || error.value?.message || '宗门暂时无法读取。'
async function load() { loading.value = true; error.value = null; try { const response = await cultivationService.getSects(filters); sects.value = Array.isArray(response) ? response.filter((sect) => sect.visible === true) : [] } catch (requestError) { error.value = requestError } finally { loading.value = false } }
function kindLabel(kind) { return ({ normal: '普通', special: '特殊', hidden: '隐藏' })[kind] || kind || '未知' }
function eligibilityMessage(sect) { if (sect.realm_confirmed !== true) return '境界不足，暂不可推进'; if (sect.messenger_contacted !== true) return '请先联系使者'; if (sect.trial_confirmed !== true) return '请完成入门试炼'; return sect.realm_confirmed === true && sect.can_join === true ? '入门条件已满足' : '等待服务器确认' }
function applySectState(result) { sects.value = sects.value.map((item) => item.sect_key === result.sect_key ? { ...item, ...result } : item) }
async function contactMessenger(sect) { if (sect.visible !== true || sect.realm_confirmed !== true || sect.messenger_contacted === true) return; await mutate(sect, () => cultivationService.contactSectMessenger(sect.sect_key)) }
async function completeTrial(sect) { if (sect.visible !== true || sect.messenger_contacted !== true || sect.trial_confirmed === true) return; await mutate(sect, () => cultivationService.completeSectTrial(sect.sect_key)) }
async function mutate(sect, action) { busyId.value = sect.sect_key; error.value = null; try { applySectState(await action()) } catch (requestError) { error.value = requestError } finally { busyId.value = null } }
async function join(sect) { if (sect.can_join !== true || sect.visible !== true) return; busyId.value = sect.sect_key; error.value = null; try { const result = await cultivationService.joinSect(sect.id || sect.sect_key); sects.value = sects.value.map((item) => ({ ...item, joined: item.sect_key === result.sect_key })) } catch (requestError) { error.value = requestError } finally { busyId.value = null } }
onMounted(load)
</script>

<style scoped>
.sects-page,.sect-list{display:grid;gap:var(--page-gap)}header h1{margin:4px 0}header p:not(.cultivation-eyebrow){margin:0;color:var(--color-text-secondary)}.cultivation-eyebrow{margin:0;color:var(--color-primary-dark);font-size:11px;font-weight:800;letter-spacing:.14em}.cultivation-surface{display:grid;gap:var(--spacing-md);padding:var(--surface-padding);border:1px solid var(--color-border);border-radius:var(--surface-radius);background:var(--color-card);box-shadow:var(--shadow-sm)}.sects-filter-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--spacing-md)}label{display:grid;gap:6px;font-size:var(--font-size-sm);font-weight:700}select,input{min-height:var(--touch-target-min);padding:8px;border:1px solid var(--color-border);border-radius:var(--radius-md);background:var(--color-card);color:var(--color-text)}.sect-card{border-left:4px solid var(--color-border)}.sect-card--special{border-left-color:var(--color-primary)}.sect-card__heading,.sect-card__heading>div,.sect-card__actions{display:flex;align-items:center;justify-content:space-between;gap:12px}.sect-card__heading h2{display:inline;margin:0;font-size:1.1rem}.sect-card__legacy-icon{display:inline-grid;place-items:center;width:28px;height:28px;margin-right:8px;border:1px solid var(--color-border-strong);border-radius:50%}.sect-card__details{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0}.sect-card__details div{padding-top:8px;border-top:1px solid var(--color-border)}dt{color:var(--color-text-secondary);font-size:var(--font-size-sm)}dd{margin:3px 0 0;font-weight:700}.sect-card__action-group{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}@media(max-width:767px){.sects-filter-grid,.sect-card__details{grid-template-columns:1fr}.sect-card__actions{align-items:stretch;flex-direction:column}.sect-card__action-group{flex-direction:column}.sect-card__actions .cultivation-action{width:100%}}
</style>
