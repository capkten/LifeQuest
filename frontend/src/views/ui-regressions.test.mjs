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

test('sidebar displays the application version beside the LifeQuest brand', async () => {
  const [sidebar, viteConfig] = await Promise.all([
    readFile(new URL('../components/layout/Sidebar.vue', import.meta.url), 'utf8'),
    readFile(new URL('../../vite.config.js', import.meta.url), 'utf8'),
  ])

  assert.match(sidebar, /appVersion/)
  assert.match(sidebar, /v\{\{ appVersion \}\}/)
  assert.match(viteConfig, /readFileSync/)
  assert.match(viteConfig, /VERSION/)
})

test('all application runtimes consume the root VERSION source', async () => {
  const [backend, gradle, workflow] = await Promise.all([
    readFile(new URL('../../../backend/app/main.py', import.meta.url), 'utf8'),
    readFile(new URL('../../android/app/build.gradle', import.meta.url), 'utf8'),
    readFile(new URL('../../../.github/workflows/android-release.yml', import.meta.url), 'utf8'),
  ])

  assert.match(backend, /readFileSync[\s\S]*VERSION|read_text\([\s\S]*VERSION/)
  assert.match(gradle, /VERSION[\s\S]*versionName|versionName[\s\S]*VERSION/)
  assert.match(workflow, /diff --quiet HEAD\^ HEAD -- VERSION/)
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
  assert.match(workflow, /node-version: 22/)
  assert.match(workflow, /npx cap sync android/)
  assert.match(app, /VITE_ANDROID_UPDATE_MANIFEST_URL|UpdatePrompt/)
})

test('android production builds use the canonical API domain without a secret override', async () => {
  const [envAndroid, envExample, workflow] = await Promise.all([
    readFile(new URL('../../.env.android', import.meta.url), 'utf8'),
    readFile(new URL('../../.env.android.example', import.meta.url), 'utf8'),
    readFile(new URL('../../../.github/workflows/android-release.yml', import.meta.url), 'utf8'),
  ])

  for (const source of [envAndroid, envExample, workflow]) {
    assert.match(source, /VITE_API_BASE_URL=https:\/\/life\.capkin\.cn\/api/)
  }
  assert.doesNotMatch(workflow, /ANDROID_API_BASE_URL/)
  assert.doesNotMatch(workflow, /secrets\.ANDROID_API_BASE_URL/)
})

test('android update prompt downloads and launches APK installation natively', async () => {
  const [prompt, updater, activity, manifest, filePaths, updaterComposable, workflow] = await Promise.all([
    readFile(new URL('../components/layout/UpdatePrompt.vue', import.meta.url), 'utf8'),
    readFile(new URL('../../android/app/src/main/java/com/lifequest/app/AppUpdaterPlugin.java', import.meta.url), 'utf8'),
    readFile(new URL('../../android/app/src/main/java/com/lifequest/app/MainActivity.java', import.meta.url), 'utf8'),
    readFile(new URL('../../android/app/src/main/AndroidManifest.xml', import.meta.url), 'utf8'),
    readFile(new URL('../../android/app/src/main/res/xml/file_paths.xml', import.meta.url), 'utf8'),
    readFile(new URL('../composables/useAppUpdate.js', import.meta.url), 'utf8'),
    readFile(new URL('../../../.github/workflows/android-release.yml', import.meta.url), 'utf8'),
  ])

  assert.match(prompt, /AppUpdater|startDownload/)
  assert.doesNotMatch(prompt, /Browser\.open/)
  assert.match(updater, /DownloadManager/)
  assert.match(updater, /Context\.RECEIVER_EXPORTED/)
  assert.doesNotMatch(updater, /Context\.RECEIVER_NOT_EXPORTED/)
  assert.match(updater, /ACTION_VIEW/)
  assert.match(updater, /resumePendingInstall/)
  assert.match(activity, /registerPlugin\(AppUpdaterPlugin\.class\)/)
  assert.match(activity, /resumePendingInstall\(\)/)
  assert.match(manifest, /REQUEST_INSTALL_PACKAGES/)
  assert.match(filePaths, /external-files-path/)
  assert.match(updaterComposable, /addListener\(['"]downloadProgress['"],/)
  assert.match(updaterComposable, /openGithubDownload/)
  assert.match(prompt, /role="progressbar"/)
  assert.match(prompt, /下载进度|正在连接下载服务/)
  assert.match(prompt, /打开 GitHub 下载/)
  assert.match(updater, /notifyListeners\(['"]downloadProgress['"]/)
  assert.match(updater, /COLUMN_BYTES_DOWNLOADED_SO_FAR/)
  assert.match(updater, /STATUS_FAILED/)
  assert.match(workflow, /releaseUrl/)
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

test('shop search remains usable on mobile', async () => {
  const source = await readFile(new URL('./Shop.vue', viewsDirectory), 'utf8')

  assert.match(source, /@media \(max-width: 767px\) \{[\s\S]*?\.shop-search \{[\s\S]*?flex: 1 1 auto[\s\S]*?width: 100%[\s\S]*?height: 44px/)
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
  assert.match(source, /:disabled="completingId === habit\.id"/)
  assert.match(source, /:aria-disabled="Boolean\(habitBlockReason\(habit\)\)"/)
  assert.match(source, /function habitBlockReason\(habit\)/)
  assert.match(source, /if \(habit\.completed_today\)/)
  assert.match(source, /v-model="form\.weekdays" type="checkbox"/)
  assert.match(source, /v-model\.number="form\.weekly_target"/)
  assert.match(source, /habit\.weekly_completed.*habit\.weekly_target/)
})

test('daily habit consumers compare optional server state fields explicitly', async () => {
  const [service, home, todos] = await Promise.all([
    readFile(new URL('../services/todo.js', viewsDirectory), 'utf8'),
    readFile(new URL('./Home.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./Todos.vue', viewsDirectory), 'utf8'),
  ])

  for (const [file, source] of [['Home.vue', home], ['Todos.vue', todos]]) {
    assert.match(source, /habit\.paused_today === true/, `${file} must check paused_today explicitly`)
    assert.match(source, /habit\.is_active === false/, `${file} must check is_active explicitly`)
    assert.match(source, /habit\.excused_today === true/, `${file} must check excused_today explicitly`)
    assert.match(source, /habit\.scheduled_today === false/, `${file} must check scheduled_today explicitly`)
  }

  const dailyMethod = service.match(/async getDailySummary\(\) \{[\s\S]*?\n  \},/)?.[0]
  assert.ok(dailyMethod, 'daily summary service method must remain available')
  assert.doesNotMatch(dailyMethod, /result\.data/)
})

test('todo task filters use project buttons and show unfinished tasks first', async () => {
  const source = await readFile(new URL('./Todos.vue', viewsDirectory), 'utf8')

  assert.doesNotMatch(source, /id="project-filter-select"/)
  assert.match(source, /project-filter-btn/)
  assert.match(source, /id:\s*'unassigned'/)
  assert.match(source, /projectFilters/)
  assert.match(source, /openTaskCount/)
  assert.match(source, /visibleTasks/)
  assert.match(source, /task in visibleTasks/)
  assert.match(source, /status === 'completed'/)
})

test('todo subtasks use a compact right-side arrow toggle', async () => {
  const source = await readFile(new URL('./Todos.vue', viewsDirectory), 'utf8')

  assert.doesNotMatch(source, /class="subtask-toggle-btn"/)
  assert.match(source, /class="subtask-toggle"/)
  assert.match(source, /aria-label="expandedTaskId === task\.id \? '收起子任务' : '展开子任务'"/)
  assert.match(source, /class="subtask-divider"/)
  assert.match(source, /subtask-toggle-icon--expanded/)
})

test('finance account editor applies type-aware balance rules and credit guidance', async () => {
  const source = await readFile(new URL('./FinanceAccounts.vue', viewsDirectory), 'utf8')

  assert.doesNotMatch(source, /:min="form\.type === 'credit'/)
  assert.match(source, /信用额度至少需要/)
  assert.match(source, /creditLimit < Math\.abs\(balance\)/)
  assert.match(source, /信用卡可为负|当前欠款/)
  assert.match(source, /已用额度/)
  assert.match(source, /可用额度/)
  assert.match(source, /净资产/)
})

test('finance accounts expose inactive accounts and a reactivation flow', async () => {
  const source = await readFile(new URL('./FinanceAccounts.vue', viewsDirectory), 'utf8')

  assert.match(source, /getAccounts\(\{ include_inactive: true \}\)/)
  assert.match(source, /activeAccounts/)
  assert.match(source, /!acct\.is_active/)
  assert.match(source, /reactivateAccount\(acct\)/)
  assert.match(source, /updateAccount\(.*is_active: true/s)
})

test('todo task creation supports optional project and milestone context', async () => {
  const source = await readFile(new URL('./Todos.vue', viewsDirectory), 'utf8')
  const projectDetail = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')

  assert.match(source, /id="item-project"/)
  assert.match(source, /id="item-milestone"/)
  assert.match(source, /project_id: contextProjectId\.value/)
  assert.match(source, /base\.project_id = form\.value\.project_id/)
  assert.match(source, /base\.milestone_id = form\.value\.milestone_id/)
  assert.match(source, /route\.query\.project_id/)
  assert.match(source, /projectService\.getProject\(projectId\)/)
  assert.match(projectDetail, /path: '\/todos'/)
  assert.match(projectDetail, /query: \{ project_id: project\.id \}/)
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

test('habit entry points respect all server lock fields and non-retryable refresh failures', async () => {
  const [todos, home, history] = await Promise.all([
    readFile(new URL('./Todos.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./Home.vue', viewsDirectory), 'utf8'),
    readFile(new URL('../components/HabitHistoryDialog.vue', import.meta.url), 'utf8'),
  ])

  for (const source of [todos, home]) {
    assert.match(source, /completed_today/)
    assert.match(source, /paused_today/)
    assert.match(source, /excused_today/)
    assert.match(source, /scheduled_today/)
    assert.match(source, /weekly_remaining/)
  }
  assert.match(history, /shiftDateKey/)
  assert.doesNotMatch(history, /function shiftDate\(/)
  assert.match(todos, /Promise\.allSettled\(/)
  assert.match(todos, /无需再次提交/)
})

test('habit history initializes date forms when mounted already visible', async () => {
  const source = await readFile(new URL('../components/HabitHistoryDialog.vue', import.meta.url), 'utf8')
  const mounted = source.match(/onMounted\(\(\) => \{([\s\S]*?)\n\}\)/)?.[1]

  assert.ok(mounted, 'habit history needs a mounted lifecycle handler')
  assert.match(mounted, /if \(props\.visible\) \{[\s\S]*resetForms\(\)[\s\S]*loadHistory\(\)/)
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
  const [finance, stats] = await Promise.all([
    readFile(new URL('./FinanceTransactions.vue', viewsDirectory), 'utf8'),
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
  assert.match(finance, /hasMore\.value = false/)
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

test('project lifecycle exposes start, milestone reach, and centralized phase labels', async () => {
  const [projects, detail, service, labels] = await Promise.all([
    readFile(new URL('./Projects.vue', viewsDirectory), 'utf8'),
    readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8'),
    readFile(new URL('../services/project.js', import.meta.url), 'utf8'),
    readFile(new URL('../utils/displayLabels.js', import.meta.url), 'utf8'),
  ])

  assert.match(service, /startProject\(id\)/)
  assert.match(service, /\/projects\/\$\{id\}\/start/)
  assert.match(service, /reachMilestone\(msId\)/)
  assert.match(projects, /projectService\.startProject\(/)
  assert.match(projects, /startPending/)
  assert.match(detail, /projectService\.reachMilestone\(/)
  assert.match(detail, /milestoneReachPending/)
  assert.match(detail, /里程碑已达成/)
  assert.match(labels, /PHASE_STATUS_LABELS/)
  assert.match(labels, /labelPhaseStatus\(/)
  assert.match(detail, /labelPhaseStatus\(/)
  assert.doesNotMatch(detail, /const map = \{ planning: '规划中'/)
})

test('ProjectDetail inline task creation locks duplicate submissions and keeps failed input retryable', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')
  const phaseHandler = source.match(/function addTaskToPhase\(phaseId, event\) \{([\s\S]*?)\n\}/)?.[1]
  const kanbanHandler = source.match(/function addKanbanTask\(event\) \{([\s\S]*?)\n\}/)?.[1]
  const creationHandler = source.match(/async function createTaskFromInlineForm\(event, payload\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(phaseHandler, 'phase task creation handler must remain available')
  assert.ok(kanbanHandler, 'kanban task creation handler must remain available')
  assert.ok(creationHandler, 'shared task creation handler must remain available')
  assert.match(source, /const taskCreationPending = ref\(false\)/)
  assert.match(source, /let taskCreationRequestId = 0/)
  assert.match(source, /:disabled="taskCreationPending"/)
  assert.match(phaseHandler, /return createTaskFromInlineForm\(event, \{ phase_id: phaseId \}\)/)
  assert.match(kanbanHandler, /return createTaskFromInlineForm\(event, \{ status: 'pending' \}\)/)
  assert.match(creationHandler, /if \(taskCreationPending\.value\)/)
  assert.match(creationHandler, /const token = createProjectRequestToken\(\+\+taskCreationRequestId/)
  assert.match(creationHandler, /isCurrentProjectRequest\(token, taskCreationRequestId\)/)
  assert.match(creationHandler, /finally \{[\s\S]*taskCreationPending\.value = false/)
})

test('ProjectDetail project mutations ignore stale route responses and reset every dialog state', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')
  const handlers = ['savePhase', 'confirmDeletePhase', 'saveEditProject', 'completeProject', 'confirmDeleteProject']

  for (const name of handlers) {
    const handler = source.match(new RegExp(`async function ${name}\\([^)]*\\) \\{([\\s\\S]*?)\\n\\}`))?.[1]
    assert.ok(handler, `${name} handler must remain available`)
    assert.match(handler, /createProjectRequestToken\(\+\+/)
    assert.match(handler, /isCurrentProjectRequest\(/)
  }

  assert.match(source, /let routeRevision = 0/)
  assert.match(source, /function createProjectRequestToken\(/)
  assert.match(source, /function isCurrentProjectRequest\(/)
  assert.match(source, /fetchData\([\s\S]*revision !== dataRevision/)
  assert.match(source, /finally \{[\s\S]*if \(isCurrentFetch\(requestId, normalizedId\)\) loading\.value = false/)

  const routeWatcher = source.match(/watch\(\(\) => route\.params\.id, \(nextId, previousId\) => \{([\s\S]*?)\n\}\)/)?.[1]
  const invalidationHandler = source.match(/function invalidateRequests\(\) \{([\s\S]*?)\n\}/)?.[1]
  assert.ok(routeWatcher, 'project route watcher must remain available')
  assert.ok(invalidationHandler, 'project request invalidation handler must remain available')
  assert.match(routeWatcher, /invalidateRequests\(\)/)
  assert.match(invalidationHandler, /cancelPhaseDialog\(\{ force: true \}\)/)
  assert.match(invalidationHandler, /closeEditProjectDialog\(\{ force: true \}\)/)
  assert.match(invalidationHandler, /closeDeleteDialog\(\{ force: true \}\)/)
  assert.match(invalidationHandler, /phaseDeleteState\.value = createPhaseDeleteState\(\)/)
})

test('ProjectDetail suppresses stale settlement feedback after a route change', async () => {
  const source = await readFile(new URL('./ProjectDetail.vue', viewsDirectory), 'utf8')
  const rewardHandler = source.match(/async function refreshTaskReward\(updated, taskId, taskToken\) \{([\s\S]*?)\n\}/)?.[1]

  assert.ok(rewardHandler, 'task reward refresh handler must remain available')
  assert.match(source, /let rewardRequestId = 0/)
  assert.match(source, /refreshTaskReward\(updated, task\.id, token\)/)
  assert.match(rewardHandler, /const rewardToken = createProjectRequestToken\(\+\+rewardRequestId\)/)
  assert.match(rewardHandler, /isCurrentProjectRequest\(rewardToken, rewardRequestId\)/)
  assert.match(rewardHandler, /isCurrentTaskMutation\(taskId, taskToken\)/)
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

test('profile exposes one-time MCP token management', async () => {
  const [profile, service] = await Promise.all([
    readFile(new URL('./Profile.vue', viewsDirectory), 'utf8'),
    readFile(new URL('../services/mcpToken.js', import.meta.url), 'utf8'),
  ])
  assert.match(service, /get.*auth\/mcp-tokens/)
  assert.match(service, /post.*auth\/mcp-tokens/)
  assert.match(service, /import\s+api\s+from\s+['"]\.\/api['"]/, 'MCP token service must use the JWT-aware api client')
  assert.match(service, /api\.get\(\s*['"]\/auth\/mcp-tokens['"]\s*,/, 'list must use api.get')
  assert.match(service, /api\.post\(\s*['"]\/auth\/mcp-tokens['"]\s*,/, 'create must use api.post')
  assert.match(service, /api\.delete\(\s*`\/auth\/mcp-tokens\/\$\{tokenId\}`\s*\)/, 'revoke must interpolate tokenId into api.delete')
  assert.match(profile, /mcpTokenService/)
  assert.match(profile, /newMcpToken/)
  assert.match(profile, /navigator\.clipboard\.writeText/)
  assert.match(profile, /LIFEQUEST_MCP_TOKEN/)
  assert.match(profile, /revokeTarget/)
  assert.match(profile, /:disabled="mcpTokensLoading \|\| mcpTokenCreating"/)
  assert.match(profile, /:disabled="mcpTokenCopying \|\| mcpTokenRevoking"/)
  assert.match(profile, /if \(mcpTokensLoading\.value\) \{[\s\S]*!waitForActive/)
  assert.match(profile, /if \(mcpTokenCreating\.value && !waitForActive\) return/)
  assert.match(profile, /async function createMcpToken\(\) \{\s*if \(mcpTokenCreating\.value\) return/)
  assert.match(profile, /<form class="mcp-token-form"[^>]*@submit\.prevent="createMcpToken">/)
  assert.match(profile, /<button type="button" class="[^\"]*mcp-copy-btn[^\"]*"[^>]*@click="copyMcpToken">[\s\S]*复制凭证[\s\S]*<\/button>/)
  const revokeButtonOpeningTag = profile.match(/<button\b[^>]*v-if="isMcpTokenRevocable\(token\)"[^>]*>/)?.[0]
  assert.ok(revokeButtonOpeningTag, 'MCP revoke control must remain a button opening tag')
  assert.match(revokeButtonOpeningTag, /v-if="isMcpTokenRevocable\(token\)"/)
  assert.match(revokeButtonOpeningTag, /class="[^"]*\bmcp-token-revoke\b[^"]*"/)
  assert.match(revokeButtonOpeningTag, /@click="openRevokeDialog\(token\)"/)
  assert.match(profile, /<button type="button" class="primary-btn" :disabled="mcpTokenRevoking \|\| mcpTokenCopying" @click="revokeMcpToken">/)
  assert.match(profile, /function openRevokeDialog\(token\) \{\s*if \(mcpTokenRevoking\.value\) return\s*applyMcpTokenAction/)
  assert.match(profile, /:disabled="mcpTokenRevoking \|\| mcpTokenCopying"/)
  assert.match(profile, /if \(!tokenId \|\| mcpTokenRevoking\.value \|\| mcpTokenCopying\.value\) return/)
  assert.match(profile, /fetchMcpTokens\(\{ waitForActive: true \}\)/)
  assert.doesNotMatch(profile, /localStorage\.(getItem|setItem).*mcp/i)
})

test('MCP credential panel presents modern duration and action controls', async () => {
  const source = await readFile(new URL('./Profile.vue', viewsDirectory), 'utf8')

  assert.match(source, /class="mcp-token-card__heading"/)
  assert.match(source, /class="mcp-token-card__icon"/)
  assert.match(source, /mcpActiveTokenCount/)
  assert.match(source, /role="group" aria-label="快速选择有效期"/)
  assert.match(source, /v-for="duration in mcpTokenDurationOptions"/)
  assert.match(source, /class="mcp-duration-option"/)
  assert.match(source, /@click="setMcpTokenDuration\(duration\)"/)
  assert.match(source, /id="mcp-token-expires"[\s\S]*class="mcp-token-duration-input"/)
  assert.match(source, /id="mcp-token-name"[\s\S]*class="mcp-token-name-input"/)
  assert.doesNotMatch(source, /id="mcp-token-name"[\s\S]*class="form-input"/)
  assert.match(source, /<Plus\b[^>]*\/>/)
  assert.match(source, /<CopyDocument\b[^>]*\/>/)
  assert.match(source, /<Delete\b[^>]*\/>/)
  assert.match(source, /\.mcp-token-name-input\s*\{[\s\S]*min-height: 44px;[\s\S]*border-radius: 10px;[\s\S]*background: var\(--color-card\)/)
  assert.match(source, /\.mcp-token-name-input:focus\s*\{[\s\S]*box-shadow: 0 0 0 3px/)
  assert.match(source, /@media \(max-width: 767px\) \{[\s\S]*?\.mcp-token-card__heading[\s\S]*?grid-template-columns: 1fr/)
})

async function loadMcpTokenStateModule() {
  return import('../services/mcpTokenState.js').catch(() => ({}))
}

test('MCP token list failures preserve prior metadata and block overlapping loads', async () => {
  const { createMcpTokenState, reduceMcpTokenState } = await loadMcpTokenStateModule()
  assert.equal(typeof createMcpTokenState, 'function')
  assert.equal(typeof reduceMcpTokenState, 'function')

  const prior = { id: 'token-1', name: 'Desktop', status: 'active' }
  let state = reduceMcpTokenState(createMcpTokenState(), { type: 'list-success', tokens: [prior] })
  state = reduceMcpTokenState(state, { type: 'list-start' })
  assert.strictEqual(reduceMcpTokenState(state, { type: 'list-start' }), state)

  state = reduceMcpTokenState(state, { type: 'list-failure', error: '加载失败' })
  assert.deepEqual(state.mcpTokens, [prior])
  assert.equal(state.mcpTokensLoading, false)
  assert.equal(state.mcpTokensError, '加载失败')
})

test('MCP one-time result state clears the complete result on close', async () => {
  const { createMcpTokenState, reduceMcpTokenState } = await loadMcpTokenStateModule()
  assert.equal(typeof createMcpTokenState, 'function')
  assert.equal(typeof reduceMcpTokenState, 'function')

  const created = { token: 'secret-value', expires_at: '2030-01-01T00:00:00Z' }
  let state = reduceMcpTokenState(createMcpTokenState(), { type: 'new-token', token: created })
  assert.deepEqual(state.newMcpToken, created)

  state = reduceMcpTokenState(state, { type: 'clear-new-token' })
  assert.equal(state.newMcpToken, null)
})

test('MCP token copy state blocks duplicates and preserves the result through success or failure', async () => {
  const { createMcpTokenState, reduceMcpTokenState } = await loadMcpTokenStateModule()
  assert.equal(typeof createMcpTokenState, 'function')
  assert.equal(typeof reduceMcpTokenState, 'function')

  const created = { token: 'secret-value' }
  let state = reduceMcpTokenState(createMcpTokenState(), { type: 'new-token', token: created })
  state = reduceMcpTokenState(state, { type: 'copy-start' })
  assert.equal(state.mcpTokenCopying, true)
  assert.strictEqual(reduceMcpTokenState(state, { type: 'copy-start' }), state)
  state = reduceMcpTokenState(state, { type: 'copy-success' })
  assert.equal(state.mcpTokenCopyStatus, 'success')
  state = reduceMcpTokenState(state, { type: 'copy-finish' })
  assert.equal(state.mcpTokenCopying, false)
  assert.deepEqual(state.newMcpToken, created)

  state = reduceMcpTokenState(state, { type: 'copy-start' })
  state = reduceMcpTokenState(state, { type: 'copy-failure' })
  assert.equal(state.mcpTokenCopyStatus, 'failure')
  state = reduceMcpTokenState(state, { type: 'copy-finish' })
  assert.equal(state.mcpTokenCopying, false)
  assert.deepEqual(state.newMcpToken, created)
})

test('MCP revoke state confirms, disables duplicate actions while pending, and closes after success', async () => {
  const { createMcpTokenState, reduceMcpTokenState } = await loadMcpTokenStateModule()
  assert.equal(typeof createMcpTokenState, 'function')
  assert.equal(typeof reduceMcpTokenState, 'function')

  const target = { id: 'token-2', name: 'CLI', status: 'active' }
  let state = reduceMcpTokenState(createMcpTokenState(), { type: 'open-revoke', token: target })
  assert.deepEqual(state.revokeTarget, target)
  state = reduceMcpTokenState(state, { type: 'revoke-start' })
  assert.equal(state.mcpTokenRevoking, true)
  assert.strictEqual(reduceMcpTokenState(state, { type: 'revoke-start' }), state)
  assert.strictEqual(
    reduceMcpTokenState(state, { type: 'open-revoke', token: { id: 'token-3', status: 'active' } }),
    state
  )

  state = reduceMcpTokenState(state, { type: 'revoke-success' })
  assert.equal(state.revokeTarget, null)
  state = reduceMcpTokenState(state, { type: 'revoke-finish' })
  assert.equal(state.mcpTokenRevoking, false)
})

test('MCP create failure preserves the one-time result and duplicate starts are ignored', async () => {
  const { createMcpTokenState, reduceMcpTokenState } = await loadMcpTokenStateModule()
  assert.equal(typeof createMcpTokenState, 'function')
  assert.equal(typeof reduceMcpTokenState, 'function')

  const created = { id: 'token-3', token: 'secret-value' }
  let state = reduceMcpTokenState(createMcpTokenState(), { type: 'new-token', token: created })
  state = reduceMcpTokenState(state, { type: 'create-start' })
  assert.strictEqual(reduceMcpTokenState(state, { type: 'create-start' }), state)
  state = reduceMcpTokenState(state, { type: 'create-failure' })

  assert.equal(state.mcpTokenCreating, false)
  assert.deepEqual(state.newMcpToken, created)
})

test('MCP revoke failure preserves confirmation and one-time result, while only matching success clears it', async () => {
  const { createMcpTokenState, reduceMcpTokenState } = await loadMcpTokenStateModule()
  assert.equal(typeof createMcpTokenState, 'function')
  assert.equal(typeof reduceMcpTokenState, 'function')

  const target = { id: 'token-4', name: 'CLI', status: 'active' }
  const created = { id: target.id, token: 'secret-value' }
  let state = reduceMcpTokenState(createMcpTokenState(), { type: 'new-token', token: created })
  state = reduceMcpTokenState(state, { type: 'open-revoke', token: target })
  state = reduceMcpTokenState(state, { type: 'revoke-start' })
  state = reduceMcpTokenState(state, { type: 'revoke-failure' })
  state = reduceMcpTokenState(state, { type: 'revoke-finish' })
  assert.deepEqual(state.revokeTarget, target)
  assert.deepEqual(state.newMcpToken, created)

  state = reduceMcpTokenState(state, { type: 'revoke-start' })
  state = reduceMcpTokenState(state, { type: 'revoke-success', tokenId: 'other-token' })
  assert.deepEqual(state.newMcpToken, created)

  state = reduceMcpTokenState(state, { type: 'new-token', token: created })
  state = reduceMcpTokenState(state, { type: 'open-revoke', token: target })
  state = reduceMcpTokenState(state, { type: 'revoke-start' })
  state = reduceMcpTokenState(state, { type: 'revoke-success', tokenId: target.id })
  assert.equal(state.newMcpToken, null)
})

test('MCP copy and revoke actions cannot start while the other action is pending', async () => {
  const { createMcpTokenState, reduceMcpTokenState } = await loadMcpTokenStateModule()
  assert.equal(typeof createMcpTokenState, 'function')
  assert.equal(typeof reduceMcpTokenState, 'function')

  const target = { id: 'token-5', name: 'Editor', status: 'active' }
  let state = reduceMcpTokenState(createMcpTokenState(), { type: 'new-token', token: { id: target.id, token: 'secret-value' } })
  state = reduceMcpTokenState(state, { type: 'copy-start' })
  assert.strictEqual(reduceMcpTokenState(state, { type: 'open-revoke', token: target }), state)

  state = reduceMcpTokenState(createMcpTokenState(), { type: 'open-revoke', token: target })
  state = reduceMcpTokenState(state, { type: 'revoke-start' })
  assert.strictEqual(reduceMcpTokenState(state, { type: 'copy-start' }), state)
  assert.strictEqual(reduceMcpTokenState(state, { type: 'revoke-start' }), state)
})
