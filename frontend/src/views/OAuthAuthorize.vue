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
.oauth-page {
  display: grid;
  gap: 18px;
  max-width: 720px;
  margin: 0 auto;
  padding: clamp(28px, 7vh, 72px) var(--page-padding-x) 56px;
  min-height: 100dvh;
  align-content: start;
  color: var(--color-text);
  background:
    radial-gradient(900px 420px at 50% -10%, #E7F5EF 0%, rgba(231, 245, 239, 0) 62%),
    var(--home-canvas);
  box-sizing: border-box;
}

.oauth-card {
  display: grid;
  gap: 10px;
  padding: clamp(20px, 2.6vw, 30px);
  background: #FFFFFF;
  border: 0;
  border-radius: 22px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03), 0 20px 44px -32px rgba(15, 23, 42, 0.35);
}

h1 { margin: 0; font-size: clamp(1.3rem, 1.1rem + 0.6vw, 1.6rem); letter-spacing: -0.01em; }
h2 { margin: 0; font-size: 16px; font-weight: 650; letter-spacing: -0.01em; }
p { margin: 0; line-height: 1.7; color: var(--home-ink-tertiary); }
strong { color: var(--color-text); }
a { color: var(--rank-1-accent); font-weight: 600; font-size: 13.5px; text-decoration: none; justify-self: start; }
a:hover { text-decoration: underline; }

dl { display: grid; gap: 0; margin: 4px 0 2px; }
dt {
  margin: 0;
  padding-top: 10px;
  border-top: 1px solid var(--home-hairline);
  color: var(--home-ink-tertiary);
  font-size: 11.5px;
  font-weight: 500;
}
dd {
  margin: 2px 0 10px;
  overflow-wrap: anywhere;
  color: var(--color-text);
  font-weight: 600;
  font-size: 13.5px;
}

.actions { display: flex; gap: 10px; margin-top: 8px; flex-wrap: wrap; }

button {
  justify-self: start;
  min-height: 44px;
  padding: 10px 20px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--home-soft);
  color: var(--color-text);
  cursor: pointer;
  font: inherit;
  font-size: 13.5px;
  font-weight: 600;
  transition: background 0.15s ease;
}
button:hover:not(:disabled) { background: #E9F0EE; }
button.approve { background: var(--rank-1-accent); color: #FFFFFF; }
button.approve:hover:not(:disabled) { background: #0A6B50; }
button:disabled { opacity: 0.55; cursor: wait; }
button:focus-visible, a:focus-visible { outline: 2px solid var(--rank-1-accent); outline-offset: 3px; }

.error { padding: 10px 14px; border-radius: 12px; background: #FEF3F2; color: #B42318; }

ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 0; }
li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid var(--home-hairline);
}
li:last-child { border-bottom: 0; }
li p { margin-top: 2px; overflow-wrap: anywhere; font-size: 12.5px; }
</style>
