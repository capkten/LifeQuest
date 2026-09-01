# LifeQuest Windows 客户端

`desktop/` 是基于 Tauri 2 的 Windows 客户端。它复用 LifeQuest 的 Vue 页面，并提供本地文件夹选择、Markdown 扫描、文件监听和同步写入能力。

## 使用前提

- Windows 10/11，已安装 WebView2。
- Node.js 20 或更高版本。
- Rust stable 工具链和 Tauri 2 的 Windows 构建依赖。
- 可访问 LifeQuest 服务端的地址。

## 本地开发

在仓库根目录执行：

```powershell
npm --prefix frontend ci
npm --prefix desktop ci
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm --prefix desktop run dev
```

开发模式也可以省略 `VITE_API_BASE_URL`，此时客户端通过 Vite 开发服务器代理 `/api` 请求。生产客户端必须提供服务端地址，例如：

```powershell
$env:VITE_API_BASE_URL = "https://lifequest.example.com"
```

## 构建安装包

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-desktop.ps1
```

构建结果位于 `desktop/src-tauri/target/release/bundle/`，包含 NSIS `.exe` 和 WiX `.msi`。推送到 `main` 后，GitHub Actions 的 `Build Windows Desktop` workflow 会构建并上传这两个安装包作为 workflow artifact；正式分发前仍应使用发布证书签名。

GitHub Actions 构建正式安装包时必须配置 `DESKTOP_API_BASE_URL` Secret，例如 `https://lifequest.example.com`。该地址会在构建时写入客户端；未配置时 workflow 会主动失败，避免生成无法连接服务端的安装包。

## 文件夹映射规则

- 只同步 UTF-8 编码的 `.md` 文件和文件夹。
- `.lifequest/` 保存本地同步清单，`.lifequest-conflicts/` 保存无法自动合并的副本；这两个目录不会再次被扫描。
- 浏览器页面只负责权限、预览和冲突记录；文件夹选择和本地写入只在 Windows 客户端中执行。
- 首次同步先生成预览，用户确认后才写入文件夹。
- 同步清单记录节点 ID、远端修订号、内容哈希和上次同步内容，用于三方合并。
- 网络失败的上传操作会写入应用数据目录中的持久化队列，并在下次同步按退避策略重试。访问令牌不会写入该队列或客户端状态文件。

## 冲突处理

双方只修改不同 Markdown 行时，客户端会自动合并并同时更新本地文件和云端内容。无法安全合并时会生成恢复副本，并在网页的“冲突记录”中提供“保留本地”和“保留云端”操作。

删除采用保守策略：本地误删的已同步文件会先恢复为云端版本；远端删除而本地仍有内容时会进入冲突记录，不会直接丢弃本地文件。

当前版本只同步 Markdown 文本，不同步图片附件、其他二进制文件或文件权限。
