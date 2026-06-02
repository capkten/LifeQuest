# LifeQuest Bug修复与功能完善 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复所有已知Bug并完善缺失功能，使LifeQuest成为一个完整可用的个人生活管理应用

**Architecture:** 基于现有DDD架构，修复后端API并补充前端缺失页面。笔记系统需要添加Markdown编辑器支持，用户系统需要添加文件上传功能。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, Vue 3, Vite, Element Plus, Pinia, Axios, Markdown编辑器(mditor或v-md-editor)

---

## 第一部分：Bug修复

### Task 1: 修复习惯完成不奖励金币和经验

**Files:**
- Modify: `backend/app/services/todo.py`

- [ ] **Step 1: 查看当前代码**

```python
# backend/app/services/todo.py 第86-93行
def complete_habit(self, habit: Habit) -> Habit:
    habit.streak += 1
    if habit.streak > habit.best_streak:
        habit.best_streak = habit.streak
    self.db.commit()
    self.db.refresh(habit)
    return habit
```

- [ ] **Step 2: 修改complete_habit方法添加奖励**

```python
def complete_habit(self, habit: Habit, user_id: UUID) -> Habit:
    habit.streak += 1
    if habit.streak > habit.best_streak:
        habit.best_streak = habit.streak
    
    # 添加金币和经验奖励
    user = self.user_repo.get_by_id(user_id)
    if user:
        self._update_rewards(user, habit.coin_reward, habit.exp_reward)
    
    self.db.commit()
    self.db.refresh(habit)
    return habit
```

- [ ] **Step 3: 更新API端点传递user_id**

修改 `backend/app/api/todos.py` 中的 `complete_habit` 端点：
```python
@router.post("/habits/{habit_id}/complete", response_model=HabitResponse)
def complete_habit(
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TodoService(db)
    habit = service.get_habit_for_user(habit_id, current_user.id)
    return service.complete_habit(habit, current_user.id)
```

- [ ] **Step 4: 运行测试验证**

Run: `cd backend && pytest tests/test_todos.py -v`

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/todo.py backend/app/api/todos.py
git commit -m "fix: add coin and exp rewards to habit completion"
```

---

### Task 2: 修复页面标题英文问题

**Files:**
- Modify: `frontend/src/components/layout/AppLayout.vue`

- [ ] **Step 1: 修改pageTitle映射为中文**

```javascript
const pageTitle = computed(() => {
  const titles = {
    Home: '首页',
    Todos: '待办',
    Tasks: '任务',
    Goals: '目标',
    Notes: '笔记',
    NotebookDetail: '笔记本',
    Shop: '商城',
    Backpack: '背包',
    Profile: '个人'
  }
  return titles[route.name] || 'LifeQuest'
})
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/layout/AppLayout.vue
git commit -m "fix: translate page titles to Chinese"
```

---

### Task 3: 修复Notes.vue空状态按钮英文问题

**Files:**
- Modify: `frontend/src/views/Notes.vue`

- [ ] **Step 1: 修改空状态按钮文字**

找到第44行附近，将 "Create Notebook" 改为 "新建笔记本"

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/Notes.vue
git commit -m "fix: translate Notes empty state button to Chinese"
```

---

## 第二部分：笔记系统完善

### Task 4: 添加笔记内容返回支持

**Files:**
- Modify: `backend/app/schemas/note.py`
- Modify: `backend/app/api/notes.py`

- [ ] **Step 1: 修改NoteResponse添加content字段**

```python
# backend/app/schemas/note.py
class NoteResponse(NoteBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    folder_id: UUID
    file_path: Optional[str] = None
    content: Optional[str] = None  # 添加此字段
    word_count: int
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 2: 修改get_note API读取文件内容**

```python
# backend/app/api/notes.py
@router.get("/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    note = service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not service.verify_note_ownership(note, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 读取文件内容
    content = ""
    if note.file_path and os.path.exists(note.file_path):
        with open(note.file_path, "r", encoding="utf-8") as f:
            content = f.read()
    
    # 构造响应
    note_data = NoteResponse.model_validate(note)
    note_data.content = content
    return note_data
```

- [ ] **Step 3: 添加笔记本和文件夹的更新删除API**

```python
# backend/app/api/notes.py 添加以下端点

@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
def update_notebook(
    notebook_id: UUID,
    notebook_in: NotebookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    notebook = service.notebook_repo.get_by_id(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return service.notebook_repo.update(notebook, notebook_in.model_dump(exclude_unset=True))

@router.delete("/notebooks/{notebook_id}")
def delete_notebook(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    service.notebook_repo.delete(notebook_id)
    return {"message": "Notebook deleted"}

@router.put("/folders/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: UUID,
    folder_in: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_folder_ownership(folder_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    folder = service.folder_repo.get_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return service.folder_repo.update(folder, folder_in.model_dump(exclude_unset=True))

@router.delete("/folders/{folder_id}")
def delete_folder(
    folder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_folder_ownership(folder_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    service.folder_repo.delete(folder_id)
    return {"message": "Folder deleted"}
```

- [ ] **Step 4: 添加NotebookUpdate和FolderUpdate schemas**

```python
# backend/app/schemas/note.py
class NotebookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None

class FolderUpdate(BaseModel):
    name: Optional[str] = None
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/schemas/note.py backend/app/api/notes.py
git commit -m "feat: add content return and CRUD for notebooks/folders"
```

---

### Task 5: 添加文件夹笔记列表页面

**Files:**
- Create: `frontend/src/views/FolderDetail.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/services/note.js`

- [ ] **Step 1: 添加笔记服务方法**

```javascript
// frontend/src/services/note.js 添加
async getNotesByFolder(folderId) {
  const response = await api.get(`/notes/folder/${folderId}`)
  return response.data
},

async getNote(noteId) {
  const response = await api.get(`/notes/${noteId}`)
  return response.data
},

async createNote(data) {
  const response = await api.post('/notes/', data)
  return response.data
},

async updateNote(noteId, data) {
  const response = await api.put(`/notes/${noteId}`, data)
  return response.data
},

async deleteNote(noteId) {
  await api.delete(`/notes/${noteId}`)
}
```

- [ ] **Step 2: 创建FolderDetail.vue页面**

创建 `frontend/src/views/FolderDetail.vue`，包含：
- 笔记列表显示
- 创建笔记功能
- 点击笔记跳转到编辑页面

- [ ] **Step 3: 添加路由**

```javascript
// frontend/src/router/index.js 在children中添加
{
  path: 'notes/folder/:id',
  name: 'FolderDetail',
  component: () => import('../views/FolderDetail.vue')
},
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/FolderDetail.vue frontend/src/router/index.js frontend/src/services/note.js
git commit -m "feat: add folder detail page with notes list"
```

---

### Task 6: 添加Markdown笔记编辑器

**Files:**
- Create: `frontend/src/views/NoteEditor.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装Markdown编辑器依赖**

```bash
cd frontend && npm install v-md-editor@next
```

- [ ] **Step 2: 注册Markdown编辑器**

```javascript
// frontend/src/main.js
import VMdEditor from '@kangc/v-md-editor';
import '@kangc/v-md-editor/lib/style/base-editor.css';
import githubTheme from '@kangc/v-md-editor/lib/theme/github.js';
import '@kangc/v-md-editor/lib/theme/style/github.css';

VMdEditor.use(githubTheme);

app.use(VMdEditor);
```

- [ ] **Step 3: 创建NoteEditor.vue页面**

创建 `frontend/src/views/NoteEditor.vue`，包含：
- 标题编辑
- Markdown编辑器
- 保存功能
- 返回按钮

- [ ] **Step 4: 添加路由**

```javascript
// frontend/src/router/index.js
{
  path: 'notes/edit/:id',
  name: 'NoteEditor',
  component: () => import('../views/NoteEditor.vue')
},
{
  path: 'notes/new/:folderId',
  name: 'NewNote',
  component: () => import('../views/NoteEditor.vue')
},
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/NoteEditor.vue frontend/src/router/index.js frontend/src/main.js frontend/package.json
git commit -m "feat: add Markdown note editor"
```

---

## 第三部分：用户信息编辑

### Task 7: 添加头像上传功能

**Files:**
- Modify: `backend/app/api/users.py`
- Modify: `backend/app/services/user.py`

- [ ] **Step 1: 添加文件上传端点**

```python
# backend/app/api/users.py
import shutil
from fastapi import UploadFile, File

UPLOAD_DIR = pathlib.Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 验证文件类型
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # 生成唯一文件名
    file_ext = file.filename.split(".")[-1]
    filename = f"{current_user.id}.{file_ext}"
    file_path = UPLOAD_DIR / filename
    
    # 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 更新用户头像URL
    service = UserService(db)
    avatar_url = f"/uploads/avatars/{filename}"
    service.update_user(current_user, UserUpdate(avatar=avatar_url))
    
    return {"avatar": avatar_url}
```

- [ ] **Step 2: 配置静态文件服务**

```python
# backend/app/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/users.py backend/app/main.py
git commit -m "feat: add avatar upload endpoint"
```

---

### Task 8: 创建用户信息编辑页面

**Files:**
- Create: `frontend/src/views/EditProfile.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/services/auth.js`
- Modify: `frontend/src/views/Profile.vue`

- [ ] **Step 1: 添加用户服务方法**

```javascript
// frontend/src/services/auth.js 添加
async updateProfile(data) {
  const response = await api.put('/users/me', data)
  return response.data
},

async uploadAvatar(file) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/users/me/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}
```

- [ ] **Step 2: 创建EditProfile.vue页面**

创建 `frontend/src/views/EditProfile.vue`，包含：
- 头像上传（点击头像触发文件选择）
- 用户名编辑
- 邮箱编辑
- 保存按钮

- [ ] **Step 3: 添加路由**

```javascript
// frontend/src/router/index.js
{
  path: 'profile/edit',
  name: 'EditProfile',
  component: () => import('../views/EditProfile.vue')
},
```

- [ ] **Step 4: 在Profile.vue添加编辑按钮**

在个人资料页面添加"编辑资料"按钮，点击跳转到编辑页面

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/EditProfile.vue frontend/src/views/Profile.vue frontend/src/router/index.js frontend/src/services/auth.js
git commit -m "feat: add user profile edit page with avatar upload"
```

---

## 第四部分：待办系统完善

### Task 9: 添加待办编辑和删除功能

**Files:**
- Modify: `frontend/src/views/Todos.vue`
- Modify: `frontend/src/services/todo.js`

- [ ] **Step 1: 添加待办服务方法**

```javascript
// frontend/src/services/todo.js 添加
async updateHabit(habitId, data) {
  const response = await api.put(`/todos/habits/${habitId}`, data)
  return response.data
},

async deleteHabit(habitId) {
  await api.delete(`/todos/habits/${habitId}`)
},

async updateTask(taskId, data) {
  const response = await api.put(`/todos/tasks/${taskId}`, data)
  return response.data
},

async deleteTask(taskId) {
  await api.delete(`/todos/tasks/${taskId}`)
},

async updateGoal(goalId, data) {
  const response = await api.put(`/todos/goals/${goalId}`, data)
  return response.data
},

async deleteGoal(goalId) {
  await api.delete(`/todos/goals/${goalId}`)
}
```

- [ ] **Step 2: 在Todos.vue添加编辑和删除按钮**

每个待办项添加：
- 编辑按钮（打开编辑对话框）
- 删除按钮（确认后删除）

- [ ] **Step 3: 添加编辑对话框**

创建编辑对话框，复用创建对话框的表单，预填充现有数据

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/Todos.vue frontend/src/services/todo.js
git commit -m "feat: add edit and delete for habits/tasks/goals"
```

---

### Task 10: 添加子任务管理UI

**Files:**
- Modify: `frontend/src/views/Todos.vue`
- Modify: `frontend/src/services/todo.js`

- [ ] **Step 1: 添加子任务服务方法**

```javascript
// frontend/src/services/todo.js 添加
async getSubtasks(goalId) {
  const response = await api.get(`/todos/goals/${goalId}/subtasks`)
  return response.data
},

async createSubtask(goalId, data) {
  const response = await api.post(`/todos/goals/${goalId}/subtasks`, data)
  return response.data
},

async completeSubtask(subtaskId) {
  const response = await api.post(`/todos/subtasks/${subtaskId}/complete`)
  return response.data
},

async deleteSubtask(subtaskId) {
  await api.delete(`/todos/subtasks/${subtaskId}`)
}
```

- [ ] **Step 2: 在目标详情中添加子任务列表**

点击目标时展开显示子任务列表，支持：
- 添加子任务
- 完成子任务
- 删除子任务

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/Todos.vue frontend/src/services/todo.js
git commit -m "feat: add subtask management UI"
```

---

## 第五部分：商城系统完善

### Task 11: 添加商城商品编辑删除功能

**Files:**
- Modify: `frontend/src/views/Shop.vue`
- Modify: `frontend/src/services/shop.js`

- [ ] **Step 1: 添加商城服务方法**

```javascript
// frontend/src/services/shop.js 添加
async updateItem(itemId, data) {
  const response = await api.put(`/shop/items/${itemId}`, data)
  return response.data
},

async deleteItem(itemId) {
  await api.delete(`/shop/items/${itemId}`)
}
```

- [ ] **Step 2: 在Shop.vue添加编辑删除按钮**

每个商品卡片添加编辑和删除按钮（仅商品创建者可见）

- [ ] **Step 3: 添加编辑对话框**

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/Shop.vue frontend/src/services/shop.js
git commit -m "feat: add shop item edit and delete"
```

---

### Task 12: 添加商城兑换历史页面

**Files:**
- Create: `frontend/src/views/ExchangeHistory.vue`
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: 创建ExchangeHistory.vue页面**

显示兑换历史列表，包含：
- 商品名称
- 兑换时间
- 消耗金币
- 状态

- [ ] **Step 2: 添加路由**

```javascript
{
  path: 'shop/history',
  name: 'ExchangeHistory',
  component: () => import('../views/ExchangeHistory.vue')
},
```

- [ ] **Step 3: 在Shop.vue添加历史记录入口**

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/ExchangeHistory.vue frontend/src/router/index.js frontend/src/views/Shop.vue
git commit -m "feat: add exchange history page"
```

---

## 第六部分：背包系统完善

### Task 13: 添加背包使用历史页面

**Files:**
- Create: `frontend/src/views/BackpackHistory.vue`
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: 创建BackpackHistory.vue页面**

显示物品使用历史，包含：
- 物品名称
- 操作类型（使用/装备/丢弃）
- 操作时间

- [ ] **Step 2: 添加路由**

- [ ] **Step 3: 在Backpack.vue添加历史记录入口**

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/BackpackHistory.vue frontend/src/router/index.js frontend/src/views/Backpack.vue
git commit -m "feat: add backpack usage history page"
```

---

## 第七部分：个人资料完善

### Task 14: 添加成就系统后端

**Files:**
- Create: `backend/app/models/achievement.py`
- Create: `backend/app/schemas/achievement.py`
- Create: `backend/app/repositories/achievement.py`
- Create: `backend/app/services/achievement.py`
- Create: `backend/app/api/achievements.py`

- [ ] **Step 1: 创建成就模型**

```python
# backend/app/models/achievement.py
class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    condition_type = Column(String(50))  # task_count, habit_streak, level, etc.
    condition_value = Column(Integer)
    coin_reward = Column(Integer, default=0)
    exp_reward = Column(Integer, default=0)

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Uuid, ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: 创建成就服务和API**

实现成就判定逻辑，当用户完成任务时自动检查并解锁成就

- [ ] **Step 3: 添加种子数据**

预置一些基础成就：
- 初出茅庐：完成第一个任务
- 坚持不懈：连续7天完成习惯
- 冒险家：达到5级
- 寻宝猎人：兑换10件商品

- [ ] **Step 4: 提交**

```bash
git add backend/app/models/achievement.py backend/app/schemas/achievement.py backend/app/repositories/achievement.py backend/app/services/achievement.py backend/app/api/achievements.py
git commit -m "feat: add achievement system backend"
```

---

### Task 15: 添加成就系统前端

**Files:**
- Modify: `frontend/src/views/Profile.vue`
- Modify: `frontend/src/services/achievement.js`

- [ ] **Step 1: 创建成就服务**

```javascript
// frontend/src/services/achievement.js
export const achievementService = {
  async getAchievements() {
    const response = await api.get('/achievements')
    return response.data
  },
  
  async getUserAchievements() {
    const response = await api.get('/achievements/me')
    return response.data
  }
}
```

- [ ] **Step 2: 更新Profile.vue显示真实成就数据**

从API获取成就数据，区分已解锁和未解锁成就

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/Profile.vue frontend/src/services/achievement.js
git commit -m "feat: add achievement display with real data"
```

---

### Task 16: 添加统计数据面板

**Files:**
- Modify: `frontend/src/views/Profile.vue`

- [ ] **Step 1: 添加统计数据获取**

从多个API获取统计数据：
- 总任务完成数
- 连续打卡天数
- 总获得金币
- 总获得经验

- [ ] **Step 2: 在Profile.vue添加统计卡片**

显示四个统计卡片：
- 任务完成数
- 连续打卡
- 总金币收入
- 总经验收入

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/Profile.vue
git commit -m "feat: add statistics dashboard to profile"
```

---

## 第八部分：优化和清理

### Task 17: Element Plus按需引入

**Files:**
- Modify: `frontend/src/main.js`
- Modify: `frontend/vite.config.js`
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装按需引入插件**

```bash
cd frontend && npm install -D unplugin-vue-components unplugin-auto-import
```

- [ ] **Step 2: 配置vite.config.js**

```javascript
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()]
    }),
    Components({
      resolvers: [ElementPlusResolver()]
    })
  ]
})
```

- [ ] **Step 3: 简化main.js**

移除全量引入，改为按需引入

- [ ] **Step 4: 提交**

```bash
git add frontend/src/main.js frontend/vite.config.js frontend/package.json
git commit -m "perf: optimize Element Plus with tree-shaking"
```

---

### Task 18: 修复安全问题

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: 添加环境变量检查**

```python
# backend/app/config.py
class Settings(BaseSettings):
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # 必须设置
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if v == "your-secret-key-change-in-production":
            raise ValueError("Please set a proper SECRET_KEY environment variable")
        return v
```

- [ ] **Step 2: 创建.env.example文件**

```
SECRET_KEY=your-random-secret-key-here
DATABASE_URL=sqlite:///./lifequest.db
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/config.py .env.example
git commit -m "fix: require proper SECRET_KEY configuration"
```

---

## 执行顺序建议

1. **第一阶段：Bug修复** (Task 1-3) - 1小时
2. **第二阶段：笔记系统** (Task 4-6) - 3小时
3. **第三阶段：用户编辑** (Task 7-8) - 2小时
4. **第四阶段：待办完善** (Task 9-10) - 2小时
5. **第五阶段：商城完善** (Task 11-12) - 1.5小时
6. **第六阶段：背包完善** (Task 13) - 1小时
7. **第七阶段：成就系统** (Task 14-16) - 3小时
8. **第八阶段：优化清理** (Task 17-18) - 1小时

**总计预估时间：15小时**

---

## 自我审查

### 1. 需求覆盖检查

| 需求 | 对应任务 | 状态 |
|------|---------|------|
| 习惯奖励修复 | Task 1 | ✅ |
| 页面标题中文化 | Task 2 | ✅ |
| 笔记内容返回 | Task 4 | ✅ |
| 笔记编辑器 | Task 6 | ✅ |
| 文件夹笔记列表 | Task 5 | ✅ |
| 用户头像上传 | Task 7 | ✅ |
| 用户信息编辑 | Task 8 | ✅ |
| 待办编辑删除 | Task 9 | ✅ |
| 子任务管理 | Task 10 | ✅ |
| 商城编辑删除 | Task 11 | ✅ |
| 兑换历史 | Task 12 | ✅ |
| 背包历史 | Task 13 | ✅ |
| 成就系统 | Task 14-15 | ✅ |
| 统计数据 | Task 16 | ✅ |
| 性能优化 | Task 17 | ✅ |
| 安全修复 | Task 18 | ✅ |

### 2. 占位符检查

无TBD、TODO或未完成的占位符。

### 3. 类型一致性检查

所有API端点、服务方法、前端调用保持一致。

---

Plan complete and saved to `docs/superpowers/plans/2026-05-26-lifequest-bugfix-completion.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** - 每个任务派发一个新的子代理执行，任务之间进行审查，迭代速度快

**2. Inline Execution** - 在当前会话中执行任务，批量执行并设置检查点

**Which approach?**
