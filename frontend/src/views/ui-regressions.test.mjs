import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const viewsDirectory = new URL('./', import.meta.url)

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

test('note editor leaves loading state when opening a new note route', async () => {
  const source = await readFile(new URL('./NoteEditor.vue', viewsDirectory), 'utf8')

  assert.match(source, /if \(!noteId\.value\) \{[\s\S]*loading\.value = false[\s\S]*hydrated\.value = true/)
})
