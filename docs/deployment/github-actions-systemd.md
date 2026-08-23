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

## Android 自动发布

修改 `frontend/android/app/build.gradle` 中的 `versionName` 或 `versionCode` 并推送到 `main` 后，Android 工作流会构建签名 APK/AAB 并创建 GitHub Release。仅修改普通前端文件不会发布 Android 版本。

还需要添加这些 GitHub Secrets：

- `ANDROID_API_BASE_URL`: Android App 使用的正式后端地址，例如 `https://example.com/api`
- `ANDROID_UPDATE_MANIFEST_URL`: 可选，默认使用当前 GitHub 仓库的 Release 地址
- `ANDROID_KEYSTORE_BASE64`: Android keystore 的 Base64 内容
- `ANDROID_KEYSTORE_PASSWORD`: keystore 密码
- `ANDROID_KEY_ALIAS`: 签名 alias
- `ANDROID_KEY_PASSWORD`: alias 密码

`VITE_ANDROID_UPDATE_MANIFEST_URL` 应配置为：

```text
https://github.com/capkten/LifeQuest/releases/latest/download/latest.json
```

App 只会在 Android 原生环境检查更新。发现新版本后弹出提示，点击更新会打开 APK 下载地址；Android 最终安装仍需要用户确认。

Android 工作流使用 JDK 21；本地构建也需要安装 JDK 21，并从 `frontend/android` 目录执行 Gradle：

```bash
cd frontend/android
./gradlew assembleDebug
```
