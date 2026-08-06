# LifeQuest 笔记 MCP 工具设计

## 目标

让接入 LifeQuest MCP 的 AI 能完成笔记模块的常规操作：管理笔记本、浏览目录、创建/读取/修改/移动/删除笔记及文件夹，并进行检索。

## 范围

复用现有 `NoteService`、Repository 和 Schema，不新增数据表，不直接操作 Markdown 文件。保留现有 `search_notes`、`get_note`、`update_note`，补齐其余 REST 笔记能力：

- 笔记本：`list_notebooks`、`create_notebook`、`delete_notebook`
- 目录：`get_notebook_tree`、`list_note_children`、`create_folder`
- 笔记：`create_note`、`delete_node`
- 节点：`rename_or_move_node`
- 检索：`list_recent_notes`、`discover_notes`、`mark_note_opened`

## 安全与错误

每个工具先调用 `_resolve_user_id()`。通过笔记本用户归属或节点所属笔记本验证当前用户；不存在、类型不正确或不属于当前用户的资源均视为不可访问。名称冲突、非法父节点、自移动及移动到后代等错误复用 `NoteService` 的 `ValueError`，不绕过服务层。

删除笔记本和节点使用独立工具，明确返回删除结果；删除文件夹时沿用服务层递归删除其子节点和正文文件的行为。

## 返回数据

Notebook 返回序列化后的笔记本对象；目录树返回嵌套节点；节点列表返回序列化后的节点；笔记创建、读取、更新返回节点元数据和正文。日期、UUID 继续使用现有 `_serialize` 转换为 JSON 安全值。

## 验收标准

1. 登录后 AI 可以从笔记本列表开始定位任意笔记。
2. AI 可以创建根目录/子目录下的笔记和文件夹。
3. AI 可以读取和更新正文、标题、摘要、标签、置顶状态。
4. AI 可以重命名、移动和删除节点，并遵守同名及树结构约束。
5. AI 可以按标题/摘要/标签搜索，查看最近笔记，并按现有 discover 参数筛选。
6. 未登录或访问其他用户资源时不会泄露数据。
