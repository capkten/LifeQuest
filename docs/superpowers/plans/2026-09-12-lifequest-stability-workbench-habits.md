# LifeQuest 稳定性、今日工作台与习惯闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复六个已复现的跨用户、财务、习惯和日期问题，并按统一业务不变量重新验收 FEAT-01 今日工作台与 FEAT-02 习惯计划和记录能力。

**Architecture:** 保留现有 FastAPI、SQLAlchemy、Vue 3 服务层边界；只增加一个聚焦的习惯指标模块和必要的日期工具。后端以用户锁、数据库原子更新、完成记录和工作台 revision 作为权威状态，前端只提交操作并展示服务端结果，异步请求通过 generation、幂等 request ID 和独立错误状态防止旧结果覆盖新状态。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Vue 3, Vite, Node `node:test`, Playwright, SQLite test databases.

**Spec:** `docs/superpowers/specs/2026-09-12-lifequest-stability-workbench-habits-design.md`

## Global Constraints

- 项目版本唯一来源是根目录 `VERSION`；当前工作树版本为 `1.13.0`，任何版本递增必须先修改 `VERSION`，再运行 `cd frontend && npm run sync:version`。
- 后端继续以 UTC 保存时间戳，以 `Asia/Shanghai` 计算业务日期和日期区间。
- 前端所有“今天”“昨天”“日期输入默认值”“日历当前月/今天标记”都通过共享日期工具计算，不直接调用 `toISOString().slice(0, 10)` 或浏览器本地 `getFullYear/getMonth/getDate` 作为业务日期。
- 每日习惯同一中国日最多一条完成记录；每周目标周期固定为周一至周日，完成槽位为每周 `min(实际完成数, weekly_target)`。
- 普通打卡和补记都检查每周目标上限；目标已满返回 `409`，不新增记录、不发放奖励、不改变连续周期。
- 补记只能写入最近 90 天内、习惯创建日之后、有效计划日且不在暂停或请假区间的日期；补记不发放奖励并保留 `is_makeup` 标记。
- 习惯历史只使用 `habit_completions(habit_id, completed_on)` 证明的完成日期，不根据 `last_completed_at`、连续数或其他间接字段伪造历史。
- 财务每一个减少余额的有效操作都使用带余额条件的数据库原子更新；修改流水先反向旧影响，再校验并应用新影响，失败时整个事务回滚。
- 财务同一中国日最多发放一笔首笔流水经验奖励；当前待保存流水必须在奖励查询前 flush。
- 旧非法项目关联采用读取隔离，不自动修改历史任务归属；项目读取和统计只允许 `Task.user_id == Project.user_id` 的任务参与。
- 今日重点最多三项，保留选择顺序；旧 revision 返回 `409`；快速创建的同一用户、同一 request ID 和同一内容只创建一条任务。
- 工作台完成必须调用既有待办完成结算路径；服务端成功后才显示完成，奖励或刷新失败不得诱导重复提交。
- 本轮不实现 FEAT-03 至 FEAT-10，不展开 ENG-02、ENG-03、ENG-05、ENG-06 的独立改造；本轮不改变退款规则：不支持部分退款，按同种可用背包数量整体核验，不绑定具体订单物品来源。
- 不进行大规模服务拆分；新增模块只承担习惯指标或日期转换的单一职责。
- 保留当前工作树中所有无关用户修改，尤其是 `docs/superpowers/` 下已有文件；提交时只暂存当前任务所属文件。
- 每个任务必须先写失败回归测试，再运行确认失败，再写最小实现，最后运行专项测试和相关全量测试。

## File Map

- 项目读取隔离：`backend/app/services/project.py`、`backend/app/api/projects.py`、`backend/tests/test_audit_fixes.py`。
- 财务原子余额与首笔奖励：`backend/app/services/finance.py`、`backend/tests/test_audit_fixes.py`、`backend/tests/test_finance.py`。
- 习惯指标和完成记录：新建 `backend/app/services/habit_metrics.py`，修改 `backend/app/services/todo.py`、`backend/app/services/stats.py`，测试 `backend/tests/test_habit_schedule.py` 和 `backend/tests/test_audit_fixes.py`。
- 中国日期工具：`frontend/src/utils/dateTime.js`、新建 `frontend/src/utils/dateTime.test.mjs`，以及 `Finance.vue`、`FinanceTransactions.vue`、`FinanceDebts.vue`、`Calendar.vue`、`WorkbenchTaskRow.vue`。
- FEAT-01 工作台：`backend/app/services/daily_workbench.py`、`backend/tests/test_daily_workbench.py`、`frontend/src/composables/useDailyWorkbench.js`、`frontend/src/composables/useDailyWorkbench.test.mjs`、`frontend/src/components/home/TodayWorkbench.vue`。
- FEAT-02 页面交互：`frontend/src/views/Home.vue`、`frontend/src/views/Todos.vue`、`frontend/src/components/HabitHistoryDialog.vue`、`frontend/src/views/ui-regressions.test.mjs`、`frontend/src/views/audit-fixes.test.mjs`。
- 最终证据：新建 `docs/superpowers/reports/2026-09-12-lifequest-stability-workbench-habits-verification.md`，按证据更新 `docs/2026-09-12-lifequest-improvement-roadmap.md` 和 `.harness/completion-ledger.json`；只有发布证据存在时才更新状态。

---

### Task 1: 隔离项目旧非法任务关联

**Files:**
- Modify: `backend/app/services/project.py:99-108,236-280`
- Modify: `backend/app/api/projects.py:259-278`
- Test: `backend/tests/test_audit_fixes.py`

**Interfaces:**
- Change `ProjectService.get_project_tasks` to `get_project_tasks(project_id: UUID, user_id: UUID, phase_id: Optional[UUID] = None, milestone_id: Optional[UUID] = None) -> List[Task]`.
- Keep `ProjectService.get_project_detail(project_id: UUID, user_id: UUID) -> dict` and `ProjectService._compute_project_stats(project: Project) -> dict` as the service response boundaries.
- The project API must call `get_project_tasks(project_id, current_user.id, phase_id, milestone_id)` after `get_project_for_user` succeeds.

- [ ] **Step 1: Write the failing regression test.** Add a project owned by `owner`, a completed task owned by `other` but manually linked to the owner’s project to model legacy bad data, and assert that the service currently returns the task and counts it. The fixed assertions must be:

```python
def test_legacy_foreign_project_tasks_are_hidden_from_project_reads(client, db_session):
    owner, other = make_user(db_session), make_user(db_session)
    project = Project(user_id=owner.id, name="私有项目")
    db_session.add(project)
    db_session.flush()
    db_session.add(Task(
        user_id=other.id,
        project_id=project.id,
        title="不属于项目所有者的旧任务",
        status=TaskStatus.COMPLETED,
    ))
    db_session.commit()

    service = ProjectService(db_session)
    detail = service.get_project_detail(project.id, owner.id)
    assert detail["tasks"] == []
    assert detail["total_tasks"] == 0
    assert detail["completed_tasks"] == 0
    assert detail["progress"] == 0.0
    assert service.get_project_tasks(project.id, owner.id) == []

    auth = {"Authorization": "Bearer " + create_access_token({"sub": str(owner.id)})}
    listed = client.get("/api/projects", headers=auth)
    assert listed.status_code == 200
    assert listed.json()[0]["total_tasks"] == 0
    project_tasks = client.get(f"/api/projects/{project.id}/tasks", headers=auth)
    assert project_tasks.status_code == 200
    assert project_tasks.json() == []
```

- [ ] **Step 2: Run the focused test and confirm it fails.**

```bash
cd backend && venv/bin/pytest tests/test_audit_fixes.py::test_legacy_foreign_project_tasks_are_hidden_from_project_reads -q
```

Expected: `FAIL`, because the current detail, list, and statistics queries filter only `Task.project_id`.

- [ ] **Step 3: Implement the ownership filters.** Add `Task.user_id == project.user_id` to both task queries inside `get_project_detail` and `_compute_project_stats`. Add `Task.user_id == user_id` to `get_project_tasks` alongside the project, phase, and milestone filters, and pass `current_user.id` from `backend/app/api/projects.py`.

- [ ] **Step 4: Run the focused and adjacent project tests.**

```bash
cd backend && venv/bin/pytest tests/test_audit_fixes.py::test_legacy_foreign_project_tasks_are_hidden_from_project_reads tests/test_projects.py -q
```

Expected: all selected tests pass, including existing write-side project and phase ownership tests.

- [ ] **Step 5: Commit only this task.**

```bash
git add backend/app/services/project.py backend/app/api/projects.py backend/tests/test_audit_fixes.py
git commit -m "fix(projects): isolate legacy task reads by owner"
```

### Task 2: 修复财务流水修改和首笔经验奖励

**Files:**
- Modify: `backend/app/services/finance.py:74-85,173-183,213-247,278-311,516-533`
- Test: `backend/tests/test_audit_fixes.py`
- Test: `backend/tests/test_finance.py`

**Interfaces:**
- Keep `_change_balance(account_id: UUID, amount: Decimal, require_sufficient: bool = False) -> None` as the atomic balance primitive.
- Keep `_apply_transaction_balance_effect(transaction: FinanceTransaction, reverse: bool = False) -> None`; it must derive the balance requirement from `reverse`, requiring sufficient balance only for a new expense debit or transfer source debit.
- Keep `FinanceService.update_transaction(transaction: FinanceTransaction, data: TransactionUpdate, user_id: UUID) -> FinanceTransaction` and `FinanceService.delete_transaction(transaction: FinanceTransaction) -> bool` transactionally guarded by `rollback_on_error`.

- [ ] **Step 1: Write regression tests for insufficient update rollback and flush-dependent rewards.** Add the following tests to the existing SQLite file-database section:

```python
def test_updating_transfer_beyond_source_balance_rolls_back_everything(database):
    session, factory = database
    user = make_user(session)
    source, target = make_account(session, user, 100), make_account(session, user, 0)
    created = FinanceService(session).transfer(user.id, source.id, target.id, 80)
    transaction = created["transaction"]

    with pytest.raises(HTTPException) as error:
        FinanceService(session).update_transaction(
            transaction,
            TransactionUpdate(amount=150),
            user.id,
        )

    assert error.value.status_code == 400
    session.refresh(source)
    session.refresh(target)
    session.refresh(transaction)
    assert source.balance == 20
    assert target.balance == 80
    assert transaction.amount == Decimal("80.00")
    assert transaction.type == "transfer"
    assert session.query(FinanceTransaction).count() == 1


def test_same_china_day_finance_reward_is_awarded_only_for_first_transaction(database):
    session, factory = database
    user = make_user(session)
    account = make_account(session, user, 100)
    service = FinanceService(session)

    expense(session, user.id, account.id, 10)
    session.refresh(user)
    first_experience = user.experience
    expense(session, user.id, account.id, 10)
    session.refresh(user)

    assert first_experience == 7
    assert user.experience == 9
    assert session.query(FinanceTransaction).filter_by(user_id=user.id, date=date(2026, 9, 12)).count() == 2
```

- [ ] **Step 2: Run the new tests and confirm the current failures.**

```bash
cd backend && venv/bin/pytest tests/test_audit_fixes.py::test_updating_transfer_beyond_source_balance_rolls_back_everything tests/test_audit_fixes.py::test_same_china_day_finance_reward_is_awarded_only_for_first_transaction -q
```

Expected: the transfer update can create a negative source balance, and the second transaction can receive the first-transaction bonus because the pending row is not visible to the count query.

- [ ] **Step 3: Make debit application and transaction validation atomic.** In `update_transaction`, lock the user and current row with `_lock_transaction`, compute effective `account_id`, `type`, `amount`, and `to_account_id`, validate both accounts and categories, reject a transfer without a target or with the same source and target, and reject a non-transfer carrying a target. Reverse the old effect with `reverse=True`, assign the validated update fields, flush the new row state, then apply the new effect with `reverse=False` and commit. The reverse path must never require current balance sufficiency; the new expense and transfer-source path must call `_change_balance(..., require_sufficient=True)`.

- [ ] **Step 4: Flush the new transaction before awarding experience.** In `create_transaction`, retain the existing user lock and balance update, call `self.db.flush()` immediately after adding the transaction and applying its balance effect, then call `_award_transaction_exp`. Keep reward, achievement, commit, and rollback in the same transaction so a failure removes both the reward and the transaction.

- [ ] **Step 5: Run all finance regressions.**

```bash
cd backend && venv/bin/pytest tests/test_audit_fixes.py tests/test_finance.py tests/test_finance_security.py -q
```

Expected: all selected tests pass; the update failure leaves the old transaction and both old balances intact, and the two same-day transactions add exactly `7 + 2` experience.

- [ ] **Step 6: Commit only this task.**

```bash
git add backend/app/services/finance.py backend/tests/test_audit_fixes.py backend/tests/test_finance.py
git commit -m "fix(finance): enforce atomic transaction updates and rewards"
```

### Task 3: 统一习惯指标并封闭每周补记上限

**Files:**
- Create: `backend/app/services/habit_metrics.py`
- Modify: `backend/app/services/todo.py:105-196,198-281,392-495,605-731,958-1040`
- Modify: `backend/app/services/stats.py:85-102`
- Test: `backend/tests/test_habit_schedule.py`
- Test: `backend/tests/test_audit_fixes.py`

**Interfaces:**
- Create immutable result type `HabitMetrics(total_completed: int, scheduled_count: int, completed_count: int, completion_rate: float)` in `backend/app/services/habit_metrics.py`.
- Create `calculate_habit_metrics(habit: Habit, completion_dates: Collection[date], period_start: date, period_end: date, pause_intervals: Sequence = (), leave_intervals: Sequence = ()) -> HabitMetrics`; `period_start` and `period_end` are inclusive China-local date keys.
- Create `weekly_target_progress(habit: Habit, completion_dates: Collection[date], target_date: date, pause_intervals: Sequence = (), leave_intervals: Sequence = ()) -> tuple[int, int]`, returning capped `(weekly_completed, weekly_remaining)`.
- `TodoService._habit_metrics` must obtain completion dates from `HabitCompletion` and delegate all denominator/numerator calculations to `calculate_habit_metrics`.
- `TodoService._set_completed_today` must use the completion-date set for `completed_today`; `TodoService.get_habit_history` must use the same helper for `scheduled_count`, `completed_count`, and `completion_rate`.

- [ ] **Step 1: Add regression tests for one source of truth, historical facts, and backfill capacity.** Add these cases to `backend/tests/test_habit_schedule.py`:

```python
def test_weekly_target_list_and_history_use_target_slots(client, db_session, clock):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="力量训练",
        frequency="weekly_target",
        weekly_target=3,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.flush()
    for completed_on in (date(2026, 9, 1), date(2026, 9, 3), date(2026, 9, 5), date(2026, 9, 8)):
        db_session.add(HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        ))
    db_session.commit()

    service = TodoService(db_session)
    current = service._set_completed_today(habit)
    history = service.get_habit_history(
        habit.id,
        user.id,
        start_on=date(2026, 9, 3),
        end_on=date(2026, 9, 12),
    )

    assert current.scheduled_count == 6
    assert current.completed_count == 4
    assert current.completion_rate == round(4 / 6 * 100, 1)
    assert history["scheduled_count"] == 6
    assert history["completed_count"] == 4
    assert history["completion_rate"] == round(4 / 6 * 100, 1)


def test_last_completed_at_without_a_completion_record_does_not_create_history(database, clock):
    session, factory = database
    user = make_user(session)
    habit = Habit(
        user_id=user.id,
        title="无法证明的旧完成",
        last_completed_at=datetime(2026, 9, 11, 16),
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    session.add(habit)
    session.commit()
    service = TodoService(session)

    current = service._set_completed_today(habit)
    history = service.get_habit_history(
        habit.id,
        user.id,
        start_on=date(2026, 9, 11),
        end_on=date(2026, 9, 11),
    )

    assert current.total_completed == 0
    assert current.completed_today is False
    assert history["days"][0]["completed"] is False


def test_weekly_target_backfill_cannot_exceed_target(database, clock):
    session, factory = database
    user = make_user(session)
    habit = Habit(
        user_id=user.id,
        title="补记上限",
        frequency="weekly_target",
        weekly_target=3,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    session.add(habit)
    session.flush()
    for completed_on in (date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10)):
        session.add(HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        ))
    session.commit()
    service = TodoService(session)

    with pytest.raises(HTTPException) as error:
        service.backfill_habit(
            habit,
            user.id,
            HabitBackfillCreate(completed_on=date(2026, 9, 11), note="不应写入"),
        )

    assert error.value.status_code == 409
    assert session.query(HabitCompletion).filter_by(habit_id=habit.id).count() == 3
```

- [ ] **Step 2: Run the new tests and confirm the current failures.**

```bash
cd backend && venv/bin/pytest tests/test_habit_schedule.py::test_weekly_target_list_and_history_use_target_slots tests/test_habit_schedule.py::test_last_completed_at_without_a_completion_record_does_not_create_history tests/test_habit_schedule.py::test_weekly_target_backfill_cannot_exceed_target -q
```

Expected: history reports daily planned dates instead of weekly target slots, `last_completed_at` appears as a fabricated completion, and backfill inserts a fourth weekly completion.

- [ ] **Step 3: Implement the shared metric formulas.** In `habit_metrics.py`, iterate China-local dates for non-`weekly_target` habits and count only valid planned, non-paused, non-excused dates. For `weekly_target`, iterate every week whose date range intersects `[period_start, period_end]`, require at least one valid planned date after the habit creation date, add `habit.weekly_target` denominator slots once per active week, and add `min(weekly_target, number_of_completion_dates_in_week)` numerator slots. Always set `total_completed` to the size of the supplied completion-date set and round the rate to one decimal place. `weekly_target_progress` must apply the same exclusion rules and cap the displayed completed value at the target.

- [ ] **Step 4: Route all TodoService paths through the helper and completion table.** Remove the `last_completed_at` fallback from `_habit_metrics` and `_recalculate_habit_streak`. In `complete_habit`, query the current China date in `HabitCompletion` under the existing user lock; update an existing record’s note and return without reward, otherwise enforce `_weekly_completion_count` before inserting. In `backfill_habit`, check an existing date first so an idempotent note update remains allowed, then enforce weekly capacity before `record_completion`. Keep the existing 90-day, creation-date, plan-day, pause, leave, and no-reward rules. Set `completed_today` from the current completion-date set and set weekly display values from `weekly_target_progress`.

- [ ] **Step 5: Make history and statistics fact-based.** Replace the daily `scheduled_count` and `completed_count` arithmetic in `get_habit_history` with `calculate_habit_metrics`, while keeping the day grid’s `scheduled` field as a per-day executable indicator. In `StatsService.get_habit_stats`, remove the `last_completed_at` fallback and count only unique `HabitCompletion.completed_on` rows; keep the existing `{date, total, completed}` response shape for the chart.

- [ ] **Step 6: Run habit regressions and all backend tests.**

```bash
cd backend && venv/bin/pytest tests/test_habit_schedule.py tests/test_audit_fixes.py -q
cd backend && venv/bin/pytest -q
```

Expected: all weekly target, pause/leave, streak, history, China-midnight, reward, and migration tests pass; no test relies on an inferred completion date.

- [ ] **Step 7: Commit only this task.**

```bash
git add backend/app/services/habit_metrics.py backend/app/services/todo.py backend/app/services/stats.py backend/tests/test_habit_schedule.py backend/tests/test_audit_fixes.py
git commit -m "fix(habits): unify weekly metrics and backfill limits"
```

### Task 4: 统一前端中国日期和时间显示

**Files:**
- Modify: `frontend/src/utils/dateTime.js`
- Create: `frontend/src/utils/dateTime.test.mjs`
- Modify: `frontend/src/views/Finance.vue:358-412`
- Modify: `frontend/src/views/FinanceTransactions.vue:350-450`
- Modify: `frontend/src/views/FinanceDebts.vue:263-311`
- Modify: `frontend/src/views/Calendar.vue:316-515`
- Modify: `frontend/src/components/home/WorkbenchTaskRow.vue:24-36`
- Test: `frontend/src/views/audit-fixes.test.mjs`

**Interfaces:**
- Preserve `formatDateTimeInput(value) -> string` for native `datetime-local` editing.
- Add `chinaDateKey(value = new Date()) -> string | null`; a pure `YYYY-MM-DD` input must be returned as a date key without browser-local re-interpretation.
- Add `todayChinaDateKey(value = new Date()) -> string`.
- Add `shiftDateKey(dateKey: string, amount: number) -> string` using UTC date-only arithmetic.
- Add `dateKeyFromParts(year: number, monthIndex: number, day: number) -> string` and `dateKeyParts(dateKey: string) -> { year: number, monthIndex: number, day: number }` for calendar calculations.
- Add `weekdayForDateKey(dateKey: string) -> number` with Monday represented as `0` and Sunday as `6`.
- Add `formatChinaDate(value, options = {}) -> string` and `formatChinaDateTime(value, options = {}) -> string`, both using `Asia/Shanghai` and treating pure date keys as date-only values.

- [ ] **Step 1: Write timezone-independent utility tests.** Create `frontend/src/utils/dateTime.test.mjs` with these assertions:

```javascript
import assert from 'node:assert/strict'
import test from 'node:test'
import {
  chinaDateKey,
  dateKeyFromParts,
  dateKeyParts,
  formatChinaDate,
  shiftDateKey,
  todayChinaDateKey,
  weekdayForDateKey,
} from './dateTime.js'

test('China date keys ignore the browser runtime timezone', () => {
  for (const timezone of ['UTC', 'Asia/Shanghai', 'America/Los_Angeles']) {
    process.env.TZ = timezone
    assert.equal(chinaDateKey('2026-09-11T15:59:59Z'), '2026-09-11')
    assert.equal(chinaDateKey('2026-09-11T16:00:00Z'), '2026-09-12')
    assert.equal(chinaDateKey('2026-09-12'), '2026-09-12')
  }
  assert.equal(todayChinaDateKey(new Date('2026-09-11T16:00:00Z')), '2026-09-12')
  assert.equal(shiftDateKey('2026-03-01', -1), '2026-02-28')
  assert.equal(shiftDateKey('2026-12-31', 1), '2027-01-01')
  assert.deepEqual(dateKeyParts('2026-09-12'), { year: 2026, monthIndex: 8, day: 12 })
  assert.equal(dateKeyFromParts(2026, 8, 12), '2026-09-12')
  assert.equal(weekdayForDateKey('2026-09-14'), 0)
  assert.equal(formatChinaDate('2026-09-12', { year: 'numeric', month: '2-digit', day: '2-digit' }), '2026/09/12')
})
```

- [ ] **Step 2: Run the utility test and confirm the missing exports or incorrect behavior.**

```bash
cd frontend && node --test src/utils/dateTime.test.mjs
```

Expected: `FAIL` until the shared date-key functions exist and return the fixed China-local results.

- [ ] **Step 3: Implement the date utility without changing datetime-local semantics.** Keep `formatDateTimeInput` unchanged for editing instants. Add strict date-key parsing, `Intl.DateTimeFormat(..., { timeZone: 'Asia/Shanghai' })` for timestamp conversion, and UTC-only `Date.UTC` arithmetic for date keys. Return an empty string or `null` for invalid inputs according to each function’s declared return type.

- [ ] **Step 4: Migrate all finance, calendar, and deadline displays.** Replace finance form defaults with `todayChinaDateKey()`, format pure transaction/debt dates with `formatChinaDate`, and compare debt due dates to `todayChinaDateKey()` as date keys. In `FinanceTransactions.vue`, group by `chinaDateKey(tx.date)` and calculate “今天/昨天” with `shiftDateKey`. In `Calendar.vue`, initialize and navigate month cells through `dateKeyParts`, `dateKeyFromParts`, `shiftDateKey`, and `weekdayForDateKey`; remove local `new Date(year, month, day)` and browser `getFullYear/getMonth/getDate` business calculations. Use `formatChinaDateTime` for `WorkbenchTaskRow` deadlines.

- [ ] **Step 5: Add static migration guards.** Extend `frontend/src/views/audit-fixes.test.mjs` to read `Finance.vue`, `FinanceTransactions.vue`, `FinanceDebts.vue`, and `Calendar.vue`, assert they import the shared date utility, and assert none contains `new Date().toISOString().split('T')[0]`, browser-local `getFullYear/getMonth/getDate` business calculations, or a second local `shiftDate` implementation.

- [ ] **Step 6: Run frontend utility, regression, and build checks.**

```bash
cd frontend && node --test src/utils/dateTime.test.mjs src/views/audit-fixes.test.mjs src/views/ui-regressions.test.mjs
cd frontend && npm test
cd frontend && npm run build
```

Expected: all date-key cases pass under the three runtime timezones, existing `formatDateTimeInput` tests still pass, and the production build completes.

- [ ] **Step 7: Commit only this task.**

```bash
git add frontend/src/utils/dateTime.js frontend/src/utils/dateTime.test.mjs frontend/src/views/Finance.vue frontend/src/views/FinanceTransactions.vue frontend/src/views/FinanceDebts.vue frontend/src/views/Calendar.vue frontend/src/components/home/WorkbenchTaskRow.vue frontend/src/views/audit-fixes.test.mjs
git commit -m "fix(frontend): centralize China date handling"
```

### Task 5: 加固 FEAT-01 工作台后端和异步状态机

**Files:**
- Modify: `backend/app/services/daily_workbench.py:20-114`
- Test: `backend/tests/test_daily_workbench.py`
- Modify: `frontend/src/composables/useDailyWorkbench.js:15-240`
- Test: `frontend/src/composables/useDailyWorkbench.test.mjs`
- Modify: `frontend/src/components/home/TodayWorkbench.vue:126-200`

**Interfaces:**
- Add private `DailyWorkbenchService._parse_focus_task_ids(plan: DailyFocusPlan | None) -> list[UUID]`; it returns at most three valid, unique IDs in stored order and never mutates the persisted plan.
- Keep `get_workbench(user_id: UUID) -> dict`, `update_focus(user_id: UUID, data: DailyFocusUpdate) -> dict`, and `create_quick_task(user_id: UUID, data: QuickTaskCreate) -> Task` as the API boundaries.
- Keep `useDailyWorkbench(api, options)` as the only frontend workbench request entry point; its public state remains `data`, `loading`, `loadError`, `actionError`, `feedback`, `warning`, `pendingAction`, `draft`, `editingFocus`, `focusDraft`, and `focusError`.
- Re-export `chinaDateKey` from `frontend/src/composables/useDailyWorkbench.js` during migration so existing imports remain compatible, but make `frontend/src/utils/dateTime.js` the single implementation.

- [ ] **Step 1: Add a backend test for corrupted legacy focus JSON.** Insert a `DailyFocusPlan` whose `task_ids` contains an invalid UUID, a duplicate, a missing task ID, and one valid user task. Assert `GET /api/todos/workbench` returns `200`, returns only the valid task once, keeps the stored JSON untouched, and reports the stored revision.

```python
def test_corrupt_focus_ids_are_filtered_without_failing_workbench(client, db_session, clock):
    user = make_user(db_session)
    valid = make_task(db_session, user, title="仍然有效")
    missing_id = str(uuid4())
    plan = DailyFocusPlan(
        user_id=user.id,
        plan_date=date(2026, 9, 12),
        task_ids=["not-a-uuid", str(valid.id), str(valid.id), missing_id],
        revision=4,
    )
    db_session.add(plan)
    db_session.commit()

    response = client.get("/api/todos/workbench", headers=headers(user))

    assert response.status_code == 200
    body = response.json()
    assert [task["id"] for task in body["focus_tasks"]] == [str(valid.id)]
    assert body["revision"] == 4
    db_session.refresh(plan)
    assert plan.task_ids == ["not-a-uuid", str(valid.id), str(valid.id), missing_id]
```

- [ ] **Step 2: Run the focused backend test and confirm the current `UUID(task_id)` conversion fails.**

```bash
cd backend && venv/bin/pytest tests/test_daily_workbench.py::test_corrupt_focus_ids_are_filtered_without_failing_workbench -q
```

Expected: `FAIL` with a UUID parsing exception.

- [ ] **Step 3: Implement defensive focus parsing and preserve the existing ownership rules.** `_parse_focus_task_ids` must ignore non-list JSON, catch `TypeError`, `ValueError`, and `AttributeError` from `UUID(str(raw))`, deduplicate by UUID, and stop after three valid IDs. `get_workbench` must query those IDs with both `Task.user_id == user_id` and `Task.status != TaskStatus.CANCELLED`; completed focus tasks remain visible. `update_focus` must continue using the user lock, China-date check, revision check, unique request schema, and ownership query.

- [ ] **Step 4: Make quick-create payload comparison canonical.** Persist exactly `{"title": data.title, "schedule": data.schedule, "due_date": data.due_date.isoformat() if data.due_date else None}` in `WorkbenchTaskRequest.payload`. Keep the same request ID for an unacknowledged frontend retry, return the original task for the same payload, return `409` for changed content or a deleted original task, and keep task/request insertion in one transaction.

- [ ] **Step 5: Extend the composable state tests.** Add cases proving a server-returned `date` replaces any stale client date, an old GET cannot replace a successful completion, an initial load error leaves `data === null`, a refresh error preserves prior data and a retry remains available, a lost quick-create response reuses the same request ID, and a disposed composable never calls reward or change callbacks. Keep focus conflict tests asserting the old revision and draft remain intact.

- [ ] **Step 6: Harden the composable and component contract.** Keep one request generation increment for every action and GET; check `active` and generation before every state write. Keep `refreshAfterSuccess` based on `Promise.allSettled`: a successful task completion must remain successful when workbench, reward, or Home refresh fails, and the warning must say no resubmission is needed. Do not refresh over an active focus draft. Make `TodayWorkbench` use `todayChinaDateKey()` only to detect rollover and never overwrite `data.date` with a browser date; retain the no-empty-workbench error branch, retry button, focus keyboard handling, and 44/48px mobile controls.

- [ ] **Step 7: Run the backend and frontend workbench tests.**

```bash
cd backend && venv/bin/pytest tests/test_daily_workbench.py -q
cd frontend && node --test src/composables/useDailyWorkbench.test.mjs
cd frontend && npm test
```

Expected: malformed plans are readable, all workbench race/idempotency tests pass, and no stale response changes the latest state.

- [ ] **Step 8: Commit only this task.**

```bash
git add backend/app/services/daily_workbench.py backend/tests/test_daily_workbench.py frontend/src/composables/useDailyWorkbench.js frontend/src/composables/useDailyWorkbench.test.mjs frontend/src/components/home/TodayWorkbench.vue
git commit -m "fix(workbench): harden legacy focus and async state"
```

### Task 6: 完成 FEAT-02 页面状态、历史请求和跨入口反馈

**Files:**
- Modify: `frontend/src/components/HabitHistoryDialog.vue:145-343`
- Modify: `frontend/src/views/Todos.vue:989-1055,1115-1203`
- Modify: `frontend/src/views/Home.vue:401-444`
- Test: `frontend/src/views/ui-regressions.test.mjs`
- Test: `frontend/src/views/audit-fixes.test.mjs`

**Interfaces:**
- `HabitHistoryDialog` keeps `loadHistory() -> Promise<void>` as its only history request function and must track a monotonically increasing `historyRequestId` plus the requested habit ID.
- `Todos.vue` keeps `completeHabit`, `completeTask`, and `completeGoal` as the action handlers; all post-success reward refreshes must be handled by `settleCompletion(updated)` and must never throw a retryable action error after the backend has committed.
- `Home.vue` keeps `fetchDailySummary() -> Promise<boolean>` and `refreshActionRewards() -> Promise<void>`; a false refresh result is a display warning, not a failed completion.

- [ ] **Step 1: Add failing static regression tests for the FEAT-02 lock contract.** Extend `ui-regressions.test.mjs` to assert `Todos.vue` and `Home.vue` check `completed_today`, `paused_today`, `excused_today`, `scheduled_today`, and `weekly_remaining` before submitting; assert `HabitHistoryDialog.vue` uses the shared `shiftDateKey` and `chinaDateKey` instead of defining another `shiftDate`; assert the post-success reward path uses `Promise.allSettled` and the “无需再次提交” message.

```javascript
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
```

- [ ] **Step 2: Run the new static test and confirm the current gaps.**

```bash
cd frontend && node --test src/views/ui-regressions.test.mjs
```

Expected: `FAIL` because Home does not inspect all lock fields, HistoryDialog owns a duplicate date-shift implementation, and `Todos.vue` can turn an `authStore.fetchUser()` refresh failure into a retryable completion error.

- [ ] **Step 3: Make Home and Todos trust the server lock fields.** In `Home.vue`, return before submission for paused, excused, non-scheduled, weekly-full, or already completed habits; make `fetchDailySummary` return `true` on an accepted response and `false` on a current-generation failure. In `Todos.vue`, use the same lock order in `completeHabit`, and retain `aria-disabled` plus visible reasons so business-locked buttons remain clickable while only in-flight actions use `disabled`.

- [ ] **Step 4: Make reward refresh failures non-retryable.** Refactor `settleCompletion(updated)` so it displays the server settlement immediately, runs `authStore.fetchUser()` and either `cultivationStore.applySettlement(...)` or `cultivationStore.refresh()` through `Promise.allSettled`, and reports “操作已保存，奖励状态刷新失败，请稍后刷新页面，无需再次提交。” without throwing. Keep backend API failures in the outer `catch` with the existing retry callback. Apply the same result handling to task, habit, and goal completion paths.

- [ ] **Step 5: Prevent stale history responses.** Import `chinaDateKey`, `shiftDateKey`, and `weekdayForDateKey` from `frontend/src/utils/dateTime.js`. In `loadHistory`, capture `habitId` and a new request generation, and assign `history`, `error`, and `loading` only when the dialog is still visible, the prop habit ID is unchanged, and the generation is current. Increment the generation when the dialog closes or the habit changes. Keep the day grid factual, preserve `is_makeup`, and label weekly-target denominators as “计划槽位” while non-target denominators remain “计划日”.

- [ ] **Step 6: Run focused frontend tests and build.**

```bash
cd frontend && node --test src/views/ui-regressions.test.mjs src/views/audit-fixes.test.mjs src/composables/useDailyWorkbench.test.mjs
cd frontend && npm test
cd frontend && npm run build
```

Expected: all lock, stale history, completion feedback, date, and mobile UI regressions pass; the build completes without template errors.

- [ ] **Step 7: Commit only this task.**

```bash
git add frontend/src/components/HabitHistoryDialog.vue frontend/src/views/Todos.vue frontend/src/views/Home.vue frontend/src/views/ui-regressions.test.mjs frontend/src/views/audit-fixes.test.mjs
git commit -m "fix(habits): close cross-entry state and history races"
```

### Task 7: 浏览器验收、发布门槛和路线图证据

**Files:**
- Create: `docs/superpowers/reports/2026-09-12-lifequest-stability-workbench-habits-verification.md`
- Modify: `docs/2026-09-12-lifequest-improvement-roadmap.md`
- Modify: `.harness/completion-ledger.json`
- Modify: `VERSION`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

**Interfaces:**
- Browser evidence must identify the backend/frontend URLs, test account strategy, viewport, China-local instant, action, observed response, and screenshot or request-log path for every accepted flow.
- The roadmap must retain the existing historical record and add a dated verification entry; it must not mark a feature complete from a triggered workflow or a local build alone.
- `VERSION` remains the source of truth. The implementation release increments the current `1.13.0` to `1.14.0`, then `frontend/package.json` and `frontend/package-lock.json` are synchronized with `npm run sync:version`.

- [ ] **Step 1: Run the complete automated gate before version changes.**

```bash
cd backend && venv/bin/pytest
cd frontend && npm test
cd frontend && npm run build
git diff --check
```

Expected: backend and frontend tests pass, the production build succeeds, and `git diff --check` emits no output. Record exact pass counts and any existing bundle-size warning in the report.

- [ ] **Step 2: Start real local services against an isolated test database.** Use a temporary `DATABASE_URL`, isolated notes/uploads directories, the existing backend command, and the existing Vite dev command. Create a unique test account through the real registration flow. Do not use the production database or production user data.

```bash
cd backend && DATABASE_URL="sqlite:////tmp/lifequest-stability-browser.sqlite" venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend && VITE_API_BASE_URL="http://127.0.0.1:8000/api" npm run dev -- --host 127.0.0.1 --port 5173
```

- [ ] **Step 3: Execute the FEAT-01 browser matrix.** At desktop wide, desktop narrow, and `390px` mobile width, verify first-viewport workbench rendering, quick creation in all three schedules, completion from each task group, completed-focus retention, three-item focus selection and ordering, stale revision conflict, changed request-ID payload conflict, and load/refresh failure recovery. Capture that the completion response updates the task once and reward-refresh failure displays a no-resubmission warning.

- [ ] **Step 4: Execute the FEAT-02 browser matrix.** Verify daily, specified-weekday, weekly-target, pause/resume, leave/revoke, note, backfill, and history heatmap flows. For a weekly target of `3`, complete three dates and verify both Todos and History show `3/3` target slots; attempt a fourth normal completion and a fourth backfill and verify `409`, no extra record, and no extra reward. Open two habits in succession while delaying the first history response and verify the second habit’s history remains visible.

- [ ] **Step 5: Execute China-midnight and mobile checks.** Run the finance default date, transaction grouping, debt payment date, calendar current-month/today marker, workbench date rollover, and habit-history default-date checks at `2026-09-11T15:59:59Z` and `2026-09-11T16:00:00Z`. Check desktop wide, desktop narrow, `390px` mobile, and the project’s existing `375px` or `768px` reference viewport where available; assert `document.documentElement.scrollWidth <= document.documentElement.clientWidth`, visible focus, and no control overlap.

- [ ] **Step 6: Write the verification report before changing statuses.** Record commands, pass/fail result, viewport dimensions, China-local timestamps, screenshots, response status codes, remaining bundle warning, unavailable Android/CI/production evidence, and any residual risks. Keep FEAT-01/02 marked incomplete until every required browser invariant has evidence.

- [ ] **Step 7: Increment and synchronize the release version after code and browser checks pass.** Change only the first line of `VERSION` from `1.13.0` to `1.14.0`, then run:

```bash
cd frontend && npm run sync:version
cd frontend && npm run check:version
cd frontend && npm run build
```

Do not edit generated package versions independently. Android `versionName` must continue reading `VERSION`; increment Android `versionCode` only when producing an Android package release.

- [ ] **Step 8: Update the roadmap and ledger with evidence-backed states.** Add the verification report path and exact automated/browser evidence to the dated roadmap section. Mark only the six residual fixes and FEAT-01/02 as complete when their tests and browser matrix pass; leave FEAT-03 through FEAT-10 and excluded ENG items unchanged. Keep Android real-device, production-signing, GitHub Actions final success, GitHub Release artifacts, and live health check marked pending until those external conditions are actually verified.

- [ ] **Step 9: Run the final gate and commit release evidence.**

```bash
cd backend && venv/bin/pytest
cd frontend && npm test
cd frontend && npm run check:version
cd frontend && npm run build
git diff --check
git status --short
```

Expected: all commands pass; `git status` contains only files belonging to Tasks 1-7 and the pre-existing user changes remain unstaged or in their original state. Stage the report, roadmap, ledger, version files, and implementation files explicitly, then commit:

```bash
git add VERSION frontend/package.json frontend/package-lock.json docs/superpowers/reports/2026-09-12-lifequest-stability-workbench-habits-verification.md docs/2026-09-12-lifequest-improvement-roadmap.md .harness/completion-ledger.json
git commit -m "chore(release): verify workbench and habit stability closure"
```

## Completion Checklist

- [ ] Project detail, project task list, project list statistics, and legacy foreign associations are read-isolated.
- [ ] Expense and transfer updates cannot overdraw accounts; failed updates restore old transaction and balances.
- [ ] Same-China-day finance experience awards are exactly `7` for the first transaction and `2` for each subsequent transaction.
- [ ] Weekly-target list metrics, history metrics, and displayed remaining counts use the same target-slot formula.
- [ ] Normal completion and backfill share weekly capacity checks; a full week cannot gain a fourth completion or reward.
- [ ] Habit history and statistics do not invent dates from `last_completed_at`.
- [ ] Finance, debt, calendar, workbench, and history frontend date behavior is independent of the browser timezone.
- [ ] FEAT-01 malformed focus data, revision conflicts, request-id conflicts, stale requests, completion settlement, and retry states are covered.
- [ ] FEAT-02 lock fields, notes, leave/pause, backfill, history race, reward refresh failure, and cross-entry behavior are covered.
- [ ] Backend tests, frontend tests, version check, production build, patch check, and browser evidence are recorded.
- [ ] Android, CI, release artifacts, and live health status are reported separately and are not marked successful without external evidence.
