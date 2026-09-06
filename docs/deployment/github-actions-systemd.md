# GitHub Actions 自动部署

本项目当前使用服务器上的 `systemd + uvicorn` 部署，不需要迁移 Docker。

## GitHub Secrets

在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中添加：

- `SERVER_HOST`: 服务器公网 IP 或域名
- `SERVER_USER`: SSH 用户名，例如当前的 `capkin`
- `SERVER_SSH_KEY`: 对应 SSH 私钥的完整内容
- `SERVER_KNOWN_HOSTS`: 服务器 SSH 主机公钥对应的 known_hosts 内容
- `SERVER_APP_DIR`: 生产项目目录；当前服务器使用 `/home/capkin/lifequest-prod`，标准系统级部署可使用 `/opt/lifequest`
- `CLOUDFLARE_ACCESS_CLIENT_ID`: 可选，Cloudflare Access Service Token 的 Client ID
- `CLOUDFLARE_ACCESS_CLIENT_SECRET`: 可选，Cloudflare Access Service Token 的 Client Secret

不要添加或提交服务器的 `.env`、数据库文件、上传目录和私钥。

## 当前服务器的 conda 用户服务

开发目录 `/home/capkin/apps/LifeQuest` 只用于开发；当前生产目录是 `/home/capkin/lifequest-prod`。服务器使用 conda 环境 `lifequest` 和用户级 systemd 服务。服务文件位于：

```text
~/.config/systemd/user/lifequest.service
```

服务需要提前创建并启用：

```bash
sudo loginctl enable-linger "$USER"
systemctl --user daemon-reload
systemctl --user enable --now lifequest.service
```

`update-systemd.sh` 会根据目标目录自动识别用户级服务并使用 conda 环境；也可以显式指定：

```bash
export LIFEQUEST_CONDA_PREFIX="$HOME/miniforge3/envs/lifequest"
export LIFEQUEST_SYSTEMD_SCOPE=user
```

如果服务器使用旧的系统级服务，脚本会继续使用 `sudo systemctl`。首次部署前，服务器用户还必须能通过 `git@github.com:capkten/LifeQuest.git` 拉取代码。

`SERVER_HOST` 必须是 GitHub Actions runner 能访问的公网 IP 或域名。内网地址（例如 `192.168.x.x`）不能直接用于 GitHub 云端 runner；这种情况下需要公网入口、VPN、Cloudflare Tunnel，或改用 self-hosted runner。

## 通过 Cloudflare Tunnel 连接 SSH

如果 `SERVER_HOST` 使用 Cloudflare Tunnel 域名（例如 `ssh.capkin.cn`），在 Cloudflare Zero Trust 的 Tunnel 路由中添加 Published application：

```text
Hostname: ssh.capkin.cn
Service: SSH
Origin: localhost:22
```

为这个 hostname 配置 Access 应用，并添加允许指定 Service Token 的 `Service Auth` 策略。然后在 GitHub Secrets 中添加上面的两个 `CLOUDFLARE_ACCESS_*` Secret。workflow 检测到这两个 Secret 后，会在 GitHub runner 安装 `cloudflared`，通过 `cloudflared access ssh` 连接 Tunnel，不需要公网开放 22 端口或配置路由器端口转发。Cloudflare 官方文档要求 SSH Tunnel 客户端使用 `cloudflared`，并将 SSH 服务路由到 `ssh://localhost:22`。

如果两个 Cloudflare Secret 都为空，workflow 会回退到普通 SSH 连接，因此直连 IP 或已经开放 SSH 的域名仍然可用。

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

生成主机指纹（Tunnel 模式下仍需要校验服务器 SSH 主机密钥）：

```bash
ssh-keyscan -H <服务器地址>
```

如果域名没有直连 22 端口，可以使用服务器本机生成的 known_hosts 内容，前提是 Cloudflare Tunnel 的 SSH origin 确实指向这台服务器的 22 端口。将完整内容填入 `SERVER_KNOWN_HOSTS`。

## 发布流程

推送到 `main` 后，GitHub Actions 会依次：

1. 运行后端测试。
2. 运行前端回归测试和构建。
3. SSH 连接服务器并启动用户级 systemd 部署任务。
4. 检查服务器工作树是否有未提交改动。
5. 拉取 `main` 最新代码。
6. 更新 Python 依赖并重新构建前端。
7. 重启 `lifequest.service`。
8. 轮询部署任务并检查 `http://127.0.0.1:8000/api/health`。

测试失败、SSH 配置错误、服务器存在手工改动或健康检查失败，部署都会停止。

## Android 自动发布

修改 `frontend/android/app/build.gradle` 中的 `versionName` 或 `versionCode` 并推送到 `main` 后，Android 工作流会构建签名 APK/AAB 并创建 GitHub Release。仅修改普通前端文件不会发布 Android 版本。

还需要添加这些 GitHub Secrets：

- `ANDROID_API_BASE_URL`: Android App 使用的正式后端地址；当前为 `https://life.capkin.cn/api`
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
