<template>
  <div class="cave-home" :class="[`cave-home--${mode}`, { 'cave-home--onboarding': onboarding?.status === 'pending' }]">
    <header class="cave-heading">
      <div class="cave-heading-title"><h1>洞府</h1><span>{{ dateText }} · {{ modeLabels[mode] }}</span></div>
      <button v-if="data?.fortune" type="button" class="fortune-button" @click="fortuneOpen = true" aria-haspopup="dialog">
        <span aria-hidden="true">✧</span> 今日签 <span class="fortune-name">{{ data.fortune.title }}</span>
      </button>
    </header>

    <aside v-if="cave.pendingReturn?.value" class="pending-return" aria-label="待查看的归来"><span>{{ cave.pendingReturn.value.status === 'ready' ? '入定已满，回来收功。' : '有一段时间，已替你收好。' }}</span><router-link :to="`/cave/return/${cave.pendingReturn.value.session_id}`" aria-label="查看归来">归来 <span aria-hidden="true">›</span></router-link></aside>
    <aside v-if="data?.unread_letters_count" class="pending-return pending-letters" aria-label="未拆的同门书信"><span>案上有 {{ data.unread_letters_count }} 封未拆的信。</span><router-link to="/cave/letters" aria-label="查看同门书信">拆信 <span aria-hidden="true">›</span></router-link></aside>

    <div class="cave-room">
      <section class="cave-room-scene" aria-label="今日洞府">
        <CaveScene :mode="mode" :focusing="Boolean(activeSession)" :companion="activePet?.key || ''" :waiting-places="waitingCompanions.length" />
        <div v-if="data?.companions" class="scene-companions"><span v-if="activePet">正在随行：{{ activePet.name }}</span><ul v-if="waitingCompanions.length" aria-label="待相逢的同行者"><li v-for="pet in waitingCompanions" :key="pet.key"><router-link to="/cave/companions">{{ pet.name }}</router-link></li></ul></div>
        <p v-if="data?.daily_note" class="home-pet-note">{{ data.daily_note.story }}</p>
        <button type="button" class="xiaoman-line" @click="anotherLine = !anotherLine" aria-label="小满，再说一句">
          <span class="xiaoman-name">小满</span><span>{{ anotherLine ? '先把眼前这一件做好。山里的风，我替你听。' : greeting }}</span>
        </button>
        <p class="cave-quiet-note">灯已点好，等你落座。</p>
      </section>

      <section class="cave-actions" aria-label="现在做">
        <div v-if="loading && !data" class="cave-loading" role="status"><span class="unlit-lamp" aria-hidden="true"></span>正在点灯…</div>
        <div v-if="loadError" class="cave-message" role="alert"><p>洞府的门暂时推不开。</p><button type="button" @click="cave.load()">重试</button></div>

        <article v-if="queuedSession" class="now-card" aria-live="polite"><h2>等待联网收功</h2><p>这段时间已保存在此设备，联网后再确认收获。</p><router-link class="cave-primary" :to="`/cave/return/${queuedSession.id}`">查看待收功</router-link></article>
        <article v-else-if="activeSession" class="now-card now-card--active" aria-live="polite">
          <span class="now-caption">入定中</span>
          <div class="cave-countdown metric-figure">{{ remainingText }}</div>
          <h2>{{ activeSession.todo_title || primarySign?.title || '静坐片刻' }}</h2>
          <p>时间在走，洞府替你守着。</p>
          <router-link class="cave-primary" :to="`/cave/session/${activeSession.id}`">回到入定</router-link>
        </article>
        <article v-else-if="primarySign" class="now-card">
          <span class="now-caption">现在做</span>
          <h2><router-link :to="{ path: '/todos', query: { tab: 'tasks', task_id: primarySign.id } }">{{ primarySign.title }}</router-link></h2>
          <p class="now-meta">{{ sourceText(primarySign.source) }}<span v-if="primarySign.deadline"> · {{ deadlineText(primarySign.deadline) }}</span></p>
          <div class="now-action-row">
            <button class="cave-primary" type="button" :disabled="Boolean(pendingAction) || offline" @click="beginSession">{{ pendingAction === 'start' ? '正在入定…' : `${ctaLabel} ${onboarding?.status === 'pending' ? 15 : selectedDuration} 分钟` }}</button>
            <button type="button" class="cave-text-button" :disabled="Boolean(pendingAction) || rerollUsed || offline" @click="cave.reroll()">{{ rerollUsed ? '今日已换签' : '换一签' }}</button>
          </div>
          <p class="now-footnote">{{ onboarding?.status === 'pending' ? '第一签已写好。从 15 分钟开始，照看这一件事。' : '一件事，一段安静的时间。' }}</p>
          <button v-if="onboarding?.status === 'pending'" type="button" class="cave-link" :disabled="Boolean(onboardingPending) || offline" @click="cave.skipOnboarding()">跳过引导</button>
        </article>
        <article v-else-if="staleCache" class="now-card"><h2>等联网，再取今日签</h2><p>上次的签已收好。还未连接，暂不知道今天有哪些事。</p><button type="button" class="cave-primary" @click="cave.load()">重新连接</button></article>
        <article v-else-if="data" class="now-card now-card--empty" :aria-label="onboarding?.status === 'pending' ? '初到洞府' : undefined">
          <p v-if="onboarding?.status === 'pending'" class="onboarding-introduction">我是小满，替你照看这一小处。</p>
          <span v-else class="now-caption">写下一件事</span>
          <h2>{{ onboarding?.status === 'pending' ? '最近最想推进的一件事？' : '起笔，就从这里。' }}</h2>
          <p>{{ onboarding?.status === 'pending' ? '不必想得很大。写下来，就会成为今天的一件真实任务。' : '今日无签。写下一件事，便是起笔。' }}</p>
          <form class="cave-quick-form" @submit.prevent="createTask">
            <label class="sr-only" for="cave-quick-task">你现在想推进的一件事</label>
            <input id="cave-quick-task" v-model="draftTitle" maxlength="200" autocomplete="off" placeholder="你现在想推进的一件事" :disabled="Boolean(pendingAction) || offline" />
            <button type="submit" class="cave-primary" :disabled="!draftTitle.trim() || Boolean(pendingAction) || offline">写好这一签</button>
          </form>
          <div class="cave-examples" aria-label="试着从这里开始">
            <button v-for="example in examples" :key="example" type="button" @click="draftTitle = example">{{ example }}</button>
          </div>
          <button v-if="onboarding?.status === 'pending'" type="button" class="cave-link" :disabled="Boolean(onboardingPending) || offline" @click="cave.skipOnboarding()">跳过引导</button>
        </article>
        <div v-if="signs?.length" class="cave-signs" role="group" aria-label="今日三签">
          <button v-for="(sign, index) in signs" :key="sign.id" type="button" :aria-pressed="index === 0" :disabled="Boolean(pendingAction) || offline" @click="cave.selectSign(sign.id)"><span>{{ index === 0 ? '主签' : '备签' }}</span><strong>{{ sign.title }}</strong></button>
        </div>
        <div v-if="data" class="signs-tools"><span v-if="data.all_signs_done">今日签已尽。</span><span v-else>想做别的事，也可以。</span><button type="button" class="cave-text-button" @click="openBucket">从签筒里选</button></div>
        <p v-if="actionError" class="cave-message" role="alert">{{ actionError }}</p>
        <p v-if="onboardingError" class="cave-message" role="alert">{{ onboardingError }}</p>
        <router-link v-if="data" to="/cave/growth" class="cave-growth-link"><span>山中修行，日有所进</span><span>去成长看看 <span aria-hidden="true">›</span></span></router-link>
      </section>
    </div>

    <el-drawer v-model="bucketOpen" title="签筒 · 今天就想做这件" direction="btt" size="75%" class="cave-bucket-drawer">
      <div class="bucket-content">
        <label for="cave-bucket-search">找一件未完成的事</label><input id="cave-bucket-search" v-model="bucketSearch" type="search" placeholder="搜索任务" />
        <label for="cave-bucket-project">项目</label><select id="cave-bucket-project" v-model="bucketProject"><option value="">全部项目</option><option value="__none">未分配项目</option><option v-for="project in bucketProjects" :key="project.id" :value="project.id">{{ project.name }}</option></select>
        <p v-if="bucketLoading" role="status">正在取签…</p>
        <div v-else-if="candidatesError" role="alert"><p>{{ candidatesError }}</p><button type="button" class="cave-text-button" @click="openBucket">重新取签</button></div>
        <p v-else-if="!filteredCandidates.length">这里暂时没有合适的签。也可以写下一件新事。</p>
        <button v-for="task in filteredCandidates" :key="task.id" type="button" class="bucket-task" :disabled="Boolean(pendingAction) || offline" @click="chooseSign(task.id)"><span>{{ task.title }}<small v-if="task.project_name">{{ task.project_name }}</small></span><span>设为主签</span></button>
        <p v-if="actionError" role="alert">{{ actionError }}</p>
      </div>
    </el-drawer>
    <el-dialog v-model="fortuneOpen" title="今日签" width="min(420px, calc(100vw - 32px))" align-center class="cave-fortune-dialog">
      <div v-if="data?.fortune" class="fortune-detail"><span class="fortune-mark" aria-hidden="true">签</span><h2>{{ data.fortune.title }}</h2><p>{{ data.fortune.text }}</p><p class="fortune-explanation">今日签在中国时间零点更新。每一签，都愿你慢慢做好眼前的事。</p><p v-if="data.fortune.multiplier > 1" class="fortune-explanation">当天首次有灵气的收功，基础入定修为加成 10%，额外部分向下取整。任务与奇遇奖励不重复加成。</p></div>
      <template #footer><button type="button" class="cave-primary" @click="fortuneOpen = false">收好今日签</button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import CaveScene from '../components/cave/CaveScene.vue'

const cave = inject('cave')
const { data, loading, loadError, actionError, pendingAction, draftTitle, selectedDuration, mode, greeting, ctaLabel, primarySign, activeSession, remainingSeconds, signs, rerollUsed, candidates, candidatesError, offline, pendingSettlements, staleCache, onboarding, onboardingPending, onboardingError } = cave
const queuedSession = computed(() => pendingSettlements.value.find(item => item.id === activeSession.value?.id))
const activePet = computed(() => data.value?.companions?.pets.find(pet => pet.active))
const waitingCompanions = computed(() => (data.value?.companions?.pets || []).filter(pet => !pet.unlocked).slice(0, 2))
const bucketOpen = ref(false)
const bucketLoading = ref(false)
const bucketSearch = ref('')
const bucketProject = ref('')
const bucketProjects = computed(() => [...new Map((candidates?.value || []).filter(task => task.project_id).map(task => [task.project_id, { id: task.project_id, name: task.project_name || '项目' }])).values()])
const filteredCandidates = computed(() => (candidates?.value || []).filter(task => task.title.toLocaleLowerCase().includes(bucketSearch.value.trim().toLocaleLowerCase()) && (!bucketProject.value || (bucketProject.value === '__none' ? !task.project_id : task.project_id === bucketProject.value))))
async function openBucket() {
  bucketOpen.value = true
  bucketLoading.value = true
  try { await cave.loadCandidates() } finally { bucketLoading.value = false }
}
async function chooseSign(id) {
  if (await cave.selectSign(id)) bucketOpen.value = false
}
const fortuneOpen = ref(false)
const anotherLine = ref(false)
const modeLabels = { morning: '晨', day: '昼', dusk: '昏', night: '夜' }
const examples = ['整理桌面 10 分钟', '读 5 页书', '写下今天最想推进的事']
const dateText = computed(() => data.value?.date ? `${Number(data.value.date.slice(5, 7))}月${Number(data.value.date.slice(8, 10))}日` : '今日')
const remainingText = computed(() => `${String(Math.floor(remainingSeconds.value / 60)).padStart(2, '0')}:${String(remainingSeconds.value % 60).padStart(2, '0')}`)

function sourceText(source) {
  return { overdue: '一桩待了结的事', today: '今天到期', in_progress: '正在进行', unscheduled: '未安排时间', upcoming: '稍后到期', 逾期: '一桩待了结的事' }[source] || source || '今日主签'
}
function deadlineText(value) {
  return new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`))
}
function beginSession() {
  if (onboarding.value?.status === 'pending') selectedDuration.value = 15
  cave.prepareSession()
}
async function createTask() {
  await cave.createTask()
}
onMounted(() => cave.load({ source: 'direct', recordOpen: true }))
</script>

<style scoped>
.cave-home { --cave-ink: #24443d; --cave-secondary: #536d62; --cave-accent: #397b67; color: var(--cave-ink); max-width: 1100px; margin: 0 auto; width: 100%; }
.cave-home--onboarding .scene-companions { display: none; }.onboarding-introduction { color: #397b67 !important; }.cave-home--onboarding .cave-room { gap: 12px; }@media(max-width:767px) { .cave-home--onboarding .xiaoman-line { display: none; }.cave-home--onboarding .cave-room-scene :deep(.cave-scene) { height: 140px; }.cave-home--onboarding .now-card { padding-top: 12px; padding-bottom: 12px; }.cave-home--onboarding .now-card > p { margin: 6px 0; }.cave-home--onboarding .cave-quick-form { margin-top: 12px; } }
.cave-home button, .cave-home input { font-family: inherit; }.cave-home button { cursor: pointer; }.cave-home button:disabled { cursor: default; opacity: .55; }.cave-home button:focus-visible,.cave-home a:focus-visible,.cave-home input:focus-visible { outline: 2px solid #3d8f78; outline-offset: 4px; }
.cave-heading { display: flex; justify-content: space-between; align-items: center; gap: 10px; min-height: 52px; margin-bottom: 14px; }.cave-heading-title { display: flex; align-items: baseline; gap: 14px; }.cave-heading h1 { font-family: 'Noto Serif SC', 'Songti SC', SimSun, STSong, serif; font-size: 26px; font-weight: 600; letter-spacing: .12em; margin: 0; }.cave-heading-title > span { font-size: 12px; color: var(--cave-secondary); white-space: nowrap; }
.fortune-button { display: flex; gap: 7px; align-items: center; min-height: 44px; border: 0; border-radius: 8px; background: #edf2ee; color: var(--cave-ink); font-size: 14px; padding: 8px 12px; }.fortune-button > span:first-child { color: #92651f; font-size: 20px; }.fortune-name { display: none; }
.cave-room { display: grid; gap: 20px; }.cave-room-scene { position: relative; min-width: 0; }.xiaoman-line { display: flex; align-items: baseline; gap: 12px; width: 100%; text-align: left; background: none; border: 0; color: var(--cave-ink); font-size: 14px; line-height: 1.65; min-height: 52px; padding: 12px 6px 0; }.xiaoman-name { flex-shrink: 0; font-family: 'Noto Serif SC', 'Songti SC', SimSun, STSong, serif; color: var(--cave-accent); }.xiaoman-line > span:last-child { max-width: 30em; }.cave-quiet-note { display: none; color: var(--cave-secondary); font-size: 14px; }
.scene-companions { display: flex; justify-content: flex-end; align-items: center; flex-wrap: wrap; gap: 6px 16px; margin: 8px 4px 0; font-size: 12px; color: var(--cave-secondary); }.scene-companions ul { display: flex; gap: 12px; list-style: none; margin: 0; padding: 0; }.scene-companions a { display: inline-flex; align-items: center; min-height: 44px; color: var(--cave-secondary); text-decoration: underline dotted; text-underline-offset: 4px; }.home-pet-note { font-size: 12px; color: var(--cave-secondary); line-height: 1.8; padding: 0 6px; }
.pending-return { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 44px; margin: -8px 0 8px; color: #536d62; font-size: 12px; }.pending-return a { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 8px 12px; color: #397b67; font-size: 14px; text-decoration: none; }
.cave-actions { min-width: 0; }.now-card { padding: 22px; background: #fff; border-radius: 16px; }.now-caption { color: var(--cave-accent); font-size: 14px; }.now-card h2 { font-family: 'Noto Serif SC', 'Songti SC', SimSun, STSong, serif; font-size: 25px; line-height: 1.45; font-weight: 600; margin: 10px 0 8px; overflow-wrap: anywhere; }.now-card h2 a { color: inherit; text-decoration: none; }.now-card h2 a:hover { text-decoration: underline; text-underline-offset: 5px; }.now-card > p { font-size: 14px; color: var(--cave-secondary); line-height: 1.6; }.now-meta { margin-bottom: 18px; }.now-action-row { display: flex; align-items: center; gap: 16px; }.cave-primary { display: inline-flex; align-items: center; justify-content: center; min-height: 48px; padding: 12px 24px; background: var(--cave-accent, #397b67); border: 0; border-radius: 10px; color: #fff; font-size: 16px; font-weight: 500; text-decoration: none; }.now-action-row .cave-primary { flex: 1; }.now-footnote { margin: 12px 0 0; font-size: 12px !important; }
.cave-growth-link { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 6px; font-size: 12px; min-height: 48px; align-items: center; color: var(--cave-secondary); text-decoration: none; padding: 12px 4px; }.cave-growth-link > span:last-child { color: var(--cave-accent); }.cave-countdown { font-variant-numeric: tabular-nums; font-size: 48px; font-weight: 500; margin-top: 8px; }.now-card--active .cave-primary { margin-top: 16px; width: 100%; }
.cave-text-button { background: none; border: 0; color: var(--cave-accent); font-size: 14px; min-height: 44px; padding: 8px 0; white-space: nowrap; }
.cave-signs { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: 14px; }.cave-signs button { border: 0; border-radius: 8px; background: #edf2ee; text-align: left; padding: 12px 10px; min-height: 70px; min-width: 0; color: var(--cave-ink); }.cave-signs button[aria-pressed="true"] { background: #e2eee5; box-shadow: inset 0 2px 0 #397b67; }.cave-signs button > span { display: block; font-size: 12px; color: var(--cave-secondary); margin-bottom: 5px; }.cave-signs strong { display: block; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }.signs-tools { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 44px; color: var(--cave-secondary); font-size: 12px; }
.bucket-content { display: grid; gap: 12px; max-width: 680px; margin: 0 auto; color: #24443d; }.bucket-content label { font-size: 14px; }.bucket-content input, .bucket-content select { min-height: 48px; font-size: 16px; border: 1px solid #bdcfc2; border-radius: 8px; background: #f7faf8; padding: 10px 12px; color: #24443d; width: 100%; box-sizing: border-box; }.bucket-content p { font-size: 14px; }.bucket-task { display: flex; align-items: center; justify-content: space-between; text-align: left; gap: 16px; padding: 14px 10px; min-height: 60px; border: 0; background: #edf2ee; border-radius: 8px; color: #24443d; font-family: inherit; font-size: 16px; cursor: pointer; }.bucket-task > span:first-child { min-width: 0; overflow-wrap: anywhere; }.bucket-task > span:last-child { font-size: 12px; color: #397b67; white-space: nowrap; }.bucket-task small { display: block; margin-top: 4px; font-size: 12px; }.bucket-content :focus-visible { outline: 2px solid #397b67; outline-offset: 3px; }
.cave-quick-form { display: grid; gap: 12px; margin-top: 18px; }.cave-quick-form input { box-sizing: border-box; min-width: 0; width: 100%; font-size: 16px; min-height: 48px; padding: 12px; color: var(--cave-ink); background: #f7faf8; border: 1px solid #bdcfc2; border-radius: 8px; }.cave-examples { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 8px; }.cave-examples button { min-height: 44px; background: none; border: 0; color: var(--cave-secondary); text-align: left; font-size: 12px; padding: 5px 0; }
.cave-message { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; color: var(--cave-secondary); font-size: 14px; padding: 10px 0; }.cave-message p { margin: 0; }.cave-message button { border: 0; background: none; color: var(--cave-accent); min-height: 44px; padding: 8px; }.cave-loading { min-height: 160px; display: flex; justify-content: center; align-items: center; gap: 12px; background: #edf2ee; border-radius: 16px; font-size: 14px; }.unlit-lamp { width: 14px; height: 22px; border-radius: 50% 50% 4px 4px; background: #bbad83; }
.fortune-detail { text-align: center; color: #24443d; }.fortune-detail h2 { font-family: 'Noto Serif SC', SimSun, STSong, serif; font-size: 28px; margin: 16px 0; }.fortune-detail p { font-size: 16px; line-height: 1.8; }.fortune-mark { display: inline-flex; justify-content: center; align-items: center; width: 56px; height: 80px; border-radius: 28px 28px 4px 4px; color: #78531c; background: #f1e8cf; font-family: SimSun, STSong, serif; font-size: 24px; }.fortune-explanation { font-size: 14px !important; color: #536d62; margin-top: 24px; }@media (max-width: 390px) { .now-card { padding: 18px; }.now-card h2 { font-size: 23px; }.cave-heading-title { gap: 10px; }.cave-room { gap: 16px; } }
@media (min-width: 1000px) { .cave-heading { margin-bottom: 28px; }.cave-heading h1 { font-size: 30px; }.fortune-name { display: inline; }.cave-room { grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr); gap: 48px; align-items: center; }.cave-room-scene { min-height: 440px; }.xiaoman-line { padding-top: 24px; }.cave-quiet-note { display: block; padding-left: 6px; margin-top: 8px; }.now-card { padding: 32px; background: #f0f5f0; border-radius: 20px 20px 20px 4px; }.now-card h2 { font-size: 32px; margin-top: 16px; }.now-meta { margin-bottom: 30px; }.cave-growth-link { margin-top: 12px; }.now-card--empty h2 { font-size: 28px; } }
</style>
