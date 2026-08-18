import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import {
  labelRealm,
  labelResource,
  labelSectKind,
  labelSlotType,
  labelStatus,
  labelTaskPreference,
  labelTechniqueType,
  labelNpcRole,
  labelEventSummary,
} from '../utils/displayLabels.js'
import { SLOT_TYPE_LABELS, TECHNIQUE_TYPE_LABELS } from '../locales/zh-CN.js'
import { getErrorMessage } from '../utils/errorMessage.js'

function readBracedBody(source, openBraceIndex) {
  let depth = 1
  let quote = null
  let escaped = false
  let comment = null

  for (let index = openBraceIndex + 1; index < source.length; index += 1) {
    const character = source[index]
    const nextCharacter = source[index + 1]

    if (comment === 'line') {
      if (character === '\n') comment = null
      continue
    }
    if (comment === 'block') {
      if (character === '*' && nextCharacter === '/') {
        comment = null
        index += 1
      }
      continue
    }
    if (quote) {
      if (escaped) {
        escaped = false
      } else if (character === '\\') {
        escaped = true
      } else if (character === quote) {
        quote = null
      }
      continue
    }
    if (character === '/' && nextCharacter === '/') {
      comment = 'line'
      index += 1
      continue
    }
    if (character === '/' && nextCharacter === '*') {
      comment = 'block'
      index += 1
      continue
    }
    if (character === "'" || character === '"' || character === '`') {
      quote = character
      continue
    }
    if (character === '{') depth += 1
    if (character === '}') depth -= 1
    if (depth === 0) return source.slice(openBraceIndex + 1, index)
  }

  throw new Error('Unclosed source block')
}

function readCatchBlocks(source) {
  const catches = []
  const catchPattern = /catch\s*\(\s*([A-Za-z_$][\w$]*)\s*\)\s*\{/g

  for (const match of source.matchAll(catchPattern)) {
    const openBraceIndex = source.indexOf('{', match.index)
    catches.push({ caughtName: match[1], body: readBracedBody(source, openBraceIndex) })
  }

  return catches
}

function readNamedArrowCallback(source, name) {
  const pattern = new RegExp(`${name}\\s*:\\s*\\(\\s*([A-Za-z_$][\\w$]*)\\s*\\)\\s*=>\\s*\\{`)
  const match = pattern.exec(source)
  assert.ok(match, `${name} callback must exist`)
  const openBraceIndex = source.indexOf('{', match.index)
  return { caughtName: match[1], body: readBracedBody(source, openBraceIndex) }
}

function readPromiseCatchCallbacks(source) {
  const callbacks = []
  const pattern = /\.catch\s*\(\s*([A-Za-z_$][\w$]*)\s*=>\s*\{/g

  for (const match of source.matchAll(pattern)) {
    const openBraceIndex = source.indexOf('{', match.index)
    callbacks.push({ caughtName: match[1], body: readBracedBody(source, openBraceIndex) })
  }

  return callbacks
}

function readBranchBody(source, pattern, label) {
  const match = pattern.exec(source)
  assert.ok(match, `${label} must exist`)
  const openBraceIndex = source.indexOf('{', match.index)
  return readBracedBody(source, openBraceIndex)
}

const hasVisibleError = (body) => /(?:\b(?:error\w*|\w*Error)\.value\s*=|\bshowError\s*\(|\bshowToast\s*\(|\bElMessage\.error\s*\(|\balert\s*\()/.test(body)

test('display labels translate stable server keys', () => {
  assert.equal(labelRealm('foundation'), '筑基期')
  assert.equal(labelResource('spirit_stones'), '灵石')
  assert.equal(labelSectKind('normal'), '普通宗门')
  assert.equal(labelTechniqueType('mind'), '心法')
  assert.equal(labelTaskPreference('discipline-1'), '纪律修行')
  assert.equal(labelStatus('completed'), '已完成')
  assert.equal(labelResource('mind_state'), '心境')
  assert.equal(labelSlotType('body'), '身法')
  assert.equal(labelNpcRole('ordinary disciple'), '普通弟子')
  assert.equal(labelEventSummary('met'), '与普通弟子相遇')
})

test('display labels preserve unknown values and use Chinese empty fallbacks', () => {
  assert.equal(labelRealm('future_realm'), 'future_realm')
  assert.equal(labelRealm(''), '未知境界')
  assert.equal(labelResource(null), '未知资源')
})

test('slot labels keep body distinct from technique type labels', () => {
  assert.equal(TECHNIQUE_TYPE_LABELS.body, '炼体')
  assert.equal(SLOT_TYPE_LABELS.body, '身法')
  assert.notStrictEqual(SLOT_TYPE_LABELS, TECHNIQUE_TYPE_LABELS)
})

test('cultivation surfaces keep Chinese fallback and state copy', async () => {
  const files = [
    '../components/cultivation/CultivationStatusBar.vue',
    '../components/cultivation/RealmProgress.vue',
    '../components/cultivation/ResourceSummary.vue',
    '../components/cultivation/RewardToast.vue',
    '../components/cultivation/TechniqueSlotGrid.vue',
    '../components/cultivation/NpcTimeline.vue',
    '../components/cultivation/MapNode.vue',
    './Cultivation.vue',
    './World.vue',
    './Sects.vue',
    './Techniques.vue',
    './Npcs.vue',
    './Tribulations.vue',
    '../components/cultivation/TribulationProbability.vue',
    '../components/layout/AppLayout.vue',
    '../components/layout/Header.vue',
    '../components/layout/Sidebar.vue',
  ]
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))
  const source = sources.join('\n')

  for (const literal of [
    'Retry',
    'Cultivation data could not be loaded.',
    'Realm progress',
    'Resources',
    'Reward received',
    'Dismiss reward',
    'No technique slots available.',
    'NPC record',
    'Cultivation event',
    'Unknown node',
    'No description available.',
    'World node',
    'Toggle sidebar',
    'User menu',
    'Main navigation',
    'PLAN',
    'CULTIVATION',
    'REWARDS',
    'INSIGHTS',
    'Life Quest',
  ]) {
    const escapedLiteral = literal.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    assert.doesNotMatch(source, new RegExp("['\"]" + escapedLiteral + "['\"]"), `known English UI literal remains: ${literal}`)
  }

  assert.match(source, /正在读取|正在准备|正在计算/)
  assert.match(source, /重试/)
  assert.match(source, /暂无|尚未|未命名|未知/)
  assert.match(source, /获得奖励|修为|灵石|关系事件/)
})

test('cultivation pages prefer server labels before shared display labels', async () => {
  const files = [
    './Cultivation.vue',
    './World.vue',
    './Sects.vue',
    './Techniques.vue',
    './Tribulations.vue',
    '../components/cultivation/RealmProgress.vue',
    '../components/cultivation/ResourceSummary.vue',
    '../components/cultivation/NpcTimeline.vue',
  ]
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))
  const source = sources.join('\n')

  assert.match(source, /realm_label\s*\|\||[A-Za-z]+\.realm_label\s*\|\|/)
  assert.match(source, /kind_label\s*\|\||[A-Za-z]+\.kind_label\s*\|\|/)
  assert.match(source, /technique_type_label\s*\|\||[A-Za-z]+\.technique_type_label\s*\|\|/)
  assert.match(source, /required_realm_label\s*\|\||[A-Za-z]+\.required_realm_label\s*\|\|/)
  assert.match(source, /role_label\s*\|\||[A-Za-z]+\.role_label\s*\|\|/)
  assert.match(source, /labelRealm|labelResource|labelSectKind|labelTechniqueType|labelStatus/)
})

test('error messages translate backend details and machine codes', () => {
  assert.equal(
    getErrorMessage({ response: { data: { detail: 'Task not found' } } }),
    '任务不存在。',
  )
  assert.equal(
    getErrorMessage({ response: { data: { detail: 'SLOT_CONFLICT:DUPLICATE_TECHNIQUE' } } }),
    '同一功法不能重复配置。',
  )
  assert.equal(
    getErrorMessage({ response: { data: { detail: { message: '自定义错误。' } } } }),
    '自定义错误。',
  )
  assert.equal(
    getErrorMessage({ response: { data: { detail: '已经是中文。' } } }),
    '已经是中文。',
  )
  assert.equal(
    getErrorMessage({ request: {} }),
    '网络连接失败，请检查网络。',
  )
  assert.equal(
    getErrorMessage({ response: { status: 400, data: {} } }),
    '请求参数错误',
  )
  assert.equal(
    getErrorMessage({ response: { status: 404, data: {} } }),
    '资源不存在',
  )
  assert.equal(
    getErrorMessage({ response: { status: 409, data: {} } }),
    '请求冲突，请检查后重试',
  )
  assert.equal(
    getErrorMessage({ response: { status: 422, data: {} } }),
    '请求数据格式错误',
  )
  assert.equal(
    getErrorMessage({ response: { status: 500, data: {} } }),
    '服务器内部错误，请稍后重试',
  )
  assert.equal(
    getErrorMessage({ response: { status: 503, data: {} } }),
    '操作失败，请重试。',
  )
})

test('api and pages use the shared error converter', async () => {
  const apiSource = await readFile(new URL('../services/api.js', import.meta.url), 'utf8')
  const files = [
    '../components/notes/NoteViewer.vue',
    '../components/cultivation/TribulationProbability.vue',
    './Home.vue',
    './Todos.vue',
    './Backpack.vue',
    './Finance.vue',
    './FinanceAccounts.vue',
    './FinanceTransactions.vue',
    './FinanceDebts.vue',
    './FinanceBudgets.vue',
    './Projects.vue',
    './ProjectDetail.vue',
    './Notes.vue',
    './EditProfile.vue',
    './Profile.vue',
    './NotebookFileManage.vue',
    './Sects.vue',
    './Techniques.vue',
    './Shop.vue',
    './Login.vue',
    './Register.vue',
  ]
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))

  assert.match(apiSource, /getErrorMessage/)
  assert.match(apiSource, /getErrorMessage\(error\)/)
  for (const [file, source] of files.map((file, index) => [file, sources[index]])) {
    assert.doesNotMatch(source, /error\?\.response\?\.data\?\.detail|err\.response\?\.data\?\.detail|cause\.response\?\.data\?\.detail|response\.data\?\.detail/, `${file} reads raw backend error details`)
  }
})

test('api converts every non-401 HTTP and network error branch', async () => {
  const source = await readFile(new URL('../services/api.js', import.meta.url), 'utf8')
  const httpBranch = readBranchBody(
    source,
    /if \(!error\.config\?\.skipErrorToast && status && status !== 401\)\s*\{/g,
    'non-401 HTTP status branch',
  )
  const networkBranch = readBranchBody(
    source,
    /else if \(!error\.config\?\.skipErrorToast && !error\.response\)\s*\{/g,
    'network/no-response branch',
  )

  assert.match(httpBranch, /getErrorMessage\(error\)/)
  assert.match(networkBranch, /getErrorMessage\(error\)/)
})

test('Sects onError converts the request error before rendering it', async () => {
  const source = await readFile(new URL('./Sects.vue', import.meta.url), 'utf8')
  const { caughtName, body } = readNamedArrowCallback(source, 'onError')

  assert.match(body, new RegExp(`getErrorMessage\\(\\s*${caughtName}\\s*\\)`))
})

test('ProjectDetail converts every Promise catch error before showing it', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')
  const callbacks = readPromiseCatchCallbacks(source)

  assert.equal(callbacks.length, 2, 'ProjectDetail Promise catch callbacks must remain covered')
  for (const { caughtName, body } of callbacks) {
    assert.match(body, new RegExp(`getErrorMessage\\(\\s*${caughtName}\\s*\\)`))
  }
})

test('Home task and goal catches are treated as visible errors', async () => {
  const source = await readFile(new URL('./Home.vue', import.meta.url), 'utf8')
  const visibleHomeCatches = readCatchBlocks(source)
    .filter(({ body }) => hasVisibleError(body))
    .filter(({ body }) => /errorTasks|errorGoals/.test(body))

  assert.equal(visibleHomeCatches.length, 2, 'Home task and goal errors must be scanned')
  for (const { caughtName, body } of visibleHomeCatches) {
    assert.match(body, new RegExp(`getErrorMessage\\(\\s*${caughtName}\\s*\\)`))
  }
})

test('visible errors in task 4 page catches use the caught error converter', async () => {
  const files = [
    './Home.vue',
    './Todos.vue',
    './Backpack.vue',
    './Finance.vue',
    './FinanceAccounts.vue',
    './FinanceTransactions.vue',
    './FinanceDebts.vue',
    './FinanceBudgets.vue',
    './Notes.vue',
    './Projects.vue',
    './ProjectDetail.vue',
    './EditProfile.vue',
    './Profile.vue',
    './NotebookFileManage.vue',
    './Sects.vue',
    './Techniques.vue',
    './Login.vue',
    './Register.vue',
    './Shop.vue',
  ]
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))

  for (const [file, source] of files.map((file, index) => [file, sources[index]])) {
    for (const { caughtName, body } of readCatchBlocks(source)) {
      if (hasVisibleError(body)) {
        assert.match(body, new RegExp(`getErrorMessage\\(\\s*${caughtName}\\s*\\)`), `${file} has a visible catch error without the shared converter`)
      }
    }
  }
})
