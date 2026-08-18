import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import {
  isTrustedLabel,
  labelRealm,
  labelResource,
  labelSectKind,
  labelSlotType,
  labelStatus,
  labelTaskPreference,
  labelTechniqueType,
  labelNpcRole,
  labelEventSummary,
  labelFromServer,
  labelLockReason,
  labelDifficulty,
  labelFrequency,
  labelAccountType,
  labelPeriod,
  labelSource,
  labelProjectStatus,
  labelTaskStatus,
  labelItemType,
  labelActionType,
  labelExchangeStatus,
  labelTransactionType,
} from '../utils/displayLabels.js'
import { SLOT_TYPE_LABELS, TECHNIQUE_TYPE_LABELS } from '../locales/zh-CN.js'
import { getErrorMessage } from '../utils/errorMessage.js'

const cultivationFiles = [
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

const legacyFiles = [
  './Login.vue',
  './Register.vue',
  './Home.vue',
  './Todos.vue',
  './Profile.vue',
  './Projects.vue',
  './Shop.vue',
  './EditProfile.vue',
  './NoteEditor.vue',
  './Notes.vue',
  './NotebookFileManage.vue',
  './Finance.vue',
  './FinanceAccounts.vue',
  './FinanceBudgets.vue',
  './FinanceDebts.vue',
  './FinanceTransactions.vue',
  './Backpack.vue',
  './BackpackHistory.vue',
  './ExchangeHistory.vue',
  './CoinHistory.vue',
  './Stats.vue',
]

const forbiddenLegacyLiterals = [
  'PERSONAL PROGRESS SYSTEM',
  'DAILY PROGRESS',
  'PLAYER SUMMARY',
  'Loading note...',
  'Wallet summary',
  'TIMELINE',
]

const allowedLegacyTemplateWords = new Set([
  'LifeQuest',
  'API',
  'EXP',
  'ID',
  'NPC',
  'URL',
])

function templateSource(source) {
  return source.match(/<template\b[^>]*>([\s\S]*?)<\/template>/i)?.[1] || ''
}

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

function readNamedFunction(source, name, parameter) {
  const pattern = new RegExp(`function\\s+${name}\\s*\\(\\s*${parameter}\\s*\\)\\s*\\{`)
  const match = pattern.exec(source)
  assert.ok(match, `${name} must exist`)
  const openBraceIndex = source.indexOf('{', match.index)
  const body = readBracedBody(source, openBraceIndex)
  return new Function(`return function ${name}(${parameter}) {${body}}`)()
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

function templateText(source) {
  const template = source.match(/<template\b[^>]*>([\s\S]*?)<\/template>/i)?.[1] || ''
  return template
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/{{[\s\S]*?}}/g, ' ')
    .replace(/<(?:[^'"<>]|"[^"]*"|'[^']*')*>/g, ' ')
}

function templateEnglish(source) {
  return templateText(source).match(/\b[A-Za-z][A-Za-z-]*\b/g) || []
}

test('legacy pages contain no forbidden English user-facing literals', async () => {
  const sources = await Promise.all(legacyFiles.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))

  for (const [file, source] of legacyFiles.map((file, index) => [file, sources[index]])) {
    const template = templateSource(source)
    for (const literal of forbiddenLegacyLiterals) {
      assert.doesNotMatch(template, new RegExp(literal.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `${file} still renders ${literal}`)
    }
  }
})

test('NoteEditor keeps dynamic status and errors localized', async () => {
  const source = await readFile(new URL('./NoteEditor.vue', import.meta.url), 'utf8')
  // Scan the raw script source so interpolated status strings remain visible.
  for (const pattern of [
    /['"`]Unsaved changes['"`]/,
    /['"`]Saving\.\.\.['"`]/,
    /['"`]Save failed · retry['"`]/,
    /`Saved\s+\$\{/,
    /['"`]All changes saved['"`]/,
    /`Notebook\s+\$\{/,
    /`Notebook\s+\$\{[^}]+\}\s*\/\s*Folder\s+\$\{/,
    /return\s+['"]Notes['"]/,
    /['"]Could not load this note\.['"]/,
    /['"]A title is required before saving\.['"]/,
    /['"]Save failed\. Try again\.['"]/,
    /['"]Image upload failed\.['"]/,
    /['"]You have unsaved changes\. Leave this note\?['"]/,
  ]) {
    assert.doesNotMatch(source, pattern, `NoteEditor still contains ${pattern}`)
  }
  assert.match(source, /getErrorMessage\(\s*error\s*,\s*'加载笔记失败，请重试。'\s*\)/)
  assert.match(source, /getErrorMessage\(\s*error\s*,\s*'保存失败，请重试。'\s*\)/)
  assert.match(source, /getErrorMessage\(\s*error\s*,\s*'图片上传失败，请重试。'\s*\)/)
  assert.match(source, /getErrorMessage\(\s*new Error\('TITLE_REQUIRED'\)\s*\)/)
  assert.doesNotMatch(source, /error\.message/)
})

test('EditProfile keeps section headings localized', async () => {
  const template = templateSource(await readFile(new URL('./EditProfile.vue', import.meta.url), 'utf8'))
  assert.doesNotMatch(template, /PROFILE SETTINGS/)
  assert.doesNotMatch(template, /ACCOUNT INFO/)
  assert.match(template, /资料设置/)
  assert.match(template, /账户信息/)
})

test('ProjectDetail close buttons use Chinese aria labels', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', import.meta.url), 'utf8')
  assert.doesNotMatch(source, /aria-label="Close"/)
  assert.equal((source.match(/aria-label="关闭"/g) || []).length, 5)
})

test('NPC meeting and sect preference controls keep stable keys internal', async () => {
  const [npcs, sects, timeline] = await Promise.all([
    readFile(new URL('./Npcs.vue', import.meta.url), 'utf8'),
    readFile(new URL('./Sects.vue', import.meta.url), 'utf8'),
    readFile(new URL('../components/cultivation/NpcTimeline.vue', import.meta.url), 'utf8'),
  ])

  assert.doesNotMatch(npcs, /sect-1-normal-1/)
  assert.match(npcs, /cultivationService\.getSects\(\)/)
  assert.match(npcs, /<option v-for="sect in sectOptions"/)
  assert.match(npcs, /\{\{ sect\.name \}\}/)
  assert.doesNotMatch(sects, /<input v-model\.trim="filters\.task_preference"/)
  assert.match(sects, /<select v-model="filters\.task_preference"/)
  assert.match(sects, /taskPreferenceOptions/)
  assert.doesNotMatch(timeline, /roleLabel !== '未知身份' \? roleLabel : firstText\(item\?\.description/)
})

test('all task 6 legacy page templates contain no bare English user-facing text', async () => {
  const sources = await Promise.all(legacyFiles.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))

  for (const [file, source] of legacyFiles.map((file, index) => [file, sources[index]])) {
    const english = templateEnglish(source).filter((word) => !allowedLegacyTemplateWords.has(word))
    assert.deepEqual(english, [], `${file} contains bare English template text: ${english.join(', ')}`)
  }
})

test('legacy pages do not render stable enum keys directly', async () => {
  const sources = await Promise.all(legacyFiles.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))
  const directEnumPattern = /{{\s*(?:[A-Za-z_$][\w$]*\??\.)?(?:difficulty|frequency|account_type|period|source|status|type|item_type|realm_key)\s*}}/

  for (const [file, source] of legacyFiles.map((file, index) => [file, sources[index]])) {
    assert.doesNotMatch(templateSource(source), directEnumPattern, `${file} renders a stable enum key directly`)
  }
})

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
  assert.equal(labelDifficulty('hard'), '困难')
  assert.equal(labelFrequency('weekly'), '每周')
  assert.equal(labelAccountType('credit'), '信用卡')
  assert.equal(labelPeriod('monthly'), '每月')
  assert.equal(labelSource('checkin'), '签到')
  assert.equal(labelProjectStatus('archived'), '已归档')
  assert.equal(labelTaskStatus('pending'), '待开始')
  assert.equal(labelItemType('collectible'), '收藏品')
  assert.equal(labelActionType('discard'), '丢弃')
  assert.equal(labelActionType('add'), '添加')
  assert.equal(labelActionType('unequip'), '卸下')
  assert.equal(labelExchangeStatus('refunded'), '已退款')
  assert.equal(labelTransactionType('transfer'), '转账')
})

test('legacy display labels use Chinese fallbacks for unknown and empty values', () => {
  for (const [label, fallback] of [
    [labelDifficulty, '未知难度'],
    [labelFrequency, '未知频率'],
    [labelAccountType, '未知账户类型'],
    [labelPeriod, '未知周期'],
    [labelSource, '其他'],
    [labelProjectStatus, '未知项目状态'],
    [labelTaskStatus, '未知任务状态'],
    [labelItemType, '未知物品类型'],
    [labelActionType, '未知动作'],
    [labelExchangeStatus, '未知兑换状态'],
    [labelTransactionType, '未知交易类型'],
  ]) {
    assert.equal(label('future_stable_key'), fallback)
    assert.equal(label(''), fallback)
    assert.equal(label(null), fallback)
  }
})

test('legacy item and coin history fallbacks stay localized', async () => {
  const [backpackSource, coinHistorySource] = await Promise.all([
    readFile(new URL('./Backpack.vue', import.meta.url), 'utf8'),
    readFile(new URL('./CoinHistory.vue', import.meta.url), 'utf8'),
  ])

  assert.match(backpackSource, /shopItem\?\.name \|\| '未知商品'/)
  assert.match(backpackSource, /shopItem\?\.name \|\| '该物品'/)
  assert.match(coinHistorySource, /tx\.description \|\| sourceLabel\(tx\.source\)/)
  assert.doesNotMatch(coinHistorySource, /tx\.description \|\| tx\.source/)
})

test('display labels hide unknown stable keys and use Chinese empty fallbacks', async () => {
  for (const [label, fallback] of [
    [labelRealm, '未知境界'],
    [labelSectKind, '未知宗门类型'],
    [labelTechniqueType, '未知功法类型'],
    [labelTaskPreference, '未知任务偏好'],
    [labelStatus, '未知状态'],
    [labelResource, '未知资源'],
    [labelSlotType, '未知格子类型'],
    [labelNpcRole, '未知身份'],
    [labelEventSummary, '未知事件'],
  ]) {
    assert.equal(label('future_stable_key'), fallback)
    assert.equal(label(''), fallback)
    assert.equal(label(null), fallback)
  }
  const displayLabels = await import('../utils/displayLabels.js')
  assert.equal(displayLabels.labelLockReason?.('future_lock_reason'), '未知渡劫状态')
  assert.equal(displayLabels.labelLockReason?.(''), '未知渡劫状态')
})

test('server labels only override fallbacks when they are localized', () => {
  const cases = [
    [{ realm_key: 'future_realm', realm_label: 'future_realm' }, 'realm_label', 'realm_key', labelRealm, '未知境界'],
    [{ kind: 'future_kind', kind_label: 'future_kind' }, 'kind_label', 'kind', labelSectKind, '未知宗门类型'],
    [{ technique_type: 'future_type', technique_type_label: 'future_type' }, 'technique_type_label', 'technique_type', labelTechniqueType, '未知功法类型'],
    [{ task_preference: 'future_preference', task_preference_label: 'future_preference' }, 'task_preference_label', 'task_preference', labelTaskPreference, '未知任务偏好'],
    [{ status: 'future_status', status_label: 'future_status' }, 'status_label', 'status', labelStatus, '未知状态'],
    [{ resource: 'future_resource', resource_label: 'future_resource' }, 'resource_label', 'resource', labelResource, '未知资源'],
    [{ slot_type: 'future_slot', slot_type_label: 'future_slot' }, 'slot_type_label', 'slot_type', labelSlotType, '未知格子类型'],
    [{ role: 'future_role', role_label: 'future_role' }, 'role_label', 'role', labelNpcRole, '未知身份'],
    [{ event_key: 'future_event', summary_label: 'future_event' }, 'summary_label', 'event_key', labelEventSummary, '未知事件'],
    [{ lock_reason: 'future_lock', lock_reason_label: 'future_lock' }, 'lock_reason_label', 'lock_reason', labelLockReason, '未知渡劫状态'],
  ]

  for (const [record, labelKey, valueKey, fallback, expected] of cases) {
    assert.equal(labelFromServer(record, labelKey, record[valueKey], fallback), expected)
  }
  assert.equal(labelFromServer({ realm_key: 'foundation', realm_label: '筑基期' }, 'realm_label', 'foundation', labelRealm), '筑基期')
  assert.equal(labelFromServer({ realm_key: 'foundation', realm_label: '服务器中文境界' }, 'realm_label', 'foundation', labelRealm), '服务器中文境界')
  assert.equal(isTrustedLabel('foundation', 'foundation'), false)
  assert.equal(isTrustedLabel('筑基期', 'foundation'), true)
})

test('slot labels keep body distinct from technique type labels', () => {
  assert.equal(TECHNIQUE_TYPE_LABELS.body, '炼体')
  assert.equal(SLOT_TYPE_LABELS.body, '身法')
  assert.notStrictEqual(SLOT_TYPE_LABELS, TECHNIQUE_TYPE_LABELS)
})

test('cultivation surfaces keep Chinese fallback and state copy', async () => {
  const sources = await Promise.all(cultivationFiles.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))

  for (const [file, source] of cultivationFiles.map((file, index) => [file, sources[index]])) {
    const english = templateEnglish(source).filter((word) => !['EXP', 'LifeQuest', 'NPC'].includes(word))
    assert.deepEqual(english, [], `${file} contains bare English template text: ${english.join(', ')}`)
  }

  assert.match(sources.join('\n'), /正在读取|正在准备|正在计算/)
  assert.match(sources.join('\n'), /重试/)
  assert.match(sources.join('\n'), /暂无|尚未|未命名|未知/)
  assert.match(sources.join('\n'), /获得奖励|修为|灵石|关系事件/)
})

test('cultivation pages prefer server labels before shared display labels', async () => {
  const assertions = {
    './Cultivation.vue': [/labelFromServer/, /labelRealm/],
    './World.vue': [/labelFromServer/, /labelStatus/],
    './Sects.vue': [
      /labelFromServer/,
      /labelSectKind/,
      /labelTaskPreference/,
      /labelRealm/,
      /labelStatus/,
      /labelNpcRole/,
    ],
    './Techniques.vue': [
      /labelFromServer/,
      /labelTechniqueType/,
      /labelRealm/,
    ],
    './Tribulations.vue': [/labelFromServer/, /labelRealm/],
    '../components/cultivation/CultivationStatusBar.vue': [/labelFromServer/, /labelResource/],
    '../components/cultivation/RealmProgress.vue': [/labelFromServer/, /labelRealm/],
    '../components/cultivation/ResourceSummary.vue': [/labelFromServer/, /labelResource/],
    '../components/cultivation/RewardToast.vue': [/labelFromServer/, /labelResource/],
    '../components/cultivation/MapNode.vue': [/labelFromServer/, /labelStatus/, /labelRealm/],
    '../components/cultivation/NpcTimeline.vue': [/labelFromServer/, /labelNpcRole/, /labelEventSummary/],
    './Npcs.vue': [/labelFromServer/, /labelNpcRole/],
    '../components/cultivation/TribulationProbability.vue': [/labelFromServer/, /labelRealm/, /labelLockReason/],
  }

  for (const [file, patterns] of Object.entries(assertions)) {
    const source = await readFile(new URL(file, import.meta.url), 'utf8')
    for (const pattern of patterns) assert.match(source, pattern, `${file} must prefer server labels before fallback`)
  }
})

test('cultivation resource projections preserve server labels', async () => {
  const [cultivation, sidebar] = await Promise.all([
    readFile(new URL('./Cultivation.vue', import.meta.url), 'utf8'),
    readFile(new URL('../components/layout/Sidebar.vue', import.meta.url), 'utf8'),
  ])

  assert.match(cultivation, /const resources = computed\(\(\) => projectResources\(overview\.value\)\)/)
  assert.match(cultivation, /function projectResources\(overview\)/)
  assert.match(sidebar, /labelFromServer\(cultivationOverview,\s*['"]spirit_stones_label['"],\s*['"]spirit_stones['"],\s*labelResource\)/)
})

test('cultivation resource projection merges nested resources with top-level labels at runtime', async () => {
  const source = await readFile(new URL('./Cultivation.vue', import.meta.url), 'utf8')
  const projectResources = readNamedFunction(source, 'projectResources', 'overview')
  const projected = projectResources({
    resources: { spirit_stones: 10, merit: 4 },
    spirit_stones: 12,
    spirit_stones_label: '服务器中文灵石',
    cultivation: 88,
    cultivation_label: '服务器中文修为',
    merit_label: '服务器中文功德',
  })

  assert.equal(projected.spirit_stones, 12)
  assert.equal(projected.merit, 4)
  assert.equal(projected.spirit_stones_label, '服务器中文灵石')
  assert.equal(projected.cultivation_label, '服务器中文修为')
  assert.equal(projected.merit_label, '服务器中文功德')
  assert.equal(labelFromServer(projected, 'spirit_stones_label', 'spirit_stones', labelResource), '服务器中文灵石')
})

test('Sidebar sanitizes the server realm label through the shared helper', async () => {
  const source = await readFile(new URL('../components/layout/Sidebar.vue', import.meta.url), 'utf8')
  assert.match(source, /labelFromServer\(cultivationOverview,\s*['"]realm_label['"],\s*cultivationOverview\?\.realm_key,\s*labelRealm\)/)
  assert.doesNotMatch(source, /cultivationOverview\?\.realm_label\s*\|\|/)
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
  assert.equal(getErrorMessage(new Error('TITLE_REQUIRED')), '保存前请填写标题。')
  assert.equal(getErrorMessage(new Error('NOTEBOOK_REQUIRED')), '请先选择笔记本。')
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

test('parameterized realm lock errors use localized realm labels', () => {
  const cases = [
    ['TECHNIQUE_REALM_REQUIRED:foundation', '境界不足，需要达到筑基期后再学习或配置功法。'],
    ['TECHNIQUE_REALM_REQUIRED:technique requires golden_core realm', '境界不足，需要达到金丹期后再学习或配置功法。'],
    ['SLOT_REALM_REQUIRED:golden_core', '境界不足，需要达到金丹期后购买功法格。'],
  ]

  for (const [detail, expected] of cases) {
    assert.equal(getErrorMessage({ response: { data: { detail } } }), expected)
  }
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
    './NoteEditor.vue',
    './BackpackHistory.vue',
    './ExchangeHistory.vue',
    './CoinHistory.vue',
    './Stats.vue',
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
    './NoteEditor.vue',
    './BackpackHistory.vue',
    './ExchangeHistory.vue',
    './CoinHistory.vue',
    './Stats.vue',
  ]
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))

  for (const [file, source] of files.map((file, index) => [file, sources[index]])) {
    for (const { caughtName, body } of readCatchBlocks(source)) {
      if (hasVisibleError(body)) {
        assert.match(body, new RegExp(`getErrorMessage\\(\\s*${caughtName}(?:\\s*,|\\s*\\))`), `${file} has a visible catch error without the shared converter`)
      }
    }
  }
})
