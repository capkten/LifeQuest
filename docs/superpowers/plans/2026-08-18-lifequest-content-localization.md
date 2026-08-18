# LifeQuest Content Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 LifeQuest 的系统生成内容、数据库世界观数据、API 展示字段、错误提示和前端界面统一为中文，并在文案替换后完成四种屏幕尺寸的 UI 回归检查。

**Architecture:** 后端使用一个稳定的中文内容目录作为种子和回填迁移的唯一来源；数据库保留内部 key 与历史关联，系统展示文本改为中文。API 同时返回内部 key 和展示 label，前端通过共享展示字典与错误转换器消费中文内容，最后用静态测试、构建和浏览器检查验证文案没有破坏布局。

**Tech Stack:** FastAPI、SQLAlchemy、pytest、Vue 3、Pinia、Element Plus、Vite、Node test runner、Codex in-app browser。

## Global Constraints

- 保留 API 路径、数据库字段、内部 key、稳定事件码、主键、外键和历史关联。
- 不翻译或覆盖用户自行创建的任务、笔记、项目、商品、NPC 和描述。
- 系统生成的区域、宗门、功法、NPC、事件、奖励和流水描述必须使用中文。
- 种子和回填迁移必须幂等，重复启动不能重复创建或破坏数据。
- API 兼容现有 key 字段，并增加中文 `*_label` 字段；前端不得直接展示内部 key。
- 不引入新的国际化依赖；使用项目现有 Vue、Pinia 和 Element Plus 结构。
- 所有用户可感知的静态文本、错误、占位符、`aria-label` 和 `title` 都纳入中文检查。
- 文案替换后必须检查 375px、768px、1024px、1440px，不得以静态测试代替视觉检查。
- 若委托子代理，必须显式指定 `gpt-5.6-luna`。

---

### Task 1: 建立中文内容目录和展示契约

**Files:**
- Create: `backend/app/services/content_catalog.py`
- Create: `frontend/src/locales/zh-CN.js`
- Create: `frontend/src/utils/displayLabels.js`
- Create: `frontend/src/utils/errorMessage.js`
- Create: `backend/tests/test_content_catalog.py`
- Create: `frontend/src/views/localization-regressions.test.mjs`

**Interfaces:**
- `content_catalog.py` exports `WORLD_NODE_CATALOG`, `SECT_CATALOG`, `TECHNIQUE_CATALOG`, `REALM_LABELS`, `NPC_ROLE_LABELS`, and `EVENT_SUMMARY_LABELS`.
- `displayLabels.js` exports `labelRealm(value)`, `labelSectKind(value)`, `labelTechniqueType(value)`, `labelTaskPreference(value)`, `labelStatus(value)`, and `labelResource(value)`.
- `errorMessage.js` exports `getErrorMessage(error, fallback = '操作失败，请重试。')`.

- [ ] **Step 1: Write failing catalog tests**

```python
def test_system_catalog_has_chinese_world_and_technique_content():
    from app.services.content_catalog import TECHNIQUE_CATALOG, WORLD_NODE_CATALOG

    assert WORLD_NODE_CATALOG["mortal-domain-1"]["name"] == "青云凡域"
    assert TECHNIQUE_CATALOG["steady-breath"]["name"] == "凝息诀"
    assert TECHNIQUE_CATALOG["steady-breath"]["description"]
```

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { labelRealm, labelResource } from '../utils/displayLabels.js'

test('display labels translate stable server keys', () => {
  assert.equal(labelRealm('foundation'), '筑基期')
  assert.equal(labelResource('spirit_stones'), '灵石')
})
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_catalog.py -q

cd ../frontend
node --test src/views/localization-regressions.test.mjs
```

Expected: imports or catalog keys are missing.

- [ ] **Step 3: Add the canonical dictionaries**

Use stable keys as dictionary keys and Chinese values as user-facing content. Include all nine world-node entries, every generated sect key, all three initial techniques, every realm label, slot type, sect kind, task preference, NPC role and system event summary.

- [ ] **Step 4: Add frontend display and error contracts**

Implement the exact fallback order:

```js
export function labelRealm(value) {
  return REALM_LABELS[value] || value || '未知境界'
}

export function getErrorMessage(error, fallback = '操作失败，请重试。') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'object' && detail?.message) return detail.message
  if (typeof detail === 'string') {
    if (ERROR_MESSAGES[detail]) return ERROR_MESSAGES[detail]
    if (/[\u3400-\u9fff]/.test(detail)) return detail
  }
  return fallback
}
```

- [ ] **Step 5: Run focused tests and commit**

Run the two focused commands from Step 2. Expected: all catalog and label tests pass.

```powershell
git add backend/app/services/content_catalog.py backend/tests/test_content_catalog.py frontend/src/locales/zh-CN.js frontend/src/utils/displayLabels.js frontend/src/utils/errorMessage.js frontend/src/views/localization-regressions.test.mjs
git commit -m "feat(localization): add chinese content dictionaries"
```

### Task 2: 中文种子数据和数据库幂等回填

**Files:**
- Create: `backend/app/services/content_localization.py`
- Modify: `backend/app/services/cultivation.py:165-220`
- Modify: `backend/app/main.py` startup seed section around `738-757`
- Test: `backend/tests/test_content_localization.py`

**Interfaces:**
- `ContentLocalizationService.backfill_system_content(db: Session) -> ContentBackfillSummary`.
- `ContentBackfillSummary` exposes integer counts for `world_nodes`, `sects`, `techniques`, `npcs`, and `events`.
- `CultivationService._seed_world_once(db)` creates new records from `content_catalog.py` and never reconstructs English names with string templates.

- [ ] **Step 1: Write failing migration tests**

Create an isolated SQLite database with legacy rows such as `Mortal Domain 1`, `1-Star Normal Sect 1`, `Steady Breath`, `A disciple of ...`, and `Met ordinary disciple`. Also insert one user-created NPC and assert that it stays unchanged.

```python
def test_backfill_updates_known_system_rows_without_overwriting_user_content(db_session):
    summary = ContentLocalizationService.backfill_system_content(db_session)

    node = db_session.query(WorldNode).filter_by(node_key="mortal-domain-1").one()
    technique = db_session.query(Technique).filter_by(technique_key="steady-breath").one()
    assert node.name == "青云凡域"
    assert technique.name == "凝息诀"
    assert summary.world_nodes >= 1
```

- [ ] **Step 2: Run the migration test and verify it fails**

Run:

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_localization.py::test_backfill_updates_known_system_rows_without_overwriting_user_content -q
```

Expected: the backfill service or Chinese values are missing.

- [ ] **Step 3: Implement the backfill service**

Update only records addressable by stable system keys. For generated NPCs use `is_generated=True`; for fixed core NPCs use the known role and sect relation; for events update only known system event keys or exact legacy templates. Do not update arbitrary user descriptions.

- [ ] **Step 4: Switch seeding to the catalog and call backfill after seeding**

The startup sequence must be:

```python
CultivationService.seed_world(db)
ContentLocalizationService.backfill_system_content(db)
```

The API-time `seed_world()` path must also create Chinese records for a fresh database. The startup migration remains inside the existing transaction/error logging boundary.

- [ ] **Step 5: Verify idempotency and migration safety**

Add tests that call backfill twice, verify stable row counts and names, preserve foreign keys, preserve user-created content, and work with an empty database. Run:

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_localization.py tests/test_cultivation.py -q
```

- [ ] **Step 6: Commit the data layer**

```powershell
git add backend/app/services/content_localization.py backend/app/services/content_catalog.py backend/app/services/cultivation.py backend/app/main.py backend/tests/test_content_localization.py
git commit -m "fix(localization): backfill chinese system content"
```

### Task 3: API 中文展示字段和动态系统文本

**Files:**
- Modify: `backend/app/schemas/cultivation.py`
- Modify: `backend/app/services/cultivation.py`
- Modify: `backend/app/api/cultivation.py`
- Modify: `backend/app/services/checkin.py`
- Modify: `backend/app/services/coin.py`
- Modify: `backend/app/services/achievement.py`
- Inspect: `backend/app/services/title.py`
- Inspect: `backend/app/services/finance.py`
- Modify: `backend/tests/test_cultivation.py`
- Test: `backend/tests/test_content_localization.py`

**Interfaces:**
- `SectSummary` adds `kind_label`, `entry_realm_label`, and `task_preference_label`.
- `TechniqueSummary` adds `technique_type_label` and `required_realm_label`.
- `CultivationOverview` adds `realm_label`.
- NPC and event summaries return Chinese system descriptions while preserving `event_key`.

- [ ] **Step 1: Add failing API contract assertions**

```python
def test_cultivation_api_returns_labels_without_removing_keys(client, auth_headers):
    response = client.get("/api/cultivation/sects?star=1", headers=auth_headers)
    item = response.json()[0]
    assert item["kind"] == "normal"
    assert item["kind_label"] == "普通宗门"
    assert item["entry_realm_label"]
```

- [ ] **Step 2: Run the focused API test and verify it fails**

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_localization.py::test_cultivation_api_returns_labels_without_removing_keys -q
```

- [ ] **Step 3: Add labels at the schema/service boundary**

Build labels from `content_catalog.py`, keep the existing key fields unchanged, and make missing labels fall back to the raw key only for backward compatibility.

- [ ] **Step 4: Localize generated descriptions**

Change check-in, reward, NPC meeting, achievement transaction, and cultivation log descriptions to Chinese templates. Audit title descriptions and system finance category names in `title.py` and `finance.py`; preserve already-Chinese values and change only user-visible English values. Keep user-supplied descriptions untouched.

- [ ] **Step 5: Run API and regression tests**

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests/test_content_localization.py tests/test_cultivation.py tests/test_todos.py -q
```

- [ ] **Step 6: Commit the API layer**

```powershell
git add backend/app/schemas/cultivation.py backend/app/services/cultivation.py backend/app/api/cultivation.py backend/app/services/checkin.py backend/app/services/coin.py backend/app/services/achievement.py backend/tests/test_cultivation.py backend/tests/test_content_localization.py
git commit -m "feat(localization): expose chinese api labels"
```

### Task 4: 统一错误提示和前端动态标签

**Files:**
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/utils/errorMessage.js`
- Modify: all pages currently using `error.response?.data?.detail`, including `frontend/src/views/Home.vue`, `Todos.vue`, `Backpack.vue`, `Finance*.vue`, `Projects.vue`, `Notes.vue`, and `EditProfile.vue`
- Modify: `frontend/src/views/localization-regressions.test.mjs`

**Interfaces:**
- Every page catch block passes the caught error through `getErrorMessage(error)`.
- `api.js` uses the same converter for 400, 404, 409, 422, 500 and network errors.
- Machine keys such as `SLOT_CONFLICT:DUPLICATE_TECHNIQUE` map to actionable Chinese messages.

- [ ] **Step 1: Add failing error mapping tests**

```js
test('error messages translate backend details and machine codes', async () => {
  const { getErrorMessage } = await import('../utils/errorMessage.js')
  assert.equal(getErrorMessage({ response: { data: { detail: 'Task not found' } } }), '任务不存在。')
  assert.equal(getErrorMessage({ response: { data: { detail: 'SLOT_CONFLICT:DUPLICATE_TECHNIQUE' } } }), '同一功法不能重复配置。')
})
```

- [ ] **Step 2: Implement the shared converter and replace direct detail reads**

Preserve Chinese server details when already localized; translate known English details and machine codes; use `网络连接失败，请检查网络。` for missing responses and `操作失败，请重试。` as the final fallback.

- [ ] **Step 3: Run the frontend tests**

```powershell
cd frontend
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
```

- [ ] **Step 4: Commit error handling**

```powershell
git add frontend/src/services/api.js frontend/src/utils/errorMessage.js frontend/src/views frontend/src/components
git commit -m "fix(localization): translate api errors and labels"
```

### Task 5: 中文化修仙页面和公共布局

**Files:**
- Modify: `frontend/src/components/cultivation/CultivationStatusBar.vue`
- Modify: `frontend/src/components/cultivation/RealmProgress.vue`
- Modify: `frontend/src/components/cultivation/ResourceSummary.vue`
- Modify: `frontend/src/components/cultivation/RewardToast.vue`
- Modify: `frontend/src/components/cultivation/TechniqueSlotGrid.vue`
- Modify: `frontend/src/components/cultivation/NpcTimeline.vue`
- Modify: `frontend/src/components/cultivation/MapNode.vue`
- Modify: `frontend/src/views/Cultivation.vue`, `World.vue`, `Sects.vue`, `Techniques.vue`, `Npcs.vue`, `Tribulations.vue`
- Modify: `frontend/src/components/layout/AppLayout.vue`, `Header.vue`, `Sidebar.vue`
- Test: `frontend/src/views/localization-regressions.test.mjs`

**Interfaces:**
- Every displayed realm, resource, sect type, technique type, NPC role and status uses server `*_label` first, then `displayLabels.js`.
- User-visible copy in these components contains no known English UI literals except the `LifeQuest` brand and intentional technical abbreviations.

- [ ] **Step 1: Add static regression assertions for cultivation copy**

Assert that the cultivation component sources contain Chinese replacements for retry, resources, realm progress, reward and NPC fallback states, and do not contain the known English labels.

- [ ] **Step 2: Replace cultivation and navigation copy**

Use the shared label functions and Chinese dictionaries. Do not rename component props, API fields, stable keys or CSS class names unless a layout fix requires it.

- [ ] **Step 3: Run focused tests and build**

```powershell
cd frontend
node --test src/views/localization-regressions.test.mjs src/views/cultivation-regressions.test.mjs
npm run build
```

- [ ] **Step 4: Commit cultivation localization**

```powershell
git add frontend/src/components/cultivation frontend/src/components/layout frontend/src/views/Cultivation.vue frontend/src/views/World.vue frontend/src/views/Sects.vue frontend/src/views/Techniques.vue frontend/src/views/Npcs.vue frontend/src/views/Tribulations.vue frontend/src/views/localization-regressions.test.mjs
git commit -m "fix(localization): translate cultivation interface"
```

### Task 6: 中文化原有业务页面和历史展示

**Files:**
- Modify: `frontend/src/views/Login.vue`, `Register.vue`, `Home.vue`, `Todos.vue`, `Profile.vue`, `Projects.vue`, `Shop.vue`
- Modify: `frontend/src/views/NoteEditor.vue`, `Notes.vue`, `NotebookFileManage.vue`
- Modify: `frontend/src/views/Finance.vue`, `FinanceAccounts.vue`, `FinanceBudgets.vue`, `FinanceDebts.vue`, `FinanceTransactions.vue`
- Modify: `frontend/src/views/Backpack.vue`, `BackpackHistory.vue`, `ExchangeHistory.vue`, `CoinHistory.vue`, `Stats.vue`
- Test: `frontend/src/views/localization-regressions.test.mjs`

**Interfaces:**
- All static headings, kickers, placeholders, dialog labels, accessibility labels and status fallbacks use Chinese copy.
- Existing formatters for difficulty, frequency, account type, period, source and project status are moved to or delegated through `displayLabels.js`.
- User-entered names and descriptions render unchanged.

- [ ] **Step 1: Add static scan assertions for legacy pages**

Maintain a list of forbidden user-facing literals such as `PERSONAL PROGRESS SYSTEM`, `DAILY PROGRESS`, `PLAYER SUMMARY`, `Loading note...`, `Wallet summary`, `TIMELINE` and assert they are absent from template sections.

- [ ] **Step 2: Replace static copy and direct enum rendering**

Translate headings and placeholders; replace direct `realm_key`, category, status, type, difficulty and source rendering with shared label helpers; retain values used for filtering and API requests.

- [ ] **Step 3: Run all frontend static tests and build**

```powershell
cd frontend
node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/cultivation-regressions.test.mjs src/views/localization-regressions.test.mjs
npm run build
```

- [ ] **Step 4: Commit legacy localization**

```powershell
git add frontend/src/views frontend/src/components frontend/src/utils frontend/src/locales
git commit -m "fix(localization): translate legacy pages"
```

### Task 7: 中文替换后的 UI 回归和最终验证

**Files:**
- Modify only layout files discovered during visual verification.
- Modify: `frontend/src/views/localization-regressions.test.mjs` if a reproducible layout contract is found.
- Create: `docs/superpowers/reports/2026-08-18-lifequest-content-localization-verification.md`

**Interfaces:**
- No business/API behavior changes are allowed in this task; changes are limited to text-fit, wrapping, spacing, overflow and responsive layout fixes.

- [ ] **Step 1: Start the local services**

```powershell
cd backend
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Use another available frontend port when 5173 is occupied.

- [ ] **Step 2: Check the required pages at four viewport sizes**

Inspect `/`, `/todos`, `/cultivation`, `/world`, `/sects`, `/techniques`, `/npcs`, `/tribulations`, `/notes`, `/shop`, `/backpack`, `/finance` and `/profile` at `375x900`, `768x900`, `1024x900` and `1440x900`.

Record for each page: visible Chinese copy, horizontal overflow, title/button wrapping, long content behavior, modal fit, loading/error/empty state fit, mobile navigation and desktop sidebar.

- [ ] **Step 3: Fix only verified layout regressions**

For each observed issue, adjust the smallest relevant CSS rule, such as `min-width`, `max-width`, `line-height`, `word-break`, `white-space`, grid tracks or responsive spacing. Recheck the same viewport immediately after each fix.

- [ ] **Step 4: Run final automated verification**

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest -q

cd ../frontend
node --test src/composables/useNoteAutosave.test.mjs src/views/ui-regressions.test.mjs src/views/sects-request-state.test.mjs src/views/cultivation-regressions.test.mjs src/views/localization-regressions.test.mjs
npm run build

cd ..
git diff --check
```

- [ ] **Step 5: Write the verification report**

Record exact pass counts, build warnings, database migration checks, route coverage, viewport results and any authenticated-state limitation. Do not describe a static test as a visual result.

- [ ] **Step 6: Commit final UI verification**

```powershell
git add frontend docs/superpowers/reports/2026-08-18-lifequest-content-localization-verification.md
git commit -m "test(localization): verify chinese content and ui layout"
```

## Final Review Checklist

- [ ] `git diff --check` is clean.
- [ ] No user files in `.agents/`, `.claude/skills/`, `.codex/`, `frontend/components.d.ts`, `frontend/vite-check.log` or the existing closure plan are staged.
- [ ] Database backfill is idempotent and user-owned content is preserved.
- [ ] Internal keys remain stable and are not rendered directly.
- [ ] Backend and frontend automated tests pass.
- [ ] Production build passes.
- [ ] All four viewport groups were visually checked after text replacement.
