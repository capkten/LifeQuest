import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import * as vue from 'vue'
import { compileTemplate } from '@vue/compiler-sfc'
import { getErrorMessage } from '../utils/errorMessage.js'

const viewsDirectory = new URL('./', import.meta.url)

test('cultivation backend lock details are translated into actionable Chinese feedback', () => {
  const cases = [
    ['sect is locked', '宗门当前处于锁定状态，请先完成解锁条件。'],
    ['messenger contact required before trial', '请先联系入门使者，再开始宗门试炼。'],
    ['leave current sect before joining another', '请先退出当前宗门，再加入新的宗门。'],
    ['messenger contact required before meeting NPC', '请先联系宗门使者，再与 NPC 相遇。'],
    ['NPC meeting cooldown active', 'NPC 相遇仍在冷却中，请稍后再试。'],
    ['NPC population capacity reached', 'NPC 人口槽位已满，请选择其他槽位。'],
    ['Incorrect username or password', '用户名或密码错误，请检查后重试。'],
  ]

  for (const [detail, expected] of cases) {
    assert.equal(getErrorMessage({ response: { data: { detail } } }), expected, detail)
  }
})

test('login and register failures render an inline alert in addition to toast feedback', async () => {
  const [login, register] = await Promise.all([
    readFile(new URL('./Login.vue', import.meta.url), 'utf8'),
    readFile(new URL('./Register.vue', import.meta.url), 'utf8'),
  ])

  for (const source of [login, register]) {
    assert.match(source, /v-if="authError"/)
    assert.match(source, /role="alert"/)
    assert.match(source, /authError\.value\s*=\s*getErrorMessage\(error\)/)
    assert.match(source, /authError\.value\s*=\s*null/)
  }
})

test('cultivation interaction pages render toast feedback states', async () => {
  const files = ['./Sects.vue', './Npcs.vue', './Cultivation.vue']
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, viewsDirectory), 'utf8')))

  for (const [file, source] of files.map((file, index) => [file, sources[index]])) {
    assert.match(source, /const \{[^}]*successToast[^}]*showSuccess[^}]*\}\s*=\s*useToast\(\)/, `${file} must expose success toast state`)
    assert.match(source, /const \{[^}]*errorToast[^}]*showError[^}]*\}\s*=\s*useToast\(\)/, `${file} must expose error toast state`)
    assert.match(source, /v-if="successToast"[\s\S]*role="status"/, `${file} must render success feedback`)
    assert.match(source, /v-if="errorToast"[\s\S]*role="alert"/, `${file} must render error feedback`)
  }
})

test('cultivation interaction feedback uses body-level floating toast popups', async () => {
  const files = ['./Sects.vue', './Npcs.vue', './Cultivation.vue']
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, viewsDirectory), 'utf8')))

  for (const [file, source] of files.map((file, index) => [file, sources[index]])) {
    assert.match(source, /<Teleport to="body">[\s\S]*?v-if="successToast"[\s\S]*?class="(?:toast|success-toast|cultivation-toast)/, `${file} must render success as a floating toast`)
    assert.match(source, /<Teleport to="body">[\s\S]*?v-if="errorToast"[\s\S]*?class="(?:toast|error-toast|cultivation-toast)/, `${file} must render errors as a floating toast`)
    assert.match(source, /<Transition name="toast">/, `${file} must animate toast feedback`)
    assert.doesNotMatch(source, /class="cultivation-state cultivation-state--(?:success|error)"[^>]*>\{\{ (?:successToast|errorToast) \}\}/, `${file} must not render toast feedback as an inline state`)
  }
})

test('sect business locks remain clickable so blocked reasons can be shown', async () => {
  const source = await readFile(new URL('./Sects.vue', viewsDirectory), 'utf8')

  assert.match(source, /:disabled="busyId !== null"/)
  assert.doesNotMatch(source, /:aria-disabled="busyId !== null \|\| sect\./)
})

test('sidebar places accounting directly below home', async () => {
  const source = await readFile(new URL('../components/layout/Sidebar.vue', import.meta.url), 'utf8')
  const homeIndex = source.indexOf('to="/"')
  const financeIndex = source.indexOf('to="/finance"')
  const todosIndex = source.indexOf('to="/todos"')

  assert.ok(homeIndex >= 0, 'home navigation must remain present')
  assert.ok(financeIndex > homeIndex, 'accounting must follow home')
  assert.ok(financeIndex < todosIndex, 'accounting must be directly below home')
})

test('todo metadata badges share a compact row with each title', async () => {
  const source = await readFile(new URL('./Todos.vue', viewsDirectory), 'utf8')

  assert.equal((source.match(/class="todo-card-title-row"/g) || []).length, 3)
  assert.match(source, /todo-card-title-row[\s\S]*todo-card-title[\s\S]*difficulty-badge[\s\S]*frequency-badge/)
  assert.match(source, /todo-card-title-row[\s\S]*todo-card-title[\s\S]*priority-badge[\s\S]*difficulty-badge[\s\S]*status-badge/)
})

test('todo card titles use a readable large heading size', async () => {
  const source = await readFile(new URL('./Todos.vue', viewsDirectory), 'utf8')

  assert.match(source, /\.todo-card-title\s*\{[^}]*font-size:\s*var\(--font-size-xl\)/)
  assert.match(source, /\.todo-card-title\s*\{[^}]*font-weight:\s*700/)
})

test('android release workflow and in-app update contract are present', async () => {
  const [packageJson, envExample, workflow, app] = await Promise.all([
    readFile(new URL('../../package.json', import.meta.url), 'utf8'),
    readFile(new URL('../../.env.android.example', import.meta.url), 'utf8'),
    readFile(new URL('../../../.github/workflows/android-release.yml', import.meta.url), 'utf8'),
    readFile(new URL('../App.vue', import.meta.url), 'utf8'),
  ])

  assert.match(packageJson, /"@capacitor\/app"/)
  assert.match(packageJson, /"@capacitor\/browser"/)
  assert.match(envExample, /VITE_ANDROID_UPDATE_MANIFEST_URL=/)
  assert.match(workflow, /bundleRelease/)
  assert.match(workflow, /latest\.json/)
  assert.match(workflow, /ANDROID_KEYSTORE_BASE64/)
  assert.match(app, /VITE_ANDROID_UPDATE_MANIFEST_URL|UpdatePrompt/)
})

function compileRender(source) {
  const result = compileTemplate({
    source,
    filename: 'FinanceTransactions.vue',
    id: 'finance-support-loading',
  })
  assert.deepEqual(result.errors, [], 'finance support loading template must compile')
  const imports = result.code.match(/^import \{ ([\s\S]*?) \} from "vue"\r?\n\r?\n/)
  assert.ok(imports, 'compiled template must expose Vue helpers')
  const aliases = imports[1].split(', ').map((entry) => entry.split(' as ').at(-1))
  const values = imports[1].split(', ').map((entry) => vue[entry.split(' as ')[0]])
  const code = result.code
    .replace(imports[0], '')
    .replace('export function render', 'function render')
  return Function(...aliases, `${code}\nreturn render`)(...values)
}

test('notes discovery controls use readable Chinese labels', async () => {
  const source = await readFile(new URL('./Notes.vue', viewsDirectory), 'utf8')

  assert.match(source, /aria-label="\u6392\u5e8f"/)
  assert.match(source, />\u6700\u8fd1\u6253\u5f00<\/option>/)
  assert.match(source, />\u6700\u8fd1\u66f4\u65b0<\/option>/)
  assert.match(source, /aria-label="\u7b14\u8bb0\u672c\u7b5b\u9009"/)
  assert.doesNotMatch(source, /\u93ba\u6391\u7c2d|\u93c8\u5100\u677f\u621a\u5f48\u6d93\u5bee/)
})

test('shop search overrides the desktop flex basis on mobile', async () => {
  const source = await readFile(new URL('./Shop.vue', viewsDirectory), 'utf8')

  assert.match(source, /@media \(max-width: 767px\) \{[\s\S]*?\.shop-search \{[\s\S]*?flex: 0 0 44px[\s\S]*?height: 44px/)
  assert.match(source, /@media \(max-width: 767px\) \{[\s\S]*?\.shop-search input \{[\s\S]*?height: 100%/)
})

test('notebook mobile rows collapse actions into a compact menu and pad previews', async () => {
  const [tree, viewer] = await Promise.all([
    readFile(new URL('../components/notes/NoteTree.vue', import.meta.url), 'utf8'),
    readFile(new URL('../components/notes/NoteViewer.vue', import.meta.url), 'utf8'),
  ])

  assert.match(tree, /note-tree__mobile-trigger/)
  assert.match(tree, /mobileMenuOpen/)
  for (const action of ['create-folder', 'create-note', 'rename', 'move', 'delete']) {
    assert.match(tree, new RegExp(`emitMobile\\('${action}'`))
  }
  assert.match(tree, /@media \(max-width: 767px\)[\s\S]*?\.note-tree__actions\s*\{[\s\S]*?display:\s*none/)
  assert.match(viewer, /\.viewer-content\s*\{[^}]*padding:\s*var\(--spacing-xl\)\s+var\(--spacing-lg\)/)
  assert.match(viewer, /\.viewer-content\s*\{[^}]*padding:\s*var\(--spacing-xl\)\s+var\(--spacing-lg\)\s+var\(--spacing-xl\)/)
})

test('business-locked todo and shop actions stay clickable and explain their lock', async () => {
  const [todos, shop] = await Promise.all([
    readFile(new URL('./Todos.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./Shop.vue', viewsDirectory), 'utf8'),
  ])

  assert.match(todos, /function explainBlocked\(/)
  assert.match(todos, /function explainBlocked\(message\)[\s\S]*showError\(message\)/)
  assert.match(todos, /已完成|不可完成/)
  assert.match(todos, /aria-disabled/)
  assert.match(shop, /function explainBlocked\(/)
  assert.match(shop, /金币不足|售罄/)
  assert.match(shop, /aria-disabled/)
})

test('todo habit completion uses the server completed_today field for all lock states', async () => {
  const source = await readFile(new URL('./Todos.vue', viewsDirectory), 'utf8')

  assert.match(source, /'todo-card--completed': habit\.completed_today/)
  assert.match(source, /'complete-btn--done': habit\.completed_today/)
  assert.match(source, /:aria-disabled="habit\.completed_today"/)
  assert.match(source, /if \(habit\.completed_today\)/)
  assert.doesNotMatch(source, /habit\.is_active/)
})

test('backpack business actions expose a visible blocked-action feedback path', async () => {
  const source = await readFile(new URL('./Backpack.vue', viewsDirectory), 'utf8')

  assert.match(source, /function explainBlocked\(/)
  assert.match(source, /不可使用|不可装备|不可丢弃/)
  assert.match(source, /aria-disabled/)
})

test('cross-item in-flight actions explain the shared lock without submitting', async () => {
  const [todos, shop, backpack, project] = await Promise.all([
    readFile(new URL('./Todos.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./Shop.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./Backpack.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8'),
  ])

  assert.match(todos, /if \(completingId\.value\) \{\s*explainBlocked\(/)
  assert.match(todos, /if \(completingSubtaskId\.value\) \{\s*explainBlocked\(/)
  assert.match(shop, /if \(purchasingId\.value\) \{\s*explainBlocked\(/)
  assert.match(backpack, /if \(actionId\.value\) \{\s*explainBlocked\(/)
  assert.match(project, /if \(completingTaskId\.value\) \{\s*showError\(/)
})

test('subtask deletion blocks cross-item requests with handler feedback and loading semantics', async () => {
  const source = await readFile(new URL('./Todos.vue', viewsDirectory), 'utf8')
  const handler = source.match(/async function deleteSubtask\(subtask, taskId\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(handler, 'deleteSubtask handler must remain available for the template contract')
  assert.match(handler, /if \(deletingSubtaskId\.value\) \{\s*explainBlocked\(['"]已有其他子任务正在删除，请等待完成后再试。['"]\);\s*return\s*\}/)
  assert.match(source, /:aria-disabled="Boolean\(deletingSubtaskId\)"/)
  assert.match(source, /v-if="deletingSubtaskId === subtask\.id"[\s\S]*loading-spinner/)
})

test('subtask completion uses the settlement endpoint', async () => {
  const service = await readFile(new URL('../services/todo.js', viewsDirectory), 'utf8')

  assert.match(service, /api\.post\(`\/todos\/subtasks\/\$\{subtaskId\}\/complete`\)/)
  assert.doesNotMatch(service, /api\.put\(`\/todos\/subtasks\/\$\{subtaskId\}`\s*,\s*\{ is_completed: true \}\)/)
})

test('home daily summary keeps request failures separate from the legitimate empty state', async () => {
  const source = await readFile(new URL('./Home.vue', viewsDirectory), 'utf8')

  assert.match(source, /dailyError/)
  assert.match(source, /v-else-if="dailyError"[\s\S]*重试[\s\S]*fetchDailySummary/)
  assert.match(source, /dailyError\.value\s*=\s*getErrorMessage\(e/)
})

test('notes preserve prior results and expose retryable errors for search and discovery', async () => {
  const source = await readFile(new URL('./Notes.vue', viewsDirectory), 'utf8')

  assert.match(source, /searchError/)
  assert.match(source, /discoveryError/)
  assert.match(source, /searchRequestId|searchSequence|searchAbortController/)
  assert.match(source, /discoveryRequestId|discoverySequence|discoveryAbortController/)
  assert.match(source, /searchError[\s\S]*重试|重试[\s\S]*searchError/)
  assert.match(source, /discoveryError[\s\S]*重试|重试[\s\S]*discoveryError/)
  assert.doesNotMatch(source, /catch\s*\([^)]*\)\s*\{\s*searchResults\.value\s*=\s*\[\]/)
})

test('note editor cannot save an unhydrated document after load failure', async () => {
  const source = await readFile(new URL('./NoteEditor.vue', viewsDirectory), 'utf8')

  assert.match(source, /loadError/)
  assert.match(source, /加载笔记失败，请重试/)
  assert.match(source, /loadError[\s\S]*重试|重试[\s\S]*loadError/)
  assert.match(source, /!hydrated\.value/)
  assert.match(source, /hydrated\.value\s*=\s*false[\s\S]*catch[\s\S]*loadError\.value/)
  assert.match(source, /:disabled="[^"]*hydrated[^"]*"|v-if="loadError"/)
})

test('protected list pages retain data and expose explicit refresh errors', async () => {
  const files = [
    './Finance.vue',
    './FinanceTransactions.vue',
    './CoinHistory.vue',
    './Calendar.vue',
    './Home.vue',
    './Profile.vue',
    './Stats.vue',
  ]
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, viewsDirectory), 'utf8')))

  for (const [file, source] of files.map((file, index) => [file, sources[index]])) {
    assert.match(source, /(?:refresh|load|fetch|dashboard|transactions|history|events|detail|profile|task|habit|coin)[A-Za-z]*Error|\berror\b/, `${file} needs an explicit load error state`)
    assert.match(source, /重试/, `${file} needs a retry control`)
    assert.doesNotMatch(source, /catch\s*\([^)]*\)\s*\{[\s\S]{0,180}(?:transactions|records|events|stats|achievements|dashboard|overview|taskTrends|habitStats|coinTrends)\.value\s*=\s*\[\]/, `${file} must not turn a failed refresh into empty success data`)
  }
})

test('note, finance and stats filters apply only the latest response', async () => {
  const files = [
    './Notes.vue',
    './FinanceTransactions.vue',
    './CoinHistory.vue',
    './NoteEditor.vue',
    './Stats.vue',
  ]
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, viewsDirectory), 'utf8')))

  for (const [file, source] of files.map((file, index) => [file, sources[index]])) {
    assert.match(source, /requestId|requestSequence|requestSeq|AbortController|sequence/, `${file} needs latest-response protection`)
  }
})

test('note workspace writes use independent action locks and visible failures', async () => {
  const source = await readFile(new URL('../composables/useNoteWorkspace.js', import.meta.url), 'utf8')

  assert.match(source, /actionLocks|mutationLocks|withActionLock/)
  assert.match(source, /createFolder|createNote|renameNode|moveNode|deleteNode/)
  assert.match(source, /error\.value\s*=\s*cause/)
  assert.match(source, /finally[\s\S]*(actionLocks|mutationLocks)/)
})

test('profile keeps partial data failures visible and retryable', async () => {
  const source = await readFile(new URL('./Profile.vue', viewsDirectory), 'utf8')

  assert.match(source, /titlesError/)
  assert.match(source, /titlesError[\s\S]*重试[\s\S]*fetchTitles|重试[\s\S]*fetchTitles[\s\S]*titlesError/)
  assert.match(source, /Promise\.allSettled/)
  assert.doesNotMatch(source, /todoService\.getTasks\(\)\.catch\(\(\) => \[\]\)/)
  assert.doesNotMatch(source, /todoService\.getHabits\(\)\.catch\(\(\) => \[\]\)/)
  assert.match(source, /tasksError|profileError/)
  assert.match(source, /titlesRequestId|profileRequestId/)
})

test('notebook workspace and viewer ignore stale responses after selection changes', async () => {
  const [workspace, view] = await Promise.all([
    readFile(new URL('../composables/useNoteWorkspace.js', import.meta.url), 'utf8'),
    readFile(new URL('./NotebookFileManage.vue', viewsDirectory), 'utf8'),
  ])

  assert.match(workspace, /treeRequestId|treeSequence|treeAbortController/)
  assert.match(workspace, /requestId\s*!==\s*treeRequestId|treeRequestId\s*!==\s*requestId/)
  assert.match(workspace, /selectionRequestId|selectionSequence|selectionGeneration/)
  assert.match(workspace, /selectionRequestId\s*(?:\+\+|\+=\s*1)|selectionSequence\s*(?:\+\+|\+=\s*1)|selectionGeneration\s*(?:\+\+|\+=\s*1)/)
  assert.match(view, /viewerRequestId|viewerSequence|viewerAbortController/)
  assert.match(view, /requestId\s*!==\s*viewerRequestId|viewerRequestId\s*!==\s*requestId/)
})

test('pagination refreshes release stale loading locks and expose retryable failures', async () => {
  const [finance, coins, stats] = await Promise.all([
    readFile(new URL('./FinanceTransactions.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./CoinHistory.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./Stats.vue', viewsDirectory), 'utf8'),
  ])

  assert.match(finance, /loadMoreError/)
  assert.match(finance, /filterGeneration/)
  assert.match(finance, /generation !== filterGeneration/)
  assert.match(finance, /supportLoading/)
  assert.match(finance, /transactions\.length === 0 && !supportError && !supportLoading/)
  assert.match(finance, /transactions\.length === 0 && supportError/)
  assert.match(finance, /transactions\.length === 0 && supportLoading/)
  assert.match(finance, /filter\(Boolean\)\.join/)
  assert.match(coins, /loadMoreError/)
  assert.match(coins, /filterGeneration/)
  assert.match(coins, /loadingMore\.value = false/)
  assert.match(finance, /hasMore\.value = false/)
  assert.match(coins, /hasMore\.value = false/)
  assert.match(stats, /function syncGlobalError\(/)
  assert.match(stats, /syncGlobalError\(\)/)
  assert.match(stats, /loadingOverview/)
  assert.match(stats, /loadingLevel/)
})

test('finance support loading renders and clears only for the latest request', async () => {
  const source = await readFile(new URL('./FinanceTransactions.vue', viewsDirectory), 'utf8')
  const loadingTemplate = source.match(/<div v-if="supportLoading"[^>]*>[\s\S]*?<\/div>/)?.[0]
  assert.ok(loadingTemplate, 'finance support loading must be visible in the template')

  const render = compileRender(loadingTemplate)
  const loadingNode = render({ supportLoading: true }, [])
  assert.equal(loadingNode.type, 'div')
  assert.equal(loadingNode.props['aria-live'], 'polite')
  assert.equal(loadingNode.children, '正在加载账户和分类...')
  assert.equal(render({ supportLoading: false }, []).type, Symbol.for('v-cmt'))

  const supportHandler = source.match(/async function fetchSupportData\(\) \{([\s\S]*?)\n\}/)?.[1]
  assert.ok(supportHandler, 'fetchSupportData handler must remain available')
  assert.match(supportHandler, /supportLoading\.value = true/)
  assert.match(supportHandler, /if \(requestId !== supportRequestId\) return/)
  assert.match(supportHandler, /try \{[\s\S]*Promise\.allSettled/)
  assert.match(supportHandler, /finally \{[\s\S]*supportLoading\.value = false/)
})

test('note editor leaves loading state when opening a new note route', async () => {
  const source = await readFile(new URL('./NoteEditor.vue', viewsDirectory), 'utf8')

  assert.match(source, /if \(!noteId\.value\) \{[\s\S]*loading\.value = false[\s\S]*hydrated\.value = true/)
})

test('project mutations use independent locks and phase deletion preserves task ownership', async () => {
  const [source, service] = await Promise.all([
    readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8'),
    readFile(new URL('../services/project.js', import.meta.url), 'utf8'),
  ])

  assert.match(source, /const savePending = ref\(false\)/)
  assert.match(source, /const phasePending = ref\(false\)/)
  assert.match(source, /const deletePending = ref\(false\)/)
  assert.match(source, /const finishing = ref\(false\)/)
  assert.match(source, /if \(savePending\.value\) \{[\s\S]*return[\s\S]*\}/)
  assert.match(source, /if \(phasePending\.value\) \{[\s\S]*return[\s\S]*\}/)
  assert.match(source, /if \(deletePending\.value\) \{[\s\S]*return[\s\S]*\}/)
  assert.match(source, /finally \{[\s\S]*savePending\.value = false/)
  assert.match(source, /finally \{[\s\S]*phasePending\.value = false/)
  assert.match(source, /finally \{[\s\S]*deletePending\.value = false/)
  assert.match(source, /finally \{[\s\S]*finishing\.value = false/)
  assert.doesNotMatch(source, /tasks\.value\.forEach\(t => \{ if \(t\.phase_id === phase\.id\) t\.phase_id = null \}\)/)
  assert.match(service, /deletePhase\(phaseId, options = \{\}\)/)
  assert.match(service, /params: options/)
})

test('notebook mutations expose independent pending action state and preserve failed forms', async () => {
  const source = await readFile(new URL('./NotebookFileManage.vue', viewsDirectory), 'utf8')

  assert.match(source, /pendingActions/)
  for (const action of ['folder', 'note', 'rename', 'move']) {
    assert.match(source, new RegExp(`pendingActions\\.${action}`))
  }
  assert.match(source, /finally \{[\s\S]*pendingActions\./)
  assert.match(source, /:disabled="[^\"]*pendingActions\.(folder|note|rename|move)/)
  assert.match(source, /dialogError\.value = getErrorMessage\(cause\)/)
  assert.match(source, /closeDialog\(\)[\s\S]*showToast\(/)
})

test('project edit dialog stays open while its save request is pending', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')
  const closeHandler = source.match(/function closeEditProjectDialog\(\{ force = false \} = \{\}\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(closeHandler, 'project edit dialog close handler must remain available')
  assert.match(closeHandler, /if \(!force && savePending\.value\) \{[\s\S]*return false\s*\}/)
  assert.match(source, /function cancelEditProjectDialog\(\) \{[\s\S]*closeEditProjectDialog\(\)/)
  assert.match(source, /<div v-if="showEditProjectDialog"[\s\S]*?@click\.self="cancelEditProjectDialog"[\s\S]*?<div class="dialog"[^>]*@keydown\.esc="cancelEditProjectDialog"/)
})

test('project save failure keeps its dialog context and exposes retry', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')
  const saveHandler = source.match(/async function saveEditProject\(\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(saveHandler, 'saveEditProject handler must remain available')
  assert.match(saveHandler, /catch \(e\) \{[\s\S]*editDialogError\.value = getErrorMessage\(e\)/)
  assert.match(saveHandler, /finally \{[\s\S]*savePending\.value = false/)
  assert.match(source, /editDialogError \? '重试保存项目' : '保存'/)
})

test('project phase creation keeps its dialog context and allows retry after failure', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')
  const saveHandler = source.match(/async function savePhase\(\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(saveHandler, 'savePhase handler must remain available')
  assert.match(saveHandler, /if \(phasePending\.value\)/)
  assert.match(saveHandler, /phaseDialogError\.value = getErrorMessage\(e\)/)
  assert.match(saveHandler, /phasePending\.value = false/)
  assert.match(source, /:disabled="phasePending \|\| phaseDeleteState\.pending \|\| !phaseForm\.name\.trim\(\)"/)
  assert.match(source, /phaseDialogError[\s\S]*重试保存阶段|重试保存阶段[\s\S]*phaseDialogError/)
})

test('phase deletion pending blocks phase editing and save submission with clear feedback', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')
  const saveHandler = source.match(/async function savePhase\(\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(saveHandler, 'savePhase handler must remain available')
  assert.match(saveHandler, /if \(phaseDeleteState\.value\.pending\) \{[\s\S]*return/)
  assert.match(source, /<button class="btn-icon" @click="openPhaseDialog\(phase\)"[^>]*:disabled="phasePending \|\| phaseDeleteState\.pending"[^>]*:aria-disabled="phasePending \|\| phaseDeleteState\.pending"/)
  assert.match(source, /:title="phaseDeleteState\.pending \? '阶段正在删除，请等待完成后再试。' : '编辑阶段'"/)
  assert.match(source, /<button type="submit" class="btn-primary"[^>]*:disabled="phasePending \|\| phaseDeleteState\.pending \|\| !phaseForm\.name\.trim\(\)"[^>]*:aria-disabled="phasePending \|\| phaseDeleteState\.pending \|\| !phaseForm\.name\.trim\(\)"/)
  assert.match(source, /phaseDeleteState\.pending \? '删除中\.\.\.' : phaseDialogError \? '重试保存阶段' : '保存'/)
})

test('project deletion requires confirmation and keeps confirmation context for retry', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')
  const deleteHandler = source.match(/async function confirmDeleteProject\(\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(deleteHandler, 'confirmDeleteProject handler must remain available')
  assert.match(source, /@click="openDeleteDialog"/)
  assert.match(source, /function openDeleteDialog\(\)/)
  assert.match(source, /确定要删除项目「\{\{ project\?\.name \}\}」吗？此操作不可撤销。/)
  assert.match(deleteHandler, /if \(deletePending\.value\)/)
  assert.match(deleteHandler, /deleteDialogError\.value = getErrorMessage\(e\)/)
  assert.doesNotMatch(deleteHandler, /showDeleteDialog\.value = false/)
  assert.match(source, /deleteDialogError[\s\S]*重试删除|重试删除[\s\S]*deleteDialogError/)
})

async function loadPhaseDeleteStateModule() {
  return import('../utils/phaseDeleteState.js').catch(() => ({}))
}

test('phase delete state suppresses duplicate starts and retains retry context after failure', async () => {
  const { createPhaseDeleteState, reducePhaseDeleteState } = await loadPhaseDeleteStateModule()
  assert.equal(typeof createPhaseDeleteState, 'function')
  assert.equal(typeof reducePhaseDeleteState, 'function')
  const phase = { id: 'phase-1', name: 'Race window' }
  let state = reducePhaseDeleteState(createPhaseDeleteState(), { type: 'open', phase })

  state = reducePhaseDeleteState(state, { type: 'start' })
  const duplicateStart = reducePhaseDeleteState(state, { type: 'start' })
  assert.equal(duplicateStart, state)

  state = reducePhaseDeleteState(state, { type: 'fail', error: '阶段仍有任务' })
  assert.equal(state.open, true)
  assert.equal(state.pending, false)
  assert.deepEqual(state.phase, phase)
  assert.equal(state.error, '阶段仍有任务')

  state = reducePhaseDeleteState(state, { type: 'start' })
  assert.equal(state.pending, true)
  assert.deepEqual(state.phase, phase)
})

test('phase delete state only closes after success and blocks close while pending', async () => {
  const { createPhaseDeleteState, reducePhaseDeleteState } = await loadPhaseDeleteStateModule()
  assert.equal(typeof createPhaseDeleteState, 'function')
  assert.equal(typeof reducePhaseDeleteState, 'function')
  const phase = { id: 'phase-2', name: 'Protected' }
  let state = reducePhaseDeleteState(createPhaseDeleteState(), { type: 'open', phase })
  state = reducePhaseDeleteState(state, { type: 'start' })

  assert.deepEqual(reducePhaseDeleteState(state, { type: 'close' }), state)
  assert.deepEqual(reducePhaseDeleteState(state, { type: 'succeed' }), createPhaseDeleteState())
})

test('project phase deletion wires the retryable state into a confirmation dialog', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')

  assert.match(source, /@click="openPhaseDeleteDialog\(phase\)"/)
  assert.match(source, /v-if="phaseDeleteState\.open"[\s\S]*phaseDeleteState\.phase\?\.name/)
  assert.match(source, /phaseDeleteState\.error[\s\S]*重试删除|重试删除[\s\S]*phaseDeleteState\.error/)
  assert.match(source, /function confirmDeletePhase\(\)/)
  assert.match(source, /transitionPhaseDelete\(\{ type: 'fail', error: message \}\)/)
})

test('notebook mutation dialogs stay open while the matching action is pending', async () => {
  const source = await readFile(new URL('./NotebookFileManage.vue', viewsDirectory), 'utf8')
  const pendingGuard = source.match(/function hasPendingDialogAction\(\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(pendingGuard, 'notebook pending dialog guard must remain available')
  assert.match(pendingGuard, /dialogMode\.value && pendingActions\[dialogMode\.value\]/)
  assert.match(source, /function closeDialog\(\) \{[\s\S]*if \(hasPendingDialogAction\(\)\)[\s\S]*return/)
  assert.match(source, /<div v-if="dialogMode"[^>]*@click\.self="closeDialog"[\s\S]*@keydown\.esc="closeDialog"/)
})

test('successful project save force-closes and resets the edit dialog after the request', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')
  const saveHandler = source.match(/async function saveEditProject\(\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(saveHandler, 'project save handler must remain available')
  assert.match(source, /function closeEditProjectDialog\(\{ force = false \} = \{\}\)/)
  assert.match(saveHandler, /project\.value = updated[\s\S]*closeEditProjectDialog\(\{ force: true \}\)/)
  assert.match(source, /editForm\.value = \{ name: '', description: '', color: '', start_date: '', end_date: '' \}/)
})

test('notebook route transitions do not replace a pending mutation dialog', async () => {
  const source = await readFile(new URL('./NotebookFileManage.vue', viewsDirectory), 'utf8')
  const routeWatcher = source.match(/watch\(isNewNoteRoute, \(isNew\) => \{([\s\S]*?)\n\}\)/)?.[1]

  assert.ok(routeWatcher, 'new-note route watcher must remain available')
  assert.match(routeWatcher, /if \(dialogMode\.value && pendingActions\[dialogMode\.value\]\) \{[\s\S]*return\s*\}/)
  assert.match(source, /function openCreateNote\([\s\S]*if \(dialogMode\.value && pendingActions\[dialogMode\.value\]\)/)
})

test('header profile and logout actions stop propagation before closing the menu', async () => {
  const source = await readFile(new URL('../components/layout/Header.vue', import.meta.url), 'utf8')

  assert.match(source, /@click\.stop="dropdownOpen = false"/)
  assert.match(source, /@click\.stop="handleLogout"/)
  assert.match(source, /function handleLogout\(event\)[\s\S]*event\.stopPropagation\(\)/)

  const menuOpeningTag = source.match(/<div v-if="dropdownOpen" class="dropdown-menu"[^>]*>/)?.[0]
  assert.ok(menuOpeningTag, 'dropdown menu must remain available for the propagation contract')
  assert.match(menuOpeningTag, /@click\.stop="dropdownOpen = false"/)
})
