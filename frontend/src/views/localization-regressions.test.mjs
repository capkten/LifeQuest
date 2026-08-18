import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import {
  labelRealm,
  labelResource,
  labelSectKind,
  labelStatus,
  labelTaskPreference,
  labelTechniqueType,
} from '../utils/displayLabels.js'
import { SLOT_TYPE_LABELS, TECHNIQUE_TYPE_LABELS } from '../locales/zh-CN.js'
import { getErrorMessage } from '../utils/errorMessage.js'

function readCatchBlocks(source) {
  const catches = []
  const catchPattern = /catch\s*\(\s*([A-Za-z_$][\w$]*)\s*\)\s*\{/g

  for (const match of source.matchAll(catchPattern)) {
    const bodyStart = match.index + match[0].length
    let depth = 1
    let quote = null
    let escaped = false
    let comment = null

    for (let index = bodyStart; index < source.length; index += 1) {
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
      if (depth === 0) {
        catches.push({ caughtName: match[1], body: source.slice(bodyStart, index) })
        break
      }
    }
  }

  return catches
}

const hasVisibleError = (body) => /(?:\b(?:error\w*|\w*Error)\.value\s*=|\bshowError\s*\(|\bshowToast\s*\(|\bElMessage\.error\s*\(|\balert\s*\()/.test(body)

test('display labels translate stable server keys', () => {
  assert.equal(labelRealm('foundation'), '筑基期')
  assert.equal(labelResource('spirit_stones'), '灵石')
  assert.equal(labelSectKind('normal'), '普通宗门')
  assert.equal(labelTechniqueType('mind'), '心法')
  assert.equal(labelTaskPreference('discipline-1'), '纪律修行')
  assert.equal(labelStatus('completed'), '已完成')
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
