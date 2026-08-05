# LifeQuest 缺陷修复验收记录

日期：2026-08-04

## 已验证

- 后端全量测试：`73 passed`。
- 后端覆盖率：此前成功报告约 `75%`；本轮覆盖率命令超过环境约 120 秒执行上限，未将超时记为通过。
- 前端生产构建：`npm run build` 通过；保留既有大 chunk warning 作为性能项。
- 浏览器响应式检查：375px、768px、1024px、1440px；首页、待办、商城、个人、笔记、记账、项目均无横向溢出，移动端底部导航存在，桌面端隐藏。
- MCP：未登录拒绝；仅接受登录上下文或显式 `LIFEQUEST_MCP_SERVICE_USER_ID`；API 不再默认启动子进程，supervisor 单独启动 MCP。
- 健康检查：`GET /api/health` 无需认证，数据库故障返回 `503`。

## 已修复范围

- 目标/任务/习惯奖励、成就奖励和金币流水事务一致性。
- 奖励、商品、库存、财务金额和债务余额边界校验。
- 财务账户、分类、交易、预算、债务、定期交易归属校验。
- 项目任务、阶段、里程碑跨项目绑定校验。
- 笔记根目录移动、迁移时间类型和 Markdown 原子写入回滚。
- 笔记迁移在文件移动或数据库阶段失败时恢复旧文件、保留旧表并回滚新节点。
- Docker healthcheck、持久化目录、MCP supervisor 和 nginx 代理配置。

## 环境限制

- 当前环境未安装 Docker，无法执行 `docker compose build/up/ps/logs` 的真实容器验收；已完成 Dockerfile、Compose、supervisor、healthcheck shell 语法和静态配置检查。
