<template>
  <div v-if="visible" class="members-overlay" @click.self="$emit('close')">
    <section class="members-dialog" role="dialog" aria-modal="true" aria-labelledby="members-dialog-title">
      <header class="members-header">
        <div>
          <p class="members-kicker">笔记本共享</p>
          <h2 id="members-dialog-title">协作成员</h2>
        </div>
        <button type="button" class="icon-button" aria-label="关闭成员窗口" @click="$emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
      </header>

      <form v-if="canManage" class="member-add-form" @submit.prevent="submitAdd">
        <div class="member-add-fields">
          <label class="sr-only" for="member-identifier">用户名或邮箱</label>
          <input id="member-identifier" v-model="identifier" class="member-input" type="text" placeholder="输入用户名或邮箱" autocomplete="off" required />
          <label class="sr-only" for="member-role">成员权限</label>
          <select id="member-role" v-model="role" class="member-input member-role-select">
            <option value="editor">可编辑</option>
            <option value="viewer">仅查看</option>
          </select>
          <button type="submit" class="member-add-button" :disabled="pending || !identifier.trim()">
            {{ pending ? '添加中...' : '添加成员' }}
          </button>
        </div>
        <p v-if="error" class="members-error" role="alert">{{ error }}</p>
      </form>

      <div class="members-list" aria-live="polite">
        <div v-if="loading" class="members-state">正在加载成员…</div>
        <div v-else-if="!members.length" class="members-state">还没有其他成员</div>
        <template v-else>
          <div v-for="member in members" :key="member.user_id" class="member-row">
            <div class="member-person">
              <span class="member-avatar" aria-hidden="true">{{ member.username?.slice(0, 1)?.toUpperCase() || '?' }}</span>
              <span class="member-identity"><strong>{{ member.username }}</strong><small>{{ member.email }}</small></span>
            </div>
            <div class="member-controls">
              <span v-if="member.role === 'owner'" class="member-role-label member-role-label--owner">所有者</span>
              <select v-else-if="canManage" class="member-role-select" :value="member.role" :disabled="pending" :aria-label="`${member.username} 的权限`" @change="$emit('update-role', { userId: member.user_id, role: $event.target.value })">
                <option value="editor">可编辑</option>
                <option value="viewer">仅查看</option>
              </select>
              <span v-else class="member-role-label">{{ member.role === 'editor' ? '可编辑' : '仅查看' }}</span>
              <button v-if="canManage && member.role !== 'owner'" type="button" class="remove-member-button" :disabled="pending" @click="$emit('remove', member)">移除</button>
            </div>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  members: { type: Array, default: () => [] },
  loading: Boolean,
  pending: Boolean,
  error: { type: String, default: '' },
  canManage: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'add', 'update-role', 'remove'])
const identifier = ref('')
const role = ref('editor')

watch(() => props.visible, (visible) => {
  if (visible) {
    identifier.value = ''
    role.value = 'editor'
  }
})

function submitAdd() {
  if (!identifier.value.trim()) return
  emit('add', { username_or_email: identifier.value.trim(), role: role.value })
}
</script>

<style scoped>
.members-overlay { position: fixed; inset: 0; z-index: 300; display: grid; place-items: center; padding: var(--spacing-lg); background: rgba(2, 6, 23, .64); }
.members-dialog { width: min(620px, 100%); max-height: min(720px, 90dvh); overflow: auto; border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-card); color: var(--color-text); box-shadow: var(--shadow-lg); }
.members-header { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--spacing-md); padding: var(--spacing-xl); border-bottom: 1px solid var(--color-border); }
.members-header h2 { margin: 0; font-family: var(--font-family-display); font-size: var(--font-size-xl); }
.members-kicker { margin: 0 0 var(--spacing-2xs); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.icon-button { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; border: 1px solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text-secondary); background: transparent; cursor: pointer; }
.icon-button:hover, .icon-button:focus-visible { color: var(--color-text); background: var(--color-bg-secondary); outline: 2px solid var(--color-primary); outline-offset: 2px; }
.icon-button svg { width: 20px; height: 20px; }
.member-add-form { padding: var(--spacing-lg) var(--spacing-xl); border-bottom: 1px solid var(--color-border); background: var(--color-bg-secondary); }
.member-add-fields { display: grid; grid-template-columns: minmax(0, 1fr) 130px auto; gap: var(--spacing-sm); }
.member-input, .member-role-select { min-height: 42px; box-sizing: border-box; padding: 8px 10px; border: 1px solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text); background: var(--color-card); font: inherit; }
.member-input:focus, .member-role-select:focus { border-color: var(--color-primary); outline: 2px solid rgba(14, 165, 233, .18); }
.member-add-button, .remove-member-button { min-height: 42px; padding: 8px 14px; border: 1px solid var(--color-primary); border-radius: var(--radius-md); color: #fff; background: var(--color-primary); cursor: pointer; font: inherit; font-weight: 700; }
.member-add-button:disabled, .remove-member-button:disabled { opacity: .55; cursor: not-allowed; }
.members-error { margin: var(--spacing-sm) 0 0; color: var(--color-error-dark); font-size: var(--font-size-sm); }
.members-list { padding: var(--spacing-sm) var(--spacing-xl) var(--spacing-xl); }
.members-state { padding: var(--spacing-xl) 0; color: var(--color-text-secondary); text-align: center; }
.member-row { display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md); padding: var(--spacing-md) 0; border-bottom: 1px solid var(--color-border); }
.member-row:last-child { border-bottom: 0; }
.member-person, .member-controls { display: flex; align-items: center; gap: var(--spacing-sm); min-width: 0; }
.member-avatar { display: inline-grid; flex: 0 0 auto; place-items: center; width: 36px; height: 36px; border-radius: 50%; color: var(--color-primary); background: var(--color-bg-secondary); font-weight: 800; }
.member-identity { display: grid; min-width: 0; gap: 2px; }
.member-identity strong, .member-identity small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.member-identity small { color: var(--color-text-secondary); font-size: var(--font-size-xs); }
.member-role-label { color: var(--color-text-secondary); font-size: var(--font-size-sm); font-weight: 700; }
.member-role-label--owner { color: var(--color-primary); }
.member-controls .member-role-select { min-height: 36px; }
.remove-member-button { min-height: 36px; border-color: var(--color-border); color: var(--color-error-dark); background: transparent; font-size: var(--font-size-sm); }
.remove-member-button:hover, .remove-member-button:focus-visible { border-color: var(--color-error); background: var(--color-bg-secondary); outline: 2px solid rgba(239, 68, 68, .15); }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (max-width: 560px) { .members-overlay { padding: var(--spacing-sm); } .members-header, .member-add-form { padding: var(--spacing-lg) var(--spacing-md); } .members-list { padding: var(--spacing-sm) var(--spacing-md) var(--spacing-lg); } .member-add-fields { grid-template-columns: 1fr 1fr; } .member-add-button { grid-column: 1 / -1; } .member-row { align-items: flex-start; flex-direction: column; } .member-controls { width: 100%; justify-content: flex-end; } }
</style>
