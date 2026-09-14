<template>
  <div class="profile-page">
    <section class="profile-hero">
      <div class="profile-hero-main">
        <div class="profile-avatar">
          <img v-if="avatarSrc" :src="avatarSrc" alt="用户头像" class="profile-avatar-img" />
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="8" r="4" />
            <path d="M20 21a8 8 0 1 0-16 0" />
          </svg>
        </div>

        <div class="profile-copy">
          <span class="profile-kicker">玩家概览</span>
          <div class="profile-name-row">
            <h1 class="profile-name">{{ user?.username || '冒险者' }}</h1>
            <span v-if="activeTitle" class="profile-title-badge">{{ activeTitle.name }}</span>
          </div>
          <p class="profile-subtitle">{{ user?.title || '冒险者' }}</p>
          <p v-if="user?.email" class="profile-email">{{ user.email }}</p>

          <div class="profile-meta">
            <span class="profile-meta-pill">等级 {{ user?.level || 1 }}</span>
            <span class="profile-meta-pill">{{ user?.coins || 0 }} 金币</span>
            <span class="profile-meta-pill">{{ user?.experience || 0 }} 经验</span>
            <span class="profile-meta-pill">{{ unlockedAchievementsCount }} 个成就</span>
          </div>
        </div>

        <div class="profile-actions">
          <button class="secondary-btn" @click="showTitleModal = true">切换称号</button>
          <button class="primary-btn" @click="goToEditProfile">编辑资料</button>
        </div>
      </div>

      <div class="profile-progress-card">
        <div class="progress-header">
          <div>
          <span class="section-kicker">下一等级</span>
            <h2>经验进度</h2>
          </div>
          <strong>{{ expPercent }}%</strong>
        </div>
        <div
          class="exp-bar"
          role="progressbar"
          :aria-valuenow="expPercent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`经验值进度：${expPercent}%，距离下一等级`"
        >
          <div class="exp-bar-fill" :style="{ width: expPercent + '%' }"></div>
        </div>
        <div class="progress-meta">
          <span>{{ user?.experience || 0 }} / {{ requiredExp }} 经验</span>
          <span>距离下一等级还差 {{ Math.max(requiredExp - (user?.experience || 0), 0) }} 经验</span>
        </div>
      </div>
    </section>

    <section class="attributes-grid">
      <article v-for="card in attributeCards" :key="card.key" class="attribute-card" :class="'attribute-card--' + card.key">
        <div class="attribute-icon" v-html="card.icon" aria-hidden="true"></div>
        <div class="attribute-copy">
          <span class="attribute-label">{{ card.label }}</span>
          <strong class="attribute-value">{{ card.value }}</strong>
          <span class="attribute-note">{{ card.note }}</span>
        </div>
      </article>
    </section>

    <div v-if="profileError" class="state-copy profile-error" role="alert">
      <span>{{ profileError }}</span>
      <button type="button" class="retry-btn" @click="fetchProfile">重试</button>
    </div>

    <section class="content-grid">
      <article class="surface-card">
        <div class="section-heading">
          <div>
          <span class="section-kicker">属性</span>
            <h2>能力属性</h2>
          </div>
          <span class="section-meta">来自当前账号真实数据</span>
        </div>

        <div class="stats-detail-grid">
          <div class="detail-card">
            <span class="detail-label">累计经验</span>
            <strong>{{ user?.experience || 0 }}</strong>
            <p>经验条和等级保持现有计算逻辑。</p>
          </div>
          <div class="detail-card">
            <span class="detail-label">累计金币</span>
            <strong>{{ user?.coins || 0 }}</strong>
            <p>商城兑换与背包消耗仍会同步影响这里。</p>
          </div>
          <div class="detail-card">
            <span class="detail-label">已完成任务</span>
            <strong>{{ stats.totalTasksCompleted }}</strong>
          <p>根据已完成任务的数量统计。</p>
          </div>
          <div class="detail-card">
            <span class="detail-label">最佳习惯连击</span>
            <strong>{{ stats.maxHabitStreak }}</strong>
          <p>取所有习惯最佳连击或当前连击的最大值。</p>
          </div>
        </div>
      </article>

      <article class="surface-card">
        <div class="section-heading">
          <div>
          <span class="section-kicker">物品</span>
            <h2>背包入口</h2>
          </div>
          <router-link class="text-link" to="/backpack">查看背包</router-link>
        </div>

        <div class="inventory-summary">
          <div class="inventory-summary-card">
            <span>奖励与背包</span>
            <strong>继续管理你的道具收藏</strong>
            <p>背包页会按物品类型分组，并保留使用、装备、丢弃和历史功能。</p>
          </div>
          <div class="inventory-actions">
            <router-link class="secondary-link" to="/backpack/history">使用历史</router-link>
            <router-link class="primary-link" to="/shop">前往商城</router-link>
          </div>
        </div>
      </article>
    </section>

    <section class="surface-card mcp-token-card">
      <div class="section-heading">
        <div>
          <span class="section-kicker">{{ mcpLabel }}</span>
          <h2>{{ mcpLabel }} 访问凭证</h2>
        </div>
        <span class="section-meta">用于连接 LifeQuest {{ mcpLabel }} 服务</span>
      </div>

      <form class="mcp-token-form" @submit.prevent="createMcpToken">
        <div class="mcp-token-field">
          <label class="form-label" for="mcp-token-name">凭证名称</label>
          <input
            id="mcp-token-name"
            v-model="mcpTokenForm.name"
            class="form-input"
            type="text"
            maxlength="100"
            placeholder="例如：桌面客户端"
            required
          />
        </div>
        <div class="mcp-token-field">
          <label class="form-label" for="mcp-token-expires">有效期（天）</label>
          <input
            id="mcp-token-expires"
            v-model.number="mcpTokenForm.expires_in_days"
            class="form-input"
            type="number"
            min="1"
            max="365"
            step="1"
            required
          />
        </div>
        <button
          type="submit"
          class="primary-btn"
          :disabled="mcpTokenCreating || mcpTokensLoading || !mcpTokenForm.name.trim() || mcpTokenForm.expires_in_days < 1 || mcpTokenForm.expires_in_days > 365"
        >
          {{ mcpTokenCreating ? '创建中...' : '创建凭证' }}
        </button>
      </form>

      <div v-if="mcpTokensError" class="mcp-token-error" role="alert">
        <span>{{ mcpTokensError }}</span>
        <button type="button" class="retry-btn" :disabled="mcpTokensLoading || mcpTokenCreating" @click="fetchMcpTokens">重试</button>
      </div>

      <div v-if="mcpTokensLoading" class="state-copy">加载访问凭证列表中...</div>
      <div v-else-if="mcpTokens.length === 0" class="state-copy">暂无 {{ mcpLabel }} 访问凭证</div>
      <div v-else class="mcp-token-list">
        <div v-for="token in mcpTokens" :key="token.id" class="mcp-token-row">
          <div class="mcp-token-info">
            <div class="mcp-token-name-row">
              <strong>{{ token.name }}</strong>
              <span class="mcp-token-status" :class="`mcp-token-status--${token.status}`">
                {{ mcpTokenStatusLabel(token.status) }}
              </span>
            </div>
            <span class="mcp-token-prefix">{{ token.token_prefix }}...</span>
            <span class="mcp-token-meta">
              创建于 {{ formatDate(token.created_at) }}，{{ token.status === 'revoked' ? `撤销于 ${formatDate(token.revoked_at)}` : `过期于 ${formatDate(token.expires_at)}` }}
            </span>
          </div>
          <button
            v-if="isMcpTokenRevocable(token)"
            type="button"
            class="secondary-btn mcp-token-revoke"
            :disabled="mcpTokenRevoking || mcpTokenCopying"
            @click="openRevokeDialog(token)"
          >
            撤销
          </button>
        </div>
      </div>

      <div v-if="newMcpToken" class="mcp-new-token" role="status">
        <div class="mcp-new-token-header">
          <div>
            <span class="section-kicker">仅显示一次</span>
            <h3>访问凭证已创建</h3>
          </div>
          <button type="button" class="dialog-close" aria-label="关闭凭证结果" @click="closeNewMcpToken">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <p class="mcp-token-warning">请立即复制并妥善保存，关闭后将无法再次查看完整凭证。</p>
        <p class="mcp-token-expiry">过期时间：{{ formatDate(newMcpToken.expires_at) }}</p>
        <div class="mcp-token-value-wrap">
          <code class="mcp-token-value">{{ newMcpToken.token }}</code>
          <button type="button" class="primary-btn" :disabled="mcpTokenCopying || mcpTokenRevoking" @click="copyMcpToken">复制凭证</button>
        </div>
        <div class="mcp-config-hint">
          <strong>连接配置提示</strong>
          <pre><code>{{ mcpSseConfig }}
{{ mcpStdioConfig }}</code></pre>
        </div>
      </div>
    </section>

    <section class="surface-card achievements-card">
      <div class="section-heading">
        <div>
          <span class="section-kicker">成就</span>
          <h2>成就墙</h2>
        </div>
        <span class="section-meta">{{ unlockedAchievementsCount }} / {{ mergedAchievements.length || 0 }} 已解锁</span>
      </div>

      <div v-if="achievementsLoading" class="state-copy">加载中...</div>
      <div v-else-if="mergedAchievements.length === 0" class="state-copy">暂无成就数据</div>
      <div v-else class="achievements-grid">
        <article
          v-for="ach in mergedAchievements"
          :key="ach.id"
          class="achievement-card"
          :class="{ 'achievement-card--locked': !ach.unlocked }"
        >
          <div
            class="achievement-icon"
            :class="ach.unlocked ? 'achievement-icon--unlocked' : 'achievement-icon--locked'"
          >
            <svg v-if="ach.unlocked" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <div class="achievement-copy">
            <div class="achievement-topline">
              <h3>{{ ach.name }}</h3>
              <span class="achievement-status">{{ ach.unlocked ? '已解锁' : '未解锁' }}</span>
            </div>
            <p>{{ ach.description || '暂无描述' }}</p>
            <span v-if="ach.unlocked && ach.unlocked_at" class="achievement-date">{{ formatDate(ach.unlocked_at) }} 解锁</span>
          </div>
        </article>
      </div>
    </section>

    <Teleport to="body">
      <div v-if="revokeTarget" class="dialog-overlay" @click.self="closeRevokeDialog">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="mcp-revoke-dialog-title" tabindex="-1">
          <div class="dialog-header">
            <h3 id="mcp-revoke-dialog-title" class="dialog-title">撤销 {{ mcpLabel }} 访问凭证</h3>
            <button class="dialog-close" :disabled="mcpTokenRevoking || mcpTokenCopying" @click="closeRevokeDialog" aria-label="关闭对话框">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="mcp-revoke-copy">确定要撤销「{{ revokeTarget.name }}」吗？撤销后使用该访问凭证的连接将立即失效。</p>
            <div class="dialog-actions">
              <button type="button" class="secondary-btn" :disabled="mcpTokenRevoking || mcpTokenCopying" @click="closeRevokeDialog">取消</button>
              <button type="button" class="primary-btn" :disabled="mcpTokenRevoking || mcpTokenCopying" @click="revokeMcpToken">
                {{ mcpTokenRevoking ? '撤销中...' : '确认撤销' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showTitleModal" class="dialog-overlay" @click.self="showTitleModal = false">
        <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="title-dialog-title">
          <div class="dialog-header">
            <h3 id="title-dialog-title" class="dialog-title">切换称号</h3>
              <button class="dialog-close" @click="showTitleModal = false" aria-label="关闭对话框">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <div v-if="titlesLoading" class="state-copy">加载中...</div>
            <div v-else-if="titlesError" class="state-copy" role="alert">
              <span>{{ titlesError }}</span>
              <button type="button" class="retry-btn" @click="fetchTitles">重试</button>
            </div>
            <div v-else class="titles-list">
              <button
                v-for="title in allTitles"
                :key="title.id"
                type="button"
                class="title-item"
                :class="{
                  'title-item--active': activeTitle?.id === title.id,
                  'title-item--locked': !isUnlocked(title.id)
                }"
                :disabled="!isUnlocked(title.id)"
                @click="isUnlocked(title.id) && activateTitle(title)"
              >
                <div class="title-item-icon">
                  <svg v-if="isUnlocked(title.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <circle cx="12" cy="8" r="7" />
                    <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <div class="title-item-copy">
                  <span class="title-item-name">{{ title.name }}</span>
                  <span class="title-item-desc">
                    {{ isUnlocked(title.id) ? (title.description || '') : (title.unlock_condition || '未解锁') }}
                  </span>
                </div>
                <div v-if="activeTitle?.id === title.id" class="title-item-mark">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                </div>
              </button>
              <div v-if="allTitles.length === 0" class="state-copy">暂无称号数据</div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <Transition name="toast">
      <div v-if="successToast" class="toast toast--success">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M20 6L9 17l-5-5" />
        </svg>
        {{ successToast }}
      </div>
    </Transition>
    <Transition name="toast">
      <div v-if="errorToast" class="toast toast--error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
        {{ errorToast }}
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, toRef } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStats } from '../composables/useUserStats'
import { achievementService } from '../services/achievement'
import { todoService } from '../services/todo'
import { titleService } from '../services/title'
import { mcpTokenService } from '../services/mcpToken'
import { createMcpTokenState, reduceMcpTokenState } from '../services/mcpTokenState'
import { useToast } from '../composables/useToast'
import { useAuthStore } from '../stores/auth'
import { useResolvedImage } from '../composables/useResolvedImage'
import { getErrorMessage } from '../utils/errorMessage'

const router = useRouter()
const authStore = useAuthStore()
const { user, requiredExp, expPercent } = useUserStats()
const { successToast, errorToast, showSuccess, showError } = useToast()
const avatarSrc = useResolvedImage(computed(() => user.value?.avatar))
const mcpLabel = 'MCP'
const mcpEnvironmentVariable = 'LIFEQUEST_MCP_TOKEN'
const mcpSseConfig = 'SSE: Authorization: Bearer <你的 Token>'
const mcpStdioConfig = `stdio: ${mcpEnvironmentVariable}=<你的 Token>`

const stats = reactive({
  totalTasksCompleted: 0,
  maxHabitStreak: 0
})

const allTitles = ref([])
const unlockedTitleIds = ref(new Set())
const activeTitle = ref(null)
const titlesLoading = ref(false)
const titlesError = ref(null)
let titlesRequestId = 0
const showTitleModal = ref(false)

const allAchievements = ref([])
const unlockedIds = ref(new Set())
const unlockDates = ref({})
const achievementsLoading = ref(true)
const profileError = ref(null)
let profileRequestId = 0

const mergedAchievements = computed(() => {
  return allAchievements.value.map((ach) => ({
    ...ach,
    unlocked: unlockedIds.value.has(ach.id),
    unlocked_at: unlockDates.value[ach.id] || null
  }))
})

const unlockedAchievementsCount = computed(() => mergedAchievements.value.filter((ach) => ach.unlocked).length)

const attributeCards = computed(() => [
  {
    key: 'level',
    label: '等级',
    value: `Lv. ${user.value?.level || 1}`,
    note: '成长阶段',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>'
  },
  {
    key: 'exp',
    label: '经验',
    value: `${user.value?.experience || 0} XP`,
    note: '下一等级进度',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" /></svg>'
  },
  {
    key: 'coins',
    label: '金币',
    value: `${user.value?.coins || 0}`,
    note: '商城与奖励货币',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M12 6v12M6 12h12" /></svg>'
  },
  {
    key: 'tasks',
    label: '完成任务',
    value: `${stats.totalTasksCompleted}`,
    note: '已完成数量',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>'
  }
])

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

async function fetchProfile() {
  const requestId = ++profileRequestId
  profileError.value = null
  achievementsLoading.value = true
  fetchTitles()
  const results = await Promise.allSettled([
      achievementService.getAchievements(),
      achievementService.getUserAchievements(),
      todoService.getTasks(),
      todoService.getHabits(),
    ])

  if (requestId !== profileRequestId) return

  const failures = []
  const [allResult, userAchievementsResult, tasksResult, habitsResult] = results

  if (allResult.status === 'fulfilled') {
    allAchievements.value = allResult.value || []
  } else {
    failures.push(getErrorMessage(allResult.reason, '加载成就列表失败，请重试。'))
  }

  if (userAchievementsResult.status === 'fulfilled') {
    const ids = new Set()
    const dates = {}
    for (const ua of (userAchievementsResult.value || [])) {
      const achId = ua.achievement_id || ua.achievement?.id
      if (achId) {
        ids.add(achId)
        dates[achId] = ua.unlocked_at
      }
    }
    unlockedIds.value = ids
    unlockDates.value = dates
  } else {
    failures.push(getErrorMessage(userAchievementsResult.reason, '加载成就进度失败，请重试。'))
  }

  if (tasksResult.status === 'fulfilled') {
    const taskList = Array.isArray(tasksResult.value) ? tasksResult.value : (tasksResult.value?.data || [])
    stats.totalTasksCompleted = taskList.filter(t => t.status === 'completed').length
  } else {
    failures.push(getErrorMessage(tasksResult.reason, '加载任务统计失败，请重试。'))
  }

  if (habitsResult.status === 'fulfilled') {
    const habitList = Array.isArray(habitsResult.value) ? habitsResult.value : (habitsResult.value?.data || [])
    stats.maxHabitStreak = habitList.reduce((max, h) => Math.max(max, h.best_streak || h.streak || 0), 0)
  } else {
    failures.push(getErrorMessage(habitsResult.reason, '加载习惯统计失败，请重试。'))
  }

  profileError.value = failures[0] || null
  achievementsLoading.value = false
}

const mcpTokenState = reactive(createMcpTokenState())
const mcpTokens = toRef(mcpTokenState, 'mcpTokens')
const mcpTokensLoading = toRef(mcpTokenState, 'mcpTokensLoading')
const mcpTokensError = toRef(mcpTokenState, 'mcpTokensError')
const mcpTokenForm = mcpTokenState.mcpTokenForm
const mcpTokenCreating = toRef(mcpTokenState, 'mcpTokenCreating')
const newMcpToken = toRef(mcpTokenState, 'newMcpToken')
const revokeTarget = toRef(mcpTokenState, 'revokeTarget')
const mcpTokenRevoking = toRef(mcpTokenState, 'mcpTokenRevoking')
const mcpTokenCopying = toRef(mcpTokenState, 'mcpTokenCopying')
let mcpTokensRequestId = 0
let mcpTokensRequest = null

function applyMcpTokenAction(action) {
  const nextState = reduceMcpTokenState(mcpTokenState, action)
  if (nextState !== mcpTokenState) Object.assign(mcpTokenState, nextState)
}

onMounted(fetchProfile)
onMounted(fetchMcpTokens)

function isUnlocked(titleId) {
  return unlockedTitleIds.value.has(titleId)
}

async function activateTitle(title) {
  try {
    await titleService.activateTitle(title.id)
    activeTitle.value = title
    await authStore.fetchUser()
    showSuccess(`称号已更换为「${title.name}」`)
    showTitleModal.value = false
  } catch (e) {
    showError(getErrorMessage(e))
  }
}

async function fetchTitles() {
  const requestId = ++titlesRequestId
  titlesLoading.value = true
  titlesError.value = null
  try {
    const [all, my] = await Promise.all([
      titleService.getAllTitles(),
      titleService.getMyTitles()
    ])
    if (requestId !== titlesRequestId) return
    allTitles.value = all || []
    const ids = new Set()
    for (const t of (my || [])) {
      const tid = t.title_id || t.title?.id || t.id
      if (tid) ids.add(tid)
      if (t.is_active || t.active) {
        activeTitle.value = allTitles.value.find(at => at.id === tid) || t
      }
    }
    unlockedTitleIds.value = ids
    if (!activeTitle.value && user.value?.title) {
      activeTitle.value = allTitles.value.find(t => t.name === user.value.title) || null
    }
  } catch (e) {
    if (requestId === titlesRequestId) titlesError.value = getErrorMessage(e, '加载称号失败，请重试。')
  } finally {
    if (requestId === titlesRequestId) titlesLoading.value = false
  }
}

function goToEditProfile() {
  router.push({ name: 'EditProfile' })
}

async function fetchMcpTokens({ waitForActive = false } = {}) {
  if (mcpTokenCreating.value && !waitForActive) return
  if (mcpTokensLoading.value) {
    if (!waitForActive || !mcpTokensRequest) return
    await mcpTokensRequest.catch(() => {})
    return fetchMcpTokens()
  }

  const requestId = ++mcpTokensRequestId
  applyMcpTokenAction({ type: 'list-start' })
  const request = (async () => {
    try {
      const tokens = await mcpTokenService.listTokens()
      if (requestId !== mcpTokensRequestId) return
      applyMcpTokenAction({ type: 'list-success', tokens })
    } catch (e) {
      if (requestId === mcpTokensRequestId) {
        applyMcpTokenAction({ type: 'list-failure', error: getErrorMessage(e, '加载 MCP Token 失败，请重试。') })
      }
    }
  })()
  mcpTokensRequest = request
  try {
    await request
  } finally {
    if (mcpTokensRequest === request) mcpTokensRequest = null
  }
}

async function createMcpToken() {
  if (mcpTokenCreating.value) return
  const name = mcpTokenForm.name.trim()
  const expiresInDays = Number(mcpTokenForm.expires_in_days)
  if (!name || !Number.isInteger(expiresInDays) || expiresInDays < 1 || expiresInDays > 365) {
    showError('有效期需为 1 至 365 天。')
    return
  }

  applyMcpTokenAction({ type: 'create-start' })
  try {
    const createdToken = await mcpTokenService.createToken({
      name,
      expires_in_days: expiresInDays
    })
    applyMcpTokenAction({ type: 'create-success', token: createdToken })
    mcpTokenForm.name = ''
    showSuccess('MCP Token 创建成功，请立即复制。')
    await fetchMcpTokens({ waitForActive: true })
  } catch (e) {
    applyMcpTokenAction({ type: 'create-failure' })
    showError(getErrorMessage(e, '创建 MCP Token 失败，请重试。'))
  }
}

async function copyMcpToken() {
  const token = newMcpToken.value?.token
  if (!token || mcpTokenCopying.value || mcpTokenRevoking.value) return
  applyMcpTokenAction({ type: 'copy-start' })
  try {
    await navigator.clipboard.writeText(token)
    showSuccess('MCP Token 已复制。')
    applyMcpTokenAction({ type: 'copy-success' })
  } catch (e) {
    applyMcpTokenAction({ type: 'copy-failure' })
    showError(getErrorMessage(e, '复制失败，请手动复制。'))
  } finally {
    applyMcpTokenAction({ type: 'copy-finish' })
  }
}

function closeNewMcpToken() {
  applyMcpTokenAction({ type: 'clear-new-token' })
}

function mcpTokenStatusLabel(status) {
  return { active: '有效', expired: '已过期', revoked: '已撤销' }[status] || '未知状态'
}

function isMcpTokenRevocable(token) {
  return token.status === 'active' && !token.revoked_at
}

function openRevokeDialog(token) {
  applyMcpTokenAction({ type: 'open-revoke', token })
}

function closeRevokeDialog() {
  applyMcpTokenAction({ type: 'close-revoke' })
}

async function revokeMcpToken() {
  const tokenId = revokeTarget.value?.id
  if (!tokenId || mcpTokenRevoking.value || mcpTokenCopying.value) return

  applyMcpTokenAction({ type: 'revoke-start' })
  try {
    await mcpTokenService.revokeToken(tokenId)
    showSuccess('MCP Token 已撤销。')
    applyMcpTokenAction({ type: 'revoke-success', tokenId })
    await fetchMcpTokens({ waitForActive: true })
  } catch (e) {
    applyMcpTokenAction({ type: 'revoke-failure' })
    showError(getErrorMessage(e, '撤销 MCP Token 失败，请重试。'))
  } finally {
    applyMcpTokenAction({ type: 'revoke-finish' })
  }
}
</script>

<style scoped>
.profile-page {
  padding: var(--page-padding-y) var(--page-padding-x);
  display: grid;
  gap: 16px;
}

.profile-hero,
.surface-card,
.attribute-card {
  border: 1px solid var(--color-border);
  border-radius: var(--surface-radius);
  background: var(--color-card);
  box-shadow: var(--shadow-sm);
}

.profile-hero {
  padding: var(--surface-padding);
  display: grid;
  gap: 16px;
  background:
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.16), transparent 30%),
    linear-gradient(135deg, #ffffff 0%, #eef9fb 100%);
}

.profile-hero-main {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 16px;
  align-items: center;
}

.profile-avatar {
  width: 96px;
  height: 96px;
  border-radius: 30px;
  overflow: hidden;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.profile-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-avatar svg {
  width: 40px;
  height: 40px;
  color: #fff;
}

.profile-copy {
  min-width: 0;
}

.profile-kicker,
.section-kicker {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--color-primary-dark);
}

.profile-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.profile-name,
.section-heading h2 {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-family-display);
}

.profile-name {
  font-size: clamp(1.75rem, 2.2vw, 2.5rem);
}

.profile-title-badge {
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.profile-subtitle,
.profile-email,
.section-meta,
.detail-card p,
.inventory-summary-card p,
.achievement-copy p,
.title-item-desc,
.state-copy {
  color: var(--color-text-secondary);
}

.profile-subtitle,
.profile-email {
  margin: 6px 0 0;
}

.profile-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.profile-meta-pill {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(14, 165, 233, 0.12);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.profile-actions {
  display: grid;
  gap: 10px;
}

.primary-btn,
.secondary-btn,
.primary-link,
.secondary-link,
.text-link {
  min-height: 44px;
  padding: 0 16px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  font-weight: 700;
  border: 1px solid transparent;
  cursor: pointer;
}

.primary-btn,
.primary-link {
  background: var(--color-primary);
  color: #fff;
}

.secondary-btn,
.secondary-link {
  background: #fff;
  color: var(--color-text);
  border-color: var(--color-border);
}

.text-link {
  background: transparent;
  color: var(--color-primary-dark);
}

.profile-progress-card {
  padding: 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(14, 165, 233, 0.12);
  display: grid;
  gap: 12px;
}

.progress-header,
.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
}

.progress-header h2 {
  margin: 6px 0 0;
  font-family: var(--font-family-display);
}

.progress-header strong,
.detail-card strong,
.inventory-summary-card strong {
  font-family: var(--font-family-display);
  color: var(--color-text);
}

.exp-bar {
  height: 10px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.18);
  overflow: hidden;
}

.exp-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.attributes-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.attribute-card {
  padding: 16px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.attribute-icon {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.attribute-icon :deep(svg) {
  width: 22px;
  height: 22px;
}

.attribute-card--level .attribute-icon {
  background: rgba(14, 165, 233, 0.14);
  color: var(--color-primary-dark);
}

.attribute-card--exp .attribute-icon {
  background: rgba(59, 130, 246, 0.14);
  color: var(--color-secondary);
}

.attribute-card--coins .attribute-icon {
  background: rgba(245, 158, 11, 0.16);
  color: #b45309;
}

.attribute-card--tasks .attribute-icon {
  background: rgba(16, 185, 129, 0.14);
  color: var(--color-success);
}

.attribute-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.attribute-label,
.detail-label {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-tertiary);
  font-weight: 700;
}

.attribute-value {
  color: var(--color-text);
  font-size: 1.15rem;
}

.attribute-note {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.content-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
}

.surface-card {
  padding: var(--surface-padding);
  display: grid;
  gap: 16px;
}

.stats-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-card,
.inventory-summary-card,
.achievement-card,
.title-item {
  padding: 16px;
  border-radius: 20px;
  background: var(--color-bg-secondary);
  border: 1px solid rgba(14, 165, 233, 0.08);
}

.detail-card {
  display: grid;
  gap: 8px;
}

.detail-card strong {
  font-size: 1.45rem;
}

.detail-card p {
  margin: 0;
  line-height: 1.6;
  font-size: var(--font-size-sm);
}

.inventory-summary {
  display: grid;
  gap: 14px;
}

.inventory-summary-card {
  display: grid;
  gap: 8px;
}

.inventory-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.mcp-token-card {
  gap: 18px;
}

.mcp-token-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px auto;
  align-items: end;
  gap: 12px;
}

.mcp-token-field {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.mcp-token-list {
  display: grid;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  overflow: hidden;
}

.mcp-token-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  min-width: 0;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border);
}

.mcp-token-row:last-child {
  border-bottom: 0;
}

.mcp-token-info,
.mcp-token-name-row {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.mcp-token-name-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.mcp-token-name-row strong,
.mcp-token-meta,
.mcp-token-prefix {
  min-width: 0;
  overflow-wrap: anywhere;
}

.mcp-token-name-row strong {
  color: var(--color-text);
}

.mcp-token-prefix {
  color: var(--color-text-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: var(--font-size-sm);
}

.mcp-token-meta {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
}

.mcp-token-status {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.mcp-token-status--active {
  background: rgba(16, 185, 129, 0.14);
  color: var(--color-success);
}

.mcp-token-status--expired,
.mcp-token-status--revoked {
  background: rgba(148, 163, 184, 0.16);
  color: var(--color-text-tertiary);
}

.mcp-token-revoke {
  min-height: 38px;
  padding: 0 12px;
}

.mcp-token-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.mcp-new-token {
  display: grid;
  gap: 12px;
  min-width: 0;
  padding: 16px;
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 18px;
  background: rgba(16, 185, 129, 0.07);
}

.mcp-new-token-header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.mcp-new-token h3 {
  margin: 6px 0 0;
  color: var(--color-text);
}

.mcp-token-warning {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.mcp-token-value-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.mcp-token-value {
  flex: 1;
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-card);
  color: var(--color-text);
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.5;
}

.mcp-config-hint {
  display: grid;
  gap: 8px;
  min-width: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.mcp-config-hint pre {
  margin: 0;
  padding: 12px;
  border-radius: 12px;
  background: var(--color-card);
  color: var(--color-text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.achievements-card {
  gap: 18px;
}

.achievements-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.achievement-card {
  display: flex;
  gap: 12px;
}

.achievement-card--locked {
  opacity: 0.74;
}

.achievement-icon {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.achievement-icon svg {
  width: 20px;
  height: 20px;
}

.achievement-icon--unlocked {
  background: rgba(16, 185, 129, 0.14);
  color: var(--color-success);
}

.achievement-icon--locked {
  background: rgba(148, 163, 184, 0.16);
  color: var(--color-text-tertiary);
}

.achievement-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.achievement-topline {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: start;
}

.achievement-topline h3 {
  margin: 0;
  font-size: 1rem;
  color: var(--color-text);
}

.achievement-status,
.achievement-date {
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.achievement-status {
  color: var(--color-primary-dark);
}

.achievement-date {
  color: var(--color-success);
}

.achievement-copy p {
  margin: 0;
  line-height: 1.6;
  font-size: var(--font-size-sm);
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.48);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 1000;
}

.dialog {
  width: min(100%, 680px);
  max-height: min(84vh, 760px);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 28px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--color-border);
}

.dialog-title {
  margin: 0;
  font-size: 1.2rem;
  color: var(--color-text);
}

.dialog-close {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 0;
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
}

.dialog-body {
  padding: 20px;
  overflow-y: auto;
}

.titles-list {
  display: grid;
  gap: 10px;
}

.title-item {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  text-align: left;
  cursor: pointer;
}

.title-item:disabled {
  cursor: not-allowed;
}

.title-item--active {
  border-color: rgba(14, 165, 233, 0.28);
  background: rgba(14, 165, 233, 0.08);
}

.title-item--locked {
  opacity: 0.55;
}

.title-item-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: #fff;
  color: var(--color-primary-dark);
}

.title-item-icon svg {
  width: 18px;
  height: 18px;
}

.title-item-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.title-item-name {
  font-weight: 700;
  color: var(--color-text);
}

.title-item-mark {
  color: var(--color-primary-dark);
  display: grid;
  place-items: center;
}

.title-item-mark svg {
  width: 20px;
  height: 20px;
}

.state-copy {
  text-align: center;
  padding: 32px 16px;
}

.toast {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  min-height: 44px;
  padding: 0 18px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 700;
  box-shadow: var(--shadow-lg);
  z-index: 2000;
}

.toast svg {
  width: 18px;
  height: 18px;
}

.toast--success {
  background: var(--color-success);
}

.toast--error {
  background: var(--color-error);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 1199px) {
  .attributes-grid,
  .content-grid {
    grid-template-columns: 1fr 1fr;
  }

  .profile-hero-main {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .profile-actions {
    grid-column: 1 / -1;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1023px) {
  .attributes-grid,
  .content-grid,
  .stats-detail-grid,
  .achievements-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .profile-page {
    padding: var(--spacing-md);
  }

  .profile-hero,
  .surface-card,
  .attribute-card {
    border-radius: 22px;
  }

  .profile-hero-main,
  .profile-actions,
  .progress-header,
  .section-heading,
  .title-item,
  .achievement-topline {
    grid-template-columns: 1fr;
    display: grid;
  }

  .profile-avatar {
    width: 84px;
    height: 84px;
  }

  .profile-actions,
  .inventory-actions,
  .mcp-token-form,
  .mcp-token-value-wrap {
    display: grid;
    grid-template-columns: 1fr;
  }

  .mcp-token-row {
    grid-template-columns: 1fr;
  }

  .mcp-token-error {
    align-items: start;
  }

  .toast {
    left: var(--spacing-md);
    right: var(--spacing-md);
    top: var(--spacing-md);
  }
}

@media (min-width: 768px) {
  .profile-page {
    padding: 0;
  }
}
</style>
