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
