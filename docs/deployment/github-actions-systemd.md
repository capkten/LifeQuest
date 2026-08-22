# GitHub Actions 自动部署

本项目当前使用服务器上的 `systemd + uvicorn` 部署，不需要迁移 Docker。

## GitHub Secrets

在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中添加：

- `SERVER_HOST`: 服务器公网 IP 或域名
- `SERVER_USER`: SSH 用户名，例如当前的 `root`
- `SERVER_SSH_KEY`: 对应 SSH 私钥的完整内容
- `SERVER_KNOWN_HOSTS`: 本地执行 `ssh-keyscan -H <服务器地址>` 的完整输出
- `SERVER_APP_DIR`: 项目目录，例如 `/root/LifeQuest`，也可以不填

不要添加或提交服务器的 `.env`、数据库文件、上传目录和私钥。

## SSH 密钥

在本地生成专用密钥：

```bash
ssh-keygen -t ed25519 -C "github-actions-lifequest" -f ~/.ssh/lifequest_actions
```

把 `~/.ssh/lifequest_actions.pub` 追加到服务器用户的：

```text
~/.ssh/authorized_keys
```

把 `~/.ssh/lifequest_actions` 的完整内容填入 `SERVER_SSH_KEY`。

生成主机指纹：

```bash
ssh-keyscan -H <服务器地址>
```

将完整输出填入 `SERVER_KNOWN_HOSTS`。

## 发布流程

推送到 `main` 后，GitHub Actions 会依次：

1. 运行后端测试。
2. 运行前端回归测试和构建。
3. SSH 连接服务器。
4. 检查服务器工作树是否有未提交改动。
5. 拉取 `main` 最新代码。
6. 更新 Python 依赖并重新构建前端。
7. 重启 `lifequest.service`。
8. 检查 `http://127.0.0.1:8000/api/health`。

测试失败、SSH 配置错误、服务器存在手工改动或健康检查失败，部署都会停止。
