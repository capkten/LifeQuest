# LifeQuest 设计文档

## 概述

LifeQuest（生活冒险家）是一款个人日常生活管理软件，通过游戏化机制激励用户完成日常任务。用户通过完成待办任务获得金币和经验值，用于在商城兑换奖励和提升角色等级。

## 技术架构

### 技术栈

- **后端：** Python 3.11+ + FastAPI + SQLite (v1) + SQLAlchemy
- **Web前端：** Vue 3 + Vite + Element Plus + Pinia
- **移动端：** 响应式 Web App (PWA)
- **部署：** 云服务器部署

### 架构模式

采用领域驱动设计 (DDD) 架构，按业务领域划分模块：

- **用户领域** - 用户认证、资料、等级、金币
- **笔记领域** - 笔记本、文件夹、笔记、附件
- **待办领域** - 日常习惯、普通待办、目标、子任务
- **商城领域** - 商品、订单、兑换记录
- **背包领域** - 物品、装备、使用记录

### 数据访问层

使用 Repository 模式隔离业务逻辑和数据访问，支持未来数据库迁移：

- 接口层：定义各领域 Repository 接口
- 实现层：SQLite 实现 (v1)，未来可扩展 MySQL/PostgreSQL

## 数据模型

### 用户系统

#### 用户表 (users)
- id: UUID (主键)
- username: VARCHAR(50) (唯一)
- email: VARCHAR(100) (唯一)
- password_hash: VARCHAR(255)
- avatar: VARCHAR(255)
- level: INTEGER (默认1)
- experience: INTEGER (默认0)
- coins: INTEGER (默认0)
- title: VARCHAR(50) (称号)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

#### 成就表 (achievements)
- id: UUID (主键)
- name: VARCHAR(100)
- description: TEXT
- icon: VARCHAR(50)
- condition: JSON (达成条件)
- coin_reward: INTEGER
- exp_reward: INTEGER
- created_at: TIMESTAMP

### 笔记系统

#### 笔记本表 (notebooks)
- id: UUID (主键)
- user_id: UUID (外键)
- name: VARCHAR(100)
- description: TEXT
- icon: VARCHAR(50)
- created_at: TIMESTAMP

#### 文件夹表 (folders)
- id: UUID (主键)
- notebook_id: UUID (外键)
- parent_id: UUID (自引用，支持多级)
- name: VARCHAR(100)
- path: VARCHAR(500) (物化路径)
- created_at: TIMESTAMP

#### 笔记表 (notes)
- id: UUID (主键)
- folder_id: UUID (外键)
- title: VARCHAR(200)
- file_path: VARCHAR(500) (MD文件路径)
- summary: TEXT (摘要)
- tags: JSON
- is_pinned: BOOLEAN
- word_count: INTEGER
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

#### 附件表 (attachments)
- id: UUID (主键)
- note_id: UUID (外键)
- filename: VARCHAR(255)
- file_path: VARCHAR(500)
- file_type: VARCHAR(50)
- file_size: INTEGER
- created_at: TIMESTAMP

### 待办系统

#### 日常习惯表 (habits)
- id: UUID (主键)
- user_id: UUID (外键)
- name: VARCHAR(100)
- description: TEXT
- frequency: ENUM (每日/每周/每月)
- coin_reward: INTEGER
- exp_reward: INTEGER
- streak: INTEGER (连续天数)
- best_streak: INTEGER (最佳连续)
- created_at: TIMESTAMP

#### 普通待办表 (tasks)
- id: UUID (主键)
- user_id: UUID (外键)
- title: VARCHAR(200)
- description: TEXT
- difficulty: ENUM (简单/普通/困难/地狱)
- status: ENUM (待完成/进行中/已完成)
- coin_reward: INTEGER
- exp_reward: INTEGER
- due_date: TIMESTAMP
- reminder: TIMESTAMP
- completed_at: TIMESTAMP
- created_at: TIMESTAMP

#### 目标表 (goals)
- id: UUID (主键)
- user_id: UUID (外键)
- title: VARCHAR(200)
- description: TEXT
- deadline: TIMESTAMP
- progress: INTEGER (0-100)
- coin_reward: INTEGER
- exp_reward: INTEGER
- status: ENUM
- created_at: TIMESTAMP

#### 子任务表 (subtasks)
- id: UUID (主键)
- goal_id: UUID (外键)
- title: VARCHAR(200)
- status: ENUM
- order: INTEGER
- completed_at: TIMESTAMP

### 商城系统

#### 商品表 (shop_items)
- id: UUID (主键)
- user_id: UUID (外键)
- name: VARCHAR(100)
- description: TEXT
- price: INTEGER
- category: VARCHAR(50)
- stock: INTEGER (-1为无限)
- image: VARCHAR(255)
- is_active: BOOLEAN
- created_at: TIMESTAMP

#### 兑换记录表 (exchange_history)
- id: UUID (主键)
- user_id: UUID (外键)
- item_id: UUID (外键)
- item_name: VARCHAR(100)
- price_paid: INTEGER
- quantity: INTEGER
- status: ENUM (已兑换/已使用/已过期)
- exchanged_at: TIMESTAMP
- used_at: TIMESTAMP

### 背包系统

#### 背包物品表 (backpack_items)
- id: UUID (主键)
- user_id: UUID (外键)
- item_type: ENUM (奖励券/成就徽章/虚拟物品)
- source_id: UUID (来源ID)
- name: VARCHAR(100)
- description: TEXT
- icon: VARCHAR(50)
- status: ENUM (未使用/已使用/已装备)
- obtained_at: TIMESTAMP
- used_at: TIMESTAMP

#### 使用记录表 (usage_history)
- id: UUID (主键)
- user_id: UUID (外键)
- item_id: UUID (外键)
- item_name: VARCHAR(100)
- action: ENUM (使用/装备/丢弃)
- used_at: TIMESTAMP
- notes: TEXT

## API 设计

### 用户模块

- POST /api/auth/register - 注册
- POST /api/auth/login - 登录
- GET /api/users/me - 获取用户信息
- PUT /api/users/me - 更新用户信息
- POST /api/users/me/avatar - 上传头像

### 笔记模块

- GET /api/notes - 获取笔记列表
- POST /api/notes - 创建笔记
- GET /api/notes/:id - 获取笔记详情
- PUT /api/notes/:id - 更新笔记
- DELETE /api/notes/:id - 删除笔记

### 待办模块

- GET /api/todos - 获取待办列表
- POST /api/todos - 创建待办
- PUT /api/todos/:id - 更新待办
- POST /api/todos/:id/complete - 完成待办
- DELETE /api/todos/:id - 删除待办

### 商城模块

- GET /api/shop/items - 获取商品列表
- POST /api/shop/items - 添加商品
- POST /api/shop/items/:id/purchase - 兑换商品
- GET /api/shop/orders - 兑换历史

### 背包模块

- GET /api/backpack/items - 获取背包物品
- POST /api/backpack/items/:id/use - 使用物品
- DELETE /api/backpack/items/:id - 丢弃物品
- GET /api/backpack/items/:id - 物品详情

## 游戏机制

### 等级系统

采用指数增长经验值机制：

- 公式：每级经验 = 基础值 × (1.5 ^ (等级-1))
- Lv1: 100 经验
- Lv2: 300 经验
- Lv3: 600 经验
- Lv4: 1000 经验
- Lv5: 1500 经验

### 奖励系统

采用动态难度奖励机制：

- **任务类型基础奖励：**
  - 日常待办：5-15 金币 + 10-30 经验
  - 支线任务：20-50 金币 + 50-100 经验
  - 主线任务：50-150 金币 + 100-300 经验
  - 成就：100-500 金币 + 200-1000 经验

- **难度系数调整：**
  - 简单：×0.8
  - 普通：×1.0
  - 困难：×1.5
  - 地狱：×2.0

- **额外加成：**
  - 连续完成：连续7天完成日常待办，奖励 ×1.2
  - 提前完成：在截止日期前完成，奖励 ×1.1
  - 完美主义：任务完成质量高，额外 +20% 经验

## UI 设计

### 设计系统

- **风格：** Flat Design (扁平设计)
- **配色方案：** 笔记暖墨
  - Primary: #78716C (暖灰)
  - Secondary: #A8A29E (浅暖灰)
  - Accent: #D97706 (琥珀)
  - Background: #FFFBEB (奶油白)
  - Foreground: #78716C (暖灰)

- **字体：** Plus Jakarta Sans
- **图标：** SVG 图标 (Lucide)

### 界面布局

- **侧边栏：** 用户信息、导航菜单、经验值进度
- **主内容区：** 欢迎信息、今日待办、进行中的目标

### 响应式设计

- 移动端优先设计
- 支持 375px、768px、1024px、1440px 断点
- PWA 支持，可添加到主屏幕

## 部署方案

- **后端：** 云服务器部署 (如阿里云、腾讯云)
- **前端：** 静态资源部署到 CDN
- **数据库：** SQLite (v1)，未来可迁移到 MySQL/PostgreSQL
- **域名：** 配置域名和 SSL 证书

## 未来扩展

- 支持更多数据库后端
- 添加推送通知功能
- 支持离线访问
- 添加社交功能（好友、排行榜）
- 支持多语言国际化
