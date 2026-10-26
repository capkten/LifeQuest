<template>
  <main class="oauth-page">
    <section class="oauth-card" aria-labelledby="oauth-heading">
      <RouterLink to="/profile" referrerpolicy="no-referrer">返回个人中心</RouterLink>
      <h1 id="oauth-heading">LifeQuest 应用授权</h1>
      <p>当前账号：<strong>{{ auth.user?.username }}</strong></p>
      <p v-if="loading" role="status">正在加载授权请求…</p>
      <p v-if="state.error" class="error" role="alert">{{ state.error }}</p>
      <template v-if="state.details && !state.finished">
        <h2>{{ state.details.client_name }} 请求连接 LifeQuest</h2>
        <p>此应用将能查询和操作你有权访问的任务、习惯、笔记、项目及其他 MCP 工具数据。请仅授权你信任的应用。</p>
        <dl>
          <dt>回调域名</dt><dd>{{ callbackHost }}</dd>
          <dt>完整回调地址</dt><dd>{{ state.details.redirect_uri }}</dd>
          <dt>授权范围</dt><dd>{{ state.details.scope }}</dd>
          <dt>MCP 资源</dt><dd>{{ state.details.resource }}</dd>
        </dl>
        <p>确认应用和回调域名后再继续；应用名称由客户端提供。</p>
        <div class="actions">
          <button :disabled="state.submitting" @click="submit(false)">拒绝</button>
          <button class="approve" :disabled="state.submitting" @click="submit(true)">{{ state.submitting ? '正在提交…' : '同意授权' }}</button>
        </div>
      </template>
      <p v-else-if="!loading && !requestId">如需连接新应用，请从该应用发起 OAuth 登录。你可以在下方管理已授权应用。</p>
      <p v-if="state.finished" role="status">授权请求已处理，正在返回应用…</p>
    </section>
    <section class="oauth-card" aria-labelledby="grants-heading">
      <h2 id="grants-heading">已授权应用</h2>
      <p>撤销后，该授权的访问令牌和刷新令牌立即失效，不影响个人访问令牌（PAT）。</p>
      <p v-if="grantsError" class="error" role="alert">{{ grantsError }}</p>
      <p v-if="grantsLoading" role="status">正在加载应用…</p>
      <p v-else-if="!grants.length && !grantsError">暂无应用授权。</p>
      <ul v-else>
        <li v-for="grant in grants" :key="grant.id">
          <div><strong>{{ grant.client_name }}</strong><p>{{ grant.scope }} · {{ grant.resource }}</p></div>
          <button :disabled="Boolean(revoking)" @click="revoke(grant.id)">{{ revoking === grant.id ? '正在撤销…' : '撤销授权' }}</button>
        </li>
      </ul>
      <button :disabled="grantsLoading" @click="loadGrants">刷新列表</button>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { mcpOAuthService } from '../services/mcpOAuth'
import { createConsentState } from '../services/mcpOAuthState'

const route = useRoute()
const auth = useAuthStore()
// Capture once: never switch an in-progress consent to a newly supplied handle.
const requestId = typeof route.query.request_id === 'string' ? route.query.request_id : ''
const state = reactive(createConsentState())
const loading = ref(Boolean(requestId))
const grants = ref([])
const grantsLoading = ref(false)
const grantsError = ref('')
const revoking = ref('')
const callbackHost = computed(() => {
  try { return new URL(state.details.redirect_uri).host } catch { return '无效回调地址' }
})
let referrerMeta
let previousReferrer
function message(error, fallback) {
  // Do not render server exception strings, request headers or credential values.
  const status = error?.response?.status
  if (status === 404 || status === 410) return '授权请求已失效，请返回应用重新发起登录。'
  if (status === 403) return '当前账号无权处理此请求，请返回应用重新发起登录。'
  return fallback
}
async function loadGrants() {
  grantsLoading.value = true
  grantsError.value = ''
  try { grants.value = await mcpOAuthService.listGrants() }
  catch (error) { grantsError.value = message(error, '无法加载授权列表，请重试。') }
  finally { grantsLoading.value = false }
}
async function submit(approve) {
  if (!state.beginSubmit()) return
  try {
    const result = await mcpOAuthService.consent(requestId, approve)
    // Only the authenticated server constructs and validates this callback;
    // nothing from this page's query string is used as a navigation target.
    const callback = new URL(result.redirect_uri)
    if (!['https:', 'http:'].includes(callback.protocol)) throw new Error('Invalid callback')
    state.completed()
    window.location.replace(callback.href)
  } catch (error) { state.failed(message(error, '无法提交授权，请重试或从应用重新开始。')) }
}
async function revoke(id) {
  if (revoking.value || !window.confirm('撤销此应用授权？现有连接将立即失效。')) return
  revoking.value = id
  grantsError.value = ''
  try {
    await mcpOAuthService.revokeGrant(id)
    grants.value = grants.value.filter(grant => grant.id !== id)
  } catch (error) { grantsError.value = message(error, '撤销失败，请重试。') }
  finally { revoking.value = '' }
}
onMounted(async () => {
  referrerMeta = document.querySelector('meta[name="referrer"]')
  previousReferrer = referrerMeta?.getAttribute('content')
  if (!referrerMeta) {
    referrerMeta = document.createElement('meta')
    referrerMeta.name = 'referrer'
    document.head.appendChild(referrerMeta)
  }
  referrerMeta.content = 'no-referrer'
  loadGrants()
  if (!requestId) return
  try { state.loaded(await mcpOAuthService.details(requestId)) }
  catch (error) { state.failed(message(error, '无法加载授权请求，请返回应用重新发起登录。')) }
  finally { loading.value = false }
})
onBeforeUnmount(() => {
  if (previousReferrer == null) referrerMeta?.remove()
  else referrerMeta?.setAttribute('content', previousReferrer)
})
</script>

<style scoped>
.oauth-page { max-width: 760px; margin: 0 auto; padding: 24px 16px; color: #172033; }
.oauth-card { background: #fff; border: 1px solid #d6dce5; border-radius: 16px; padding: 24px; margin-bottom: 20px; }
h1 { font-size: 1.6rem; } h2 { font-size: 1.2rem; }
p { line-height: 1.7; } dt { font-weight: 600; margin-top: 14px; }
dd { margin: 4px 0; overflow-wrap: anywhere; }
.actions { display: flex; gap: 12px; margin-top: 24px; }
button { padding: 10px 18px; border: 1px solid #64748b; border-radius: 8px; background: #fff; color: #172033; cursor: pointer; }
button.approve { background: #244ac0; color: #fff; border-color: #244ac0; }
button:disabled { opacity: .55; cursor: wait; }
.error { color: #a12323; } ul { list-style: none; padding: 0; }
li { border-bottom: 1px solid #d6dce5; padding: 14px 0; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
li p { overflow-wrap: anywhere; font-size: .9rem; }
</style>
