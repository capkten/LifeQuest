# LifeQuest API 文档

基础地址: `http://{服务器IP}:8000`

认证方式: Bearer Token (JWT)，通过请求头 `Authorization: Bearer {access_token}` 传递。

## 服务健康检查

### GET /api/health

无需认证。数据库可用时返回 `{"status":"ok"}`；数据库探针失败时返回 `503`。

---

## 认证 (Auth)

### POST /api/auth/register
注册新用户。

**请求体 (JSON):**
```json
{
  "username": "用户名",
  "email": "user@example.com",
  "password": "密码"
}
```

**响应:** `UserResponse`
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "avatar": "string|null",
  "level": 1,
  "experience": 0,
  "coins": 0,
  "total_coins_earned": 0,
  "title": "string|null",
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

---

### POST /api/auth/login
用户登录，获取令牌。

**请求体 (form-urlencoded):**
```
username=用户名&password=密码
```

**响应:** `Token`
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer"
}
```

---

### POST /api/auth/refresh
刷新访问令牌。

**请求体 (JSON):**
```json
{
  "refresh_token": "string"
}
```

**响应:** `Token`（同登录）

---

## 用户 (Users)

> 以下接口均需认证。

### GET /api/users/me
获取当前用户信息。

**响应:** `UserResponse`

---

### PUT /api/users/me
更新当前用户信息。

**请求体 (JSON):**
```json
{
  "username": "新用户名（可选）",
  "email": "新邮箱（可选）",
  "avatar": "头像地址（可选）"
}
```

**响应:** `UserResponse`

---

### POST /api/users/me/avatar
上传头像。

**请求体 (multipart/form-data):**
- `file`: 图片文件（支持 jpg/jpeg/png/gif/webp，最大 5MB）

**响应:**
```json
{
  "avatar": "/uploads/avatars/{user_id}.{ext}"
}
```

---

## 待办 (Todos)

> 以下接口均需认证。

### GET /api/todos/daily
获取今日待办汇总（包含任务、习惯、目标）。

---

### 习惯 (Habits)

#### POST /api/todos/habits
创建习惯。

**请求体:**
```json
{
  "title": "习惯名称",
  "description": "描述（可选）",
  "difficulty": "easy|medium|hard（默认 medium）",
  "frequency": "daily|weekly|monthly（默认 daily）",
  "coins_reward": 10,
  "exp_reward": 5
}
```

**响应:** `HabitResponse`
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "string",
  "description": "string|null",
  "difficulty": "medium",
  "frequency": "daily",
  "coins_reward": 10,
  "exp_reward": 5,
  "is_active": true,
  "streak": 0,
  "best_streak": 0,
  "last_completed_at": null,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

#### GET /api/todos/habits
获取所有习惯列表。

#### GET /api/todos/habits/{habit_id}
获取单个习惯详情。

#### PUT /api/todos/habits/{habit_id}
更新习惯，所有字段可选。

#### DELETE /api/todos/habits/{habit_id}
删除习惯。

#### POST /api/todos/habits/{habit_id}/complete
完成今日习惯打卡。触发连续天数更新和金币/经验奖励。

---

### 任务 (Tasks)

#### POST /api/todos/tasks
创建任务。

**请求体:**
```json
{
  "title": "任务名称",
  "description": "描述（可选）",
  "difficulty": "easy|medium|hard（默认 medium）",
  "coins_reward": 10,
  "exp_reward": 5,
  "deadline": "2026-01-01T00:00:00（可选）",
  "project_id": "uuid（可选，关联项目）",
  "phase_id": "uuid（可选）",
  "milestone_id": "uuid（可选）",
  "start_date": "2026-01-01T00:00:00（可选）",
  "priority": "low|medium|high（默认 medium）"
}
```

**响应:** `TaskResponse`
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "string",
  "description": "string|null",
  "difficulty": "medium",
  "status": "pending",
  "coins_reward": 10,
  "exp_reward": 5,
  "deadline": null,
  "completed_at": null,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00",
  "project_id": null,
  "phase_id": null,
  "milestone_id": null,
  "start_date": null,
  "priority": "medium",
  "sort_order": 0,
  "project_name": null,
  "project_color": null
}
```

#### GET /api/todos/tasks
获取所有任务。可选参数: `project_id`（按项目筛选）。

#### GET /api/todos/tasks/{task_id}
获取单个任务详情。

#### PUT /api/todos/tasks/{task_id}
更新任务，所有字段可选。可修改 `status` 为 `in_progress|completed`。

#### DELETE /api/todos/tasks/{task_id}
删除任务。

#### POST /api/todos/tasks/{task_id}/complete
完成任务，触发金币/经验奖励。

---

### 目标 (Goals)

#### POST /api/todos/goals
创建目标。

**请求体:**
```json
{
  "title": "目标名称",
  "description": "描述（可选）",
  "difficulty": "easy|medium|hard（默认 medium）",
  "coins_reward": 50,
  "exp_reward": 25,
  "deadline": "2026-01-01T00:00:00（可选）"
}
```

**响应:** `GoalResponse`
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "string",
  "description": "string|null",
  "difficulty": "medium",
  "status": "in_progress",
  "coins_reward": 50,
  "exp_reward": 25,
  "progress": 0.0,
  "deadline": null,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

#### GET /api/todos/goals
获取所有目标。

#### GET /api/todos/goals/{goal_id}
获取单个目标详情。

#### PUT /api/todos/goals/{goal_id}
更新目标，所有字段可选。`progress` 为浮点数（0-100）。

#### DELETE /api/todos/goals/{goal_id}
删除目标。

#### POST /api/todos/goals/{goal_id}/complete
完成目标，触发金币/经验奖励。

---

### 子任务 (Subtasks)

#### POST /api/todos/subtasks
创建子任务。

**请求体:**
```json
{
  "task_id": "uuid",
  "title": "子任务名称"
}
```

**响应:**
```json
{
  "id": "uuid",
  "task_id": "uuid",
  "title": "string",
  "is_completed": false,
  "created_at": "2026-01-01T00:00:00"
}
```

#### GET /api/todos/subtasks/task/{task_id}
获取指定任务的所有子任务。

#### GET /api/todos/subtasks/{subtask_id}
获取单个子任务详情。

#### PUT /api/todos/subtasks/{subtask_id}
更新子任务。字段: `title`（可选）、`is_completed`（可选，布尔值）。

#### DELETE /api/todos/subtasks/{subtask_id}
删除子任务。

---

## 笔记 (Notes)

> 以下接口均需认证。

### 笔记本 (Notebooks)

#### POST /api/notes/notebooks
创建笔记本。

**请求体:**
```json
{
  "name": "笔记本名称",
  "description": "描述（可选）",
  "icon": "图标（可选）"
}
```

**响应:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "string",
  "description": "string|null",
  "icon": "string|null",
  "created_at": "2026-01-01T00:00:00"
}
```

#### GET /api/notes/notebooks
获取所有笔记本列表。

#### GET /api/notes/notebooks/{notebook_id}
获取单个笔记本详情。

#### PUT /api/notes/notebooks/{notebook_id}
更新笔记本。字段: `name`、`description`、`icon`（均可选）。

#### DELETE /api/notes/notebooks/{notebook_id}
删除笔记本及其所有内容。

---

### 目录树 / 文件夹 / 笔记

#### GET /api/notes/notebooks/{notebook_id}/tree
获取笔记本的完整递归目录树。

**响应:**
```json
[
  {
    "id": "uuid",
    "name": "文件夹名称",
    "type": "folder",
    "parent_id": null,
    "children": [
      {
        "id": "uuid",
        "name": "笔记标题",
        "type": "note",
        "parent_id": "uuid",
        "children": []
      }
    ]
  }
]
```

#### GET /api/notes/notebooks/{notebook_id}/children
获取直接子节点。可选参数: `parent_id`（省略则返回根级内容）。

#### POST /api/notes/notebooks/{notebook_id}/folders
创建文件夹。名称冲突返回 409。

**请求体:**
```json
{
  "name": "文件夹名称",
  "parent_id": "uuid（可选，父文件夹）"
}
```

#### POST /api/notes/notebooks/{notebook_id}/notes
创建笔记。名称冲突返回 409。

**请求体:**
```json
{
  "title": "笔记标题",
  "content": "内容（可选）",
  "summary": "摘要（可选）",
  "tags": "标签（可选）",
  "parent_id": "uuid（可选，父文件夹）"
}
```

---

### 节点操作

#### PATCH /api/notes/nodes/{node_id}
重命名或移动节点。

**请求体:**
```json
{
  "name": "新名称（可选）",
  "parent_id": "uuid（可选，移动到新位置）"
}
```

#### DELETE /api/notes/nodes/{node_id}
删除节点及其所有子节点。

---

### 笔记内容

#### GET /api/notes/{note_id}
获取笔记完整内容。

**响应:**
```json
{
  "id": "uuid",
  "notebook_id": "uuid",
  "parent_id": "uuid|null",
  "type": "note",
  "name": "string",
  "path": "/笔记本/笔记",
  "content": "完整 Markdown 内容",
  "summary": "string|null",
  "tags": "string|null",
  "is_pinned": false,
  "word_count": 100,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

#### PUT /api/notes/{note_id}
更新笔记内容/元数据。

**请求体:**
```json
{
  "title": "新标题（可选）",
  "content": "新内容（可选）",
  "summary": "新摘要（可选）",
  "tags": "新标签（可选）",
  "is_pinned": true
}
```

#### GET /api/notes/search?query=关键词
按关键词搜索笔记。

#### POST /api/notes/upload-image
上传笔记中使用的图片。

**请求体 (multipart/form-data):**
- `file`: 图片文件（支持 jpg/jpeg/png/gif/webp，最大 10MB）

**响应:**
```json
{
  "url": "/uploads/notes/{filename}"
}
```

---

## 商店 (Shop)

> 以下接口均需认证。

### 商品

#### POST /api/shop/items
创建商品。

**请求体:**
```json
{
  "name": "商品名称",
  "description": "描述（可选）",
  "icon": "图标（可选）",
  "category": "分类（可选）",
  "coin_price": 0,
  "stock": -1
}
```

**响应:**
```json
{
  "id": "uuid",
  "created_by": "uuid",
  "name": "string",
  "description": "string|null",
  "icon": "string|null",
  "category": "string|null",
  "coin_price": 0,
  "stock": -1,
  "is_active": true,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

#### GET /api/shop/items
获取商品列表。参数: `skip`（默认 0）、`limit`（默认 100）。

#### GET /api/shop/items/{item_id}
获取单个商品详情。

#### PUT /api/shop/items/{item_id}
更新商品（仅创建者）。所有字段可选。

#### DELETE /api/shop/items/{item_id}
删除商品（仅创建者）。

---

### 兑换

#### POST /api/shop/exchange
使用金币兑换商品。

**请求体:**
```json
{
  "item_id": "uuid",
  "quantity": 1
}
```

**响应:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "item_id": "uuid",
  "quantity": 1,
  "total_cost": 100,
  "status": "completed",
  "created_at": "2026-01-01T00:00:00"
}
```

#### GET /api/shop/exchange/history
获取兑换历史记录。

#### GET /api/shop/exchange/{exchange_id}
获取单条兑换记录。

#### POST /api/shop/exchange/{exchange_id}/refund
退还兑换。

---

## 背包 (Backpack)

> 以下接口均需认证。

#### GET /api/backpack/items
获取背包物品。可选参数: `status`（如 `active`、`used`）。

**响应:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "shop_item_id": "uuid",
    "item_type": "consumable|equippable",
    "status": "active|used|discarded",
    "quantity": 1,
    "is_equipped": false,
    "obtained_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00"
  }
]
```

#### POST /api/backpack/items/{item_id}/use
使用消耗品。参数: `quantity`（默认 1）。

#### POST /api/backpack/items/{item_id}/equip
装备可穿戴物品。

#### POST /api/backpack/items/{item_id}/discard
丢弃物品。参数: `quantity`（默认 1）。

#### GET /api/backpack/history
获取物品使用历史。

---

## 成就 (Achievements)

#### GET /api/achievements
获取所有成就列表。**无需认证。**

**响应:**
```json
[
  {
    "id": "uuid",
    "name": "成就名称",
    "description": "成就描述",
    "icon": "图标",
    "condition_type": "条件类型",
    "condition_value": 1,
    "coin_reward": 0,
    "exp_reward": 0
  }
]
```

#### GET /api/achievements/me
获取当前用户已解锁的成就。（需认证）

**响应:**
```json
[
  {
    "id": "uuid",
    "achievement_id": "uuid",
    "unlocked_at": "2026-01-01T00:00:00",
    "achievement": { ... }
  }
]
```

---

## 签到 (Check-in)

> 以下接口均需认证。

#### POST /api/checkin
每日签到。根据连续签到天数发放金币/经验奖励。

**响应:**
```json
{
  "id": 1,
  "user_id": "uuid",
  "checkin_date": "2026-01-01",
  "streak": 5,
  "created_at": "2026-01-01T00:00:00"
}
```

#### GET /api/checkin/status
获取今日签到状态。

**响应:**
```json
{
  "checked_in": false,
  "streak": 4,
  "reward_coins": 10,
  "reward_exp": 5
}
```

---

## 称号 (Titles)

> 以下接口均需认证。

#### GET /api/titles
获取所有可用称号。

**响应:**
```json
[
  {
    "id": 1,
    "name": "称号名称",
    "description": "称号描述",
    "unlock_condition_type": "解锁条件类型",
    "unlock_condition_value": 1
  }
]
```

#### GET /api/titles/me
获取当前用户已解锁的称号。

#### PUT /api/titles/activate
激活/佩戴称号。

**请求体:**
```json
{
  "title_id": 1
}
```

---

## 金币 (Coins)

> 以下接口均需认证。

#### GET /api/coins/history
获取金币交易记录。

**查询参数:**
- `coin_type`: `"earn"` 或 `"spend"`（可选）
- `source`: `"task"`、`"habit"`、`"goal"`、`"checkin"`、`"shop"`、`"achievement"`（可选）
- `start_date`: 起始时间（可选）
- `end_date`: 结束时间（可选）
- `skip`: 偏移量（默认 0）
- `limit`: 每页条数（1-200，默认 50）

**响应:**
```json
{
  "transactions": [
    {
      "id": 1,
      "user_id": "uuid",
      "amount": 10,
      "type": "earn",
      "source": "task",
      "source_id": "uuid",
      "description": "string",
      "created_at": "2026-01-01T00:00:00"
    }
  ],
  "total_earned": 500,
  "total_spent": 200,
  "count": 30
}
```

#### GET /api/coins/totals
获取金币收支汇总。

---

## 日历 (Calendar)

> 以下接口均需认证。

#### GET /api/calendar/events
获取日期范围内的所有事件。

**查询参数:**
- `start`: 起始日期（必填，格式 `YYYY-MM-DD`）
- `end`: 结束日期（必填，格式 `YYYY-MM-DD`）

#### GET /api/calendar/day/{date}
获取指定日期的详细信息（格式 `YYYY-MM-DD`）。

---

## 统计 (Stats)

> 以下接口均需认证。

#### GET /api/stats/overview
获取总体统计概览。

#### GET /api/stats/tasks
获取任务完成趋势。参数: `period` = `week` | `month` | `year`（默认 `week`）。

#### GET /api/stats/habits
获取习惯打卡统计。参数: `period` = `week` | `month`（默认 `week`）。

#### GET /api/stats/coins
获取金币收支趋势。参数: `period` = `week` | `month` | `year`（默认 `month`）。

#### GET /api/stats/level
获取等级和经验值进度。

---

## 财务 (Finance)

> 以下接口均需认证。

### 仪表盘

#### GET /api/finance/dashboard
获取财务仪表盘摘要。

---

### 账户

#### GET /api/finance/accounts
获取所有账户列表。

#### POST /api/finance/accounts
创建账户。

**请求体:**
```json
{
  "name": "账户名称",
  "type": "cash|bank|credit|investment|other",
  "icon": "图标",
  "balance": 0.0,
  "credit_limit": 0.0,
  "billing_day": 1,
  "repayment_day": 15,
  "interest_rate": 0.0,
  "currency": "CNY",
  "sort_order": 0
}
```

**响应:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "string",
  "type": "cash",
  "icon": "string",
  "balance": 0.0,
  "credit_limit": null,
  "billing_day": null,
  "repayment_day": null,
  "interest_rate": null,
  "currency": "CNY",
  "is_active": true,
  "sort_order": 0,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

#### PUT /api/finance/accounts/{account_id}
更新账户，所有字段可选。

#### DELETE /api/finance/accounts/{account_id}
删除账户。

#### POST /api/finance/accounts/transfer
账户间转账。

**请求体:**
```json
{
  "from_id": "uuid",
  "to_id": "uuid",
  "amount": 100.0,
  "description": "转账说明"
}
```

---

### 分类

#### GET /api/finance/categories
获取所有分类。

#### POST /api/finance/categories
创建分类。

**请求体:**
```json
{
  "name": "分类名称",
  "type": "income|expense",
  "icon": "图标",
  "parent_id": "uuid（可选，父分类）",
  "sort_order": 0
}
```

#### DELETE /api/finance/categories/{category_id}
删除分类。

---

### 交易记录

#### GET /api/finance/transactions
获取交易记录（支持筛选）。

**查询参数:** `account_id`、`category_id`、`type`（income/expense）、`start_date`、`end_date`、`skip`（默认 0）、`limit`（默认 50）。均为可选。

#### POST /api/finance/transactions
创建交易记录。

**请求体:**
```json
{
  "account_id": "uuid",
  "category_id": "uuid（可选）",
  "type": "income|expense",
  "amount": 100.0,
  "description": "交易描述",
  "date": "2026-01-01",
  "to_account_id": "uuid（可选，转账目标账户）"
}
```

#### PUT /api/finance/transactions/{transaction_id}
更新交易记录，所有字段可选。

#### DELETE /api/finance/transactions/{transaction_id}
删除交易记录。

---

### 预算

#### GET /api/finance/budgets
获取所有预算。

#### POST /api/finance/budgets
创建预算。

**请求体:**
```json
{
  "category_id": "uuid（可选）",
  "amount": 1000.0,
  "period": "weekly|monthly|yearly",
  "start_date": "2026-01-01（可选）"
}
```

#### PUT /api/finance/budgets/{budget_id}
更新预算，所有字段可选。

#### DELETE /api/finance/budgets/{budget_id}
删除预算。

---

### 周期性交易

#### GET /api/finance/recurring
获取所有周期性交易。

#### POST /api/finance/recurring
创建周期性交易。

**请求体:**
```json
{
  "account_id": "uuid",
  "category_id": "uuid（可选）",
  "type": "income|expense",
  "amount": 100.0,
  "description": "交易描述",
  "frequency": "daily|weekly|monthly|yearly",
  "next_date": "2026-01-01"
}
```

#### POST /api/finance/recurring/{recurring_id}/trigger
手动触发一次周期性交易。

#### DELETE /api/finance/recurring/{recurring_id}
删除周期性交易。

---

### 借贷

#### GET /api/finance/debts
获取借贷列表。可选参数: `status`（如 `active`、`settled`）。

#### POST /api/finance/debts
创建借贷记录。

**请求体:**
```json
{
  "creditor": "债权人/债务人",
  "type": "lend|borrow",
  "amount": 1000.0,
  "remaining": 1000.0,
  "interest_rate": 0.0,
  "description": "描述",
  "due_date": "2026-06-01（可选）"
}
```

#### PUT /api/finance/debts/{debt_id}
更新借贷记录，所有字段可选。`status` 可设为 `active`、`settled`、`overdue`。

#### DELETE /api/finance/debts/{debt_id}
删除借贷记录。

#### POST /api/finance/debts/{debt_id}/payments
记录还款。

**请求体:**
```json
{
  "amount": 100.0,
  "description": "还款说明",
  "date": "2026-01-01"
}
```

---

## 项目 (Projects)

> 以下接口均需认证。

### 项目管理

#### GET /api/projects
获取项目列表。可选参数: `status`（如 `active`、`completed`）。

**响应:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "name": "项目名称",
    "description": "string|null",
    "color": "#0EA5E9",
    "icon": "folder",
    "status": "active",
    "start_date": null,
    "end_date": null,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00",
    "total_tasks": 10,
    "completed_tasks": 3,
    "progress": 30.0
  }
]
```

#### POST /api/projects
创建项目。

**请求体:**
```json
{
  "name": "项目名称",
  "description": "描述（可选）",
  "color": "#0EA5E9",
  "icon": "folder",
  "start_date": "2026-01-01（可选）",
  "end_date": "2026-12-31（可选）"
}
```

#### GET /api/projects/{project_id}
获取项目详情（含阶段和里程碑）。

#### PUT /api/projects/{project_id}
更新项目，所有字段可选。

#### DELETE /api/projects/{project_id}
删除项目。

#### POST /api/projects/{project_id}/complete
标记项目为已完成。

---

### 阶段 (Phases)

#### POST /api/projects/{project_id}/phases
创建阶段。

**请求体:**
```json
{
  "name": "阶段名称",
  "description": "描述（可选）",
  "sort_order": 0
}
```

#### PUT /api/projects/phases/{phase_id}
更新阶段。字段: `name`、`description`、`status`、`sort_order`（均可选）。

#### DELETE /api/projects/phases/{phase_id}
删除阶段。

---

### 里程碑 (Milestones)

#### POST /api/projects/{project_id}/milestones
创建里程碑。

**请求体:**
```json
{
  "name": "里程碑名称",
  "description": "描述（可选）",
  "due_date": "2026-06-01（可选）",
  "sort_order": 0
}
```

#### PUT /api/projects/milestones/{milestone_id}
更新里程碑。字段: `name`、`description`、`due_date`、`sort_order`（均可选）。

#### DELETE /api/projects/milestones/{milestone_id}
删除里程碑。

#### POST /api/projects/milestones/{milestone_id}/reach
标记里程碑为已达成。

---

### 项目任务

#### POST /api/projects/{project_id}/tasks
在项目下创建任务。

#### GET /api/projects/{project_id}/tasks
获取项目下的任务列表。可选参数: `phase_id`、`milestone_id`。

#### PUT /api/projects/tasks/{task_id}/move
移动任务到其他项目/阶段/里程碑。

**请求体:**
```json
{
  "project_id": "uuid（可选）",
  "phase_id": "uuid（可选）",
  "milestone_id": "uuid（可选）"
}
```

---

## 枚举值参考

| 枚举 | 可选值 |
|------|--------|
| Difficulty（难度） | `easy`（简单）、`medium`（中等）、`hard`（困难） |
| Frequency（频率） | `daily`（每日）、`weekly`（每周）、`monthly`（每月） |
| TaskStatus（任务状态） | `pending`（待办）、`in_progress`（进行中）、`completed`（已完成） |
| GoalStatus（目标状态） | `in_progress`（进行中）、`completed`（已完成） |
| ExchangeStatus（兑换状态） | `completed`（已完成）、`refunded`（已退款） |
| ItemType（物品类型） | `consumable`（消耗品）、`equippable`（装备） |
| ItemStatus（物品状态） | `active`（可用）、`used`（已使用）、`discarded`（已丢弃） |
| UsageAction（使用动作） | `use`（使用）、`equip`（装备）、`discard`（丢弃） |
| AccountType（账户类型） | `cash`（现金）、`bank`（银行）、`credit`（信用卡）、`investment`（投资）、`other`（其他） |
| CategoryType（分类类型） | `income`（收入）、`expense`（支出） |
| FinanceTransactionType | `income`（收入）、`expense`（支出） |
| BudgetPeriod（预算周期） | `weekly`（每周）、`monthly`（每月）、`yearly`（每年） |
| RecurFrequency（重复频率） | `daily`（每天）、`weekly`（每周）、`monthly`（每月）、`yearly`（每年） |
| DebtType（借贷类型） | `lend`（借出）、`borrow`（借入） |
| DebtStatus（借贷状态） | `active`（进行中）、`settled`（已结清）、`overdue`（已逾期） |
