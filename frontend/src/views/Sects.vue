<template>
  <div class="sects-page">
    <header><p class="cultivation-eyebrow">宗门对比</p><h1>宗门选择</h1><p>比较传承、任务偏好与入门条件。</p></header>
    <section class="sects-filters cultivation-surface" aria-labelledby="sect-filter-title">
      <div class="cultivation-section-heading"><h2 id="sect-filter-title">比较筛选</h2><span>{{ sects.length }} 个结果</span></div>
      <div class="sects-filter-grid">
        <label>星级<select v-model="filters.star" @change="load"><option :value="null">全部星级</option><option v-for="star in 9" :key="star" :value="star">{{ star }} 星</option></select></label>
        <label>类型<select v-model="filters.kind" @change="load"><option :value="null">普通与特殊</option><option value="normal">普通</option><option value="special">特殊</option><option value="hidden">隐藏</option></select></label>
        <label>任务偏好<select v-model="filters.task_preference" @change="load"><option :value="null">全部偏好</option><option v-for="option in taskPreferenceOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
      </div>
    </section>
    <div v-if="loading" class="cultivation-state">正在读取宗门...</div>
    <div v-else-if="error" class="cultivation-state cultivation-state--error" role="alert"><span>{{ error }}</span><button type="button" class="cultivation-action" @click="load">重试</button></div>
    <div v-if="actionFeedback" class="cultivation-state cultivation-state--action" role="alert" aria-live="polite">{{ actionFeedback }}</div>
    <p v-if="!loading && !error && !actionFeedback && !sects.length" class="cultivation-state">暂无符合条件的宗门。</p>
    <section v-if="!loading && !error && sects.length" class="sect-list" aria-label="宗门比较结果">
      <article v-for="sect in sects" :key="sect.id || sect.sect_key" class="sect-card cultivation-surface" :class="{ 'sect-card--special': sect.kind === 'special' }">
        <div class="sect-card__heading"><div><span class="sect-card__legacy-icon" aria-hidden="true">{{ sect.kind === 'special' ? '✦' : '◈' }}</span><h2>{{ sect.name || '未揭示宗门' }}</h2></div><span>{{ sect.star }} 星</span></div>
        <dl class="sect-card__details"><div><dt>类型</dt><dd>{{ kindLabel(sect) }}</dd></div><div><dt>核心传承</dt><dd>{{ sect.core_legacy || (sect.visible === false ? '现身后揭示' : '传承资料待服务器返回') }}</dd></div><div><dt>任务偏好</dt><dd>{{ taskPreferenceLabel(sect) }}</dd></div><div><dt>入门境界</dt><dd>{{ entryRealmLabel(sect) }}</dd></div><div><dt>试炼状态</dt><dd>{{ trialStatusLabel(sect) }}</dd></div></dl>
        <div class="sect-card__actions"><span v-if="sect.joined" role="status">已加入</span><span v-else>{{ eligibilityMessage(sect) }}</span><div v-if="!sect.joined" class="sect-card__action-group"><button type="button" class="cultivation-action" :aria-disabled="busyId !== null || sect.visible !== true || sect.realm_confirmed !== true || sect.messenger_contacted === true" @click="contactMessenger(sect)">{{ busyId === sect.sect_key ? '处理中...' : sect.messenger_contacted ? '已联系使者' : '联系使者' }}</button><button type="button" class="cultivation-action" :aria-disabled="busyId !== null || sect.visible !== true || sect.messenger_contacted !== true || sect.trial_confirmed === true" @click="completeTrial(sect)">{{ sect.trial_confirmed ? '试炼已完成' : accessFor(sect) ? '提交试炼' : '查看试炼' }}</button><button type="button" class="cultivation-action" :aria-disabled="busyId !== null || sect.joined || sect.visible !== true || sect.can_join !== true" @click="join(sect)">{{ busyId === sect.sect_key ? '确认中...' : '加入宗门' }}</button></div></div>
        <section v-if="activeTrialSectKey === sect.sect_key && accessFor(sect)" class="sect-trial" aria-label="宗门试炼目标">
          <div class="sect-trial__heading"><strong>入门试炼目标</strong><span>{{ trialProgressLabel(accessFor(sect)) }}</span></div>
          <ol class="sect-trial__objectives">
            <li v-for="(objective, objectiveKey) in accessFor(sect).objectives" :key="objectiveKey" :class="{ 'sect-trial__objective--done': objective.completed }">
              <span><strong>{{ objective.label || objectiveKey }}</strong><small>{{ objective.required ? '必需目标' : '可选目标' }}</small></span>
              <button v-if="!objective.completed" type="button" class="cultivation-action cultivation-action--compact" :aria-disabled="busyId !== null" @click="markTrialObjective(sect, objectiveKey)">{{ busyId === sect.sect_key ? '处理中...' : '标记完成' }}</button>
              <span v-else class="sect-trial__done" role="status">已完成</span>
            </li>
          </ol>
        </section>
      </article>
    </section>
    <section class="sect-npc-section cultivation-surface" aria-labelledby="sect-npc-title">
      <div class="cultivation-section-heading"><div><p class="cultivation-eyebrow">人物关系</p><h2 id="sect-npc-title">已接触宗门的人物</h2></div><router-link to="/npcs" class="cultivation-action">查看人物关系</router-link></div>
      <p v-if="!recentlyMet.length" class="cultivation-fixed-state">暂无已接触的人物记录。</p>
      <ul v-else class="sect-npc-list">
        <li v-for="npc in recentlyMet" :key="npc.id" class="sect-npc-item">
          <div><strong>{{ npc.name }}</strong><span>{{ sectNameForNpc(npc) }}</span></div>
          <span>{{ npcRoleLabel(npc) }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { cultivationService } from '../services/cultivation'
import { createSequencedRequest } from './sects-request-state'
import { getErrorMessage } from '../utils/errorMessage'
import { labelFromServer, labelNpcRole, labelRealm, labelSectKind, labelStatus, labelTaskPreference } from '../utils/displayLabels'

const filters = reactive({ star: null, kind: null, task_preference: null })
const taskPreferenceOptions = Array.from({ length: 10 }, (_, index) => {
  const value = `discipline-${index + 1}`
  return { value, label: labelTaskPreference(value) }
})
const sects = ref([]); const loading = ref(false); const error = ref(null); const actionFeedback = ref(null); const busyId = ref(null)
const accessBySect = ref({}); const activeTrialSectKey = ref(null)
const relationship = ref({ recently_met: [] })
const recentlyMet = computed(() => relationship.value?.recently_met || [])
const requestSequence = createSequencedRequest({
  onStart: () => { loading.value = true; error.value = null; actionFeedback.value = null },
  onSuccess: ([response, npcResponse]) => {
    sects.value = Array.isArray(response) ? response : []
    relationship.value = npcResponse || { recently_met: [] }
  },
  onError: (requestError) => { error.value = getErrorMessage(requestError) },
  onFinish: () => { loading.value = false },
})
function load() {
  return requestSequence(() => Promise.all([
    cultivationService.getSects(filters),
    cultivationService.getNpcs(),
  ]))
}
function kindLabel(sect) { return labelFromServer(sect, 'kind_label', sect?.kind, labelSectKind) }
function taskPreferenceLabel(sect) { return labelFromServer(sect, 'task_preference_label', sect?.task_preference, labelTaskPreference) }
function entryRealmLabel(sect) { return labelFromServer(sect, 'entry_realm_label', sect?.entry_realm, labelRealm) }
function trialStatusLabel(sect) { return labelFromServer(sect, 'trial_status_label', sect?.trial_status, labelStatus) }
function npcRoleLabel(npc) { return labelFromServer(npc, 'role_label', npc?.role, () => npc?.role ? labelNpcRole(npc.role) : '普通弟子') }
function eligibilityMessage(sect) { if (sect.visible !== true) return sect.lock_reason ? getErrorMessage({ response: { data: { detail: sect.lock_reason } } }, '隐藏宗门尚未现身。') : '隐藏宗门尚未现身'; if (sect.realm_confirmed !== true) return '境界不足，暂不可推进'; if (sect.messenger_contacted !== true) return '请先联系使者'; if (sect.trial_confirmed !== true) return '请完成入门试炼'; return sect.realm_confirmed === true && sect.can_join === true ? '入门条件已满足' : '等待服务器确认' }
function sectNameForNpc(npc) { return sects.value.find((sect) => sect.id === npc.sect_id)?.name || '已接触宗门' }
function applySectState(result) { sects.value = sects.value.map((item) => item.sect_key === result.sect_key ? { ...item, ...result } : item) }
function explainBlocked(message) { actionFeedback.value = message; activeTrialSectKey.value = null }
function blockedReason(sect, action) {
  if (busyId.value) return '已有其他宗门操作正在处理中，请等待完成后再试。'
  if (sect.visible !== true) return getErrorMessage({ response: { data: { detail: sect.lock_reason || 'HIDDEN_SECT_LOCKED' } } }, '隐藏宗门尚未现身。')
  if (action === 'contact' && sect.realm_confirmed !== true) return `境界不足，需要达到${entryRealmLabel(sect)}后再联系使者。`
  if (action === 'contact' && sect.messenger_contacted === true) return '已经联系过这位使者。'
  if (action === 'trial' && sect.messenger_contacted !== true) return '请先联系使者，再查看入门试炼。'
  if (action === 'trial' && sect.trial_confirmed === true) return '入门试炼已经完成。'
  if (action === 'join' && sect.joined) return '你已经加入该宗门。'
  if (action === 'join' && sect.can_join !== true) return eligibilityMessage(sect)
  return '当前条件尚未满足，请刷新后再试。'
}
function accessFor(sect) { return accessBySect.value[sect.sect_key] || null }
function trialProgressLabel(access) {
  const objectives = Object.values(access?.objectives || {})
  const completed = objectives.filter((objective) => objective.completed).length
  return `${completed}/${objectives.length} 项已完成`
}
async function contactMessenger(sect) {
  if (busyId.value || sect.visible !== true || sect.realm_confirmed !== true || sect.messenger_contacted === true) {
    explainBlocked(blockedReason(sect, 'contact'))
    return
  }
  await mutate(sect, () => cultivationService.contactSectMessenger(sect.sect_key))
}
async function loadTrialAccess(sect) {
  busyId.value = sect.sect_key
  actionFeedback.value = null
  try {
    const access = await cultivationService.getSectAccess(sect.sect_key)
    accessBySect.value = { ...accessBySect.value, [sect.sect_key]: access }
    activeTrialSectKey.value = sect.sect_key
    if (!Object.values(access.objectives || {}).some((objective) => objective.required && !objective.completed)) {
      actionFeedback.value = '试炼目标已满足，可以提交入门试炼。'
    } else {
      actionFeedback.value = '请完成下方必需目标，再提交入门试炼。'
    }
  } catch (requestError) {
    actionFeedback.value = getErrorMessage(requestError)
  } finally {
    busyId.value = null
  }
}
async function completeTrial(sect) {
  if (busyId.value || sect.visible !== true || sect.messenger_contacted !== true || sect.trial_confirmed === true) {
    explainBlocked(blockedReason(sect, 'trial'))
    return
  }
  if (!accessFor(sect)) {
    await loadTrialAccess(sect)
    return
  }
  const unmet = Object.entries(accessFor(sect).objectives || {}).filter(([, objective]) => objective.required && !objective.completed)
  if (unmet.length) {
    explainBlocked(`还有${unmet.length}项必需试炼目标未完成，请先标记完成。`)
    activeTrialSectKey.value = sect.sect_key
    return
  }
  await mutate(sect, () => cultivationService.completeSectTrial(sect.sect_key))
}
async function markTrialObjective(sect, objectiveKey) {
  if (busyId.value) {
    explainBlocked('已有宗门操作正在处理中，请等待完成后再试。')
    return
  }
  busyId.value = sect.sect_key
  actionFeedback.value = null
  try {
    const access = await cultivationService.updateTrialObjective(sect.sect_key, objectiveKey, true)
    accessBySect.value = { ...accessBySect.value, [sect.sect_key]: access }
    activeTrialSectKey.value = sect.sect_key
    actionFeedback.value = '试炼目标进度已更新。'
  } catch (requestError) {
    actionFeedback.value = getErrorMessage(requestError)
  } finally {
    busyId.value = null
  }
}
async function mutate(sect, action) {
  busyId.value = sect.sect_key
  actionFeedback.value = null
  try {
    applySectState(await action())
    actionFeedback.value = '宗门状态已更新。'
  } catch (requestError) {
    actionFeedback.value = getErrorMessage(requestError)
  } finally {
    busyId.value = null
  }
}
async function join(sect) {
  if (busyId.value || sect.joined || sect.visible !== true || sect.can_join !== true) {
    explainBlocked(blockedReason(sect, 'join'))
    return
  }
  busyId.value = sect.sect_key
  actionFeedback.value = null
  try {
    const result = await cultivationService.joinSect(sect.id || sect.sect_key)
    sects.value = sects.value.map((item) => ({ ...item, joined: item.sect_key === result.sect_key }))
    actionFeedback.value = '已加入宗门。'
  } catch (requestError) {
    actionFeedback.value = getErrorMessage(requestError)
  } finally {
    busyId.value = null
  }
}
onMounted(load)
</script>

<style scoped>
.sects-page,.sect-list{display:grid;gap:var(--page-gap)}header h1{margin:4px 0}header p:not(.cultivation-eyebrow){margin:0;color:var(--color-text-secondary)}.cultivation-eyebrow{margin:0;color:var(--color-primary-dark);font-size:11px;font-weight:800;letter-spacing:.14em}.cultivation-surface{display:grid;gap:var(--spacing-md);padding:var(--surface-padding);border:1px solid var(--color-border);border-radius:var(--surface-radius);background:var(--color-card);box-shadow:var(--shadow-sm)}.sects-filter-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--spacing-md)}label{display:grid;gap:6px;font-size:var(--font-size-sm);font-weight:700}select,input{min-height:var(--touch-target-min);padding:8px;border:1px solid var(--color-border);border-radius:var(--radius-md);background:var(--color-card);color:var(--color-text)}.sect-card{border-left:4px solid var(--color-border)}.sect-card--special{border-left-color:var(--color-primary)}.sect-card__heading,.sect-card__heading>div,.sect-card__actions{display:flex;align-items:center;justify-content:space-between;gap:12px}.sect-card__heading h2{display:inline;margin:0;font-size:1.1rem}.sect-card__legacy-icon{display:inline-grid;place-items:center;width:28px;height:28px;margin-right:8px;border:1px solid var(--color-border-strong);border-radius:50%}.sect-card__details{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0}.sect-card__details div{padding-top:8px;border-top:1px solid var(--color-border)}dt{color:var(--color-text-secondary);font-size:var(--font-size-sm)}dd{margin:3px 0 0;font-weight:700}.sect-card__action-group{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}.cultivation-action[aria-disabled="true"]{opacity:.64}.cultivation-state--action{border-color:var(--color-warning);color:var(--color-text)}.sect-trial{display:grid;gap:10px;padding:12px;border-top:1px solid var(--color-border);background:var(--color-bg-secondary)}.sect-trial__heading,.sect-trial__objectives li{display:flex;align-items:center;justify-content:space-between;gap:12px}.sect-trial__heading span,.sect-trial__objectives small{color:var(--color-text-secondary);font-size:var(--font-size-sm)}.sect-trial__objectives{display:grid;gap:8px;margin:0;padding:0;list-style:none}.sect-trial__objectives li{padding:10px;border:1px solid var(--color-border);background:var(--color-card)}.sect-trial__objectives li>span:first-child{display:grid;gap:3px}.sect-trial__objective--done{border-color:var(--color-success)!important}.sect-trial__done{color:var(--color-success);font-weight:700}.cultivation-action--compact{padding:6px 10px;font-size:var(--font-size-sm)}.sect-npc-section{margin-top:var(--page-gap)}.sect-npc-list{display:grid;gap:10px;margin:0;padding:0;list-style:none}.sect-npc-item{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px;border:1px solid var(--color-border);border-radius:var(--radius-md)}.sect-npc-item div{display:grid;gap:4px}.sect-npc-item span{color:var(--color-text-secondary);font-size:var(--font-size-sm)}@media(max-width:767px){.sects-filter-grid,.sect-card__details{grid-template-columns:1fr}.sect-card__actions{align-items:stretch;flex-direction:column}.sect-card__action-group{flex-direction:column}.sect-card__actions .cultivation-action{width:100%}.sect-trial__heading,.sect-trial__objectives li{align-items:flex-start;flex-direction:column}.sect-trial .cultivation-action{width:100%}.sect-npc-item{align-items:flex-start;flex-direction:column}}
</style>
