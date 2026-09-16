# 最终复核修复报告

状态：`DONE_WITH_CONCERNS`
修复基线：`ab929fa47a61eb9800fa6930d540171d76b4efd6`
修复提交：`a1c9003a7375556fa108b5ea5102319fa6854953` (`fix: close final LifeQuest review findings`)

## Finding 1：金币历史使用金额 magnitude

`CoinTransactionRepository.get_totals()` 继续按交易 `type` 分组，但现在累加 `abs(amount)`。历史 API 为返回行创建副本并规范为非负 magnitude，保留 `type`；前端仍由 `earn`/`spend` 类型决定符号。回归测试确认数据库里的旧负数没有被改写。

### RED / GREEN

新增真实 `/api/coins/history` 回归测试后，在旧实现运行：

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_defect_closure.py::test_coin_history_totals_use_magnitude_for_signed_legacy_amounts
FAILED: actual totals were total_earned=12 and total_spent=8; expected 22 and 14.
1 failed, 350 warnings in 0.92s
```

仅将聚合改为 magnitude 后，同一测试继续运行并暴露历史负数无法通过行响应模型的非负校验：

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_defect_closure.py::test_coin_history_totals_use_magnitude_for_signed_legacy_amounts
FAILED: ResponseValidationError for legacy amounts -3 and -5 (`amount >= 0`).
1 failed, 351 warnings in 0.99s
```

随后在返回副本上规范行金额，没有改写持久化记录。最终 RED/GREEN 测试结果：

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_defect_closure.py::test_coin_history_totals_use_magnitude_for_signed_legacy_amounts
1 passed, 351 warnings in 0.81s
```

该测试断言两种类型的汇总 magnitude、历史行的类型与 magnitude，以及数据库中的原始 `-5`、`-3` 仍保持不变。

金币相关聚焦测试：

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q tests/test_defect_closure.py tests/test_regressions.py tests/test_content_localization.py -k 'coin'
8 passed, 71 deselected, 364 warnings in 3.42s
```

完整后端测试：

```text
/tmp/lifequest-task13-env.taX0sH/venv/bin/pytest -q
603 passed, 1462 warnings in 179.02s (0:02:59)
```

测试环境为 brief 指定的临时 Python 3.14 虚拟环境。全量输出中的弃用/兼容性警告包括现有 FastAPI 生命周期、`python-jose` UTC API、Pydantic 字段 metadata 和 sqlite3 日期适配器警告；测试结果没有失败。

## Finding 2：严格浏览器路线合同

已将 `/calendar`、`/stats` 加入 `.harness/strict-playwright-runner.mjs` 默认路线、`.harness/contracts/task-12-browser.json` 的 `requiredRoutes`，并同步 `docs/superpowers/reports/2026-09-15-lifequest-defect-closure-verification.md` 的路线清单。

检查命令与结果：

```text
node --check .harness/strict-playwright-runner.mjs
exit 0

node --input-type=module -e "import fs from 'node:fs'; const source = fs.readFileSync('.harness/strict-playwright-runner.mjs', 'utf8'); const block = source.match(/const DEFAULT_ROUTES = (\\[[\\s\\S]*?\\n\\])/); if (!block) throw new Error('DEFAULT_ROUTES not found'); const routes = [...block[1].matchAll(/'([^']+)'/g)].map(([, route]) => route); const contract = JSON.parse(fs.readFileSync('.harness/contracts/task-12-browser.json', 'utf8')); if (JSON.stringify(routes) !== JSON.stringify(contract.requiredRoutes)) throw new Error(JSON.stringify({ routes, requiredRoutes: contract.requiredRoutes })); console.log(JSON.stringify({ routeCount: routes.length, requiredRoutes: contract.requiredRoutes }));"
{"routeCount":11,"requiredRoutes":["/","/todos","/coins/history","/finance","/finance/budgets","/finance/debts","/backpack/history","/notes","/projects","/calendar","/stats"]}
exit 0
```

## 未完成门禁与约束

- 严格浏览器验收未执行，状态仍为 blocked。Playwright 期望的 Chromium 路径 `/home/capkin/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome` 不存在，`.harness/` 内没有认证 storage-state fixture；不得将浏览器门禁记为通过。
- 没有运行 strict runner；它还会发起 live HTTP 探测。本轮未执行生产写入、部署、发布、push 或 merge。
- 没有改写金币历史流水，没有增加数据库约束、性能优化或 UI 重构。
- 控制器的 `final-fix-report.md` 和 `progress.md` 中文未提交修改保持原样，未暂存。
