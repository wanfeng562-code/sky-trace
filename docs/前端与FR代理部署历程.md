# Sky-Trace 前端与 FR24 代理部署历程

> **当前生产前端**：Cloudflare Pages（https://sky-trace.pages.dev/）。启动与 CORS 见 [启动说明与运行指南.md](./启动说明与运行指南.md)（2026-05-18）。

> 记录时间：2026-05-11  
> 覆盖内容：Cloudflare Pages 前端部署、Cloudflare Worker FR24 代理部署、反封禁联调

---

## 1. 背景

Sky-Trace 后端运行在私有云服务器上，FR24 数据通过 Python SDK（`ddima16-flightradarapi`）采集；前端为 Vue 3 + Vite 单页应用，需要公网可访问的静态托管。

部署目标：

- 前端静态产物通过 CDN 分发，保证 6 000+ 航班渲染流畅（≥ 30 fps）
- 绕过 FlightRadar24 对服务器 IP 的 `403 Forbidden` 封禁，通过免费的 Cloudflare Worker 代理转发请求

---

## 2. 第一次尝试：误用 Workers 托管前端（2026-05-09）

### 构建日志摘要

```
Executing user deploy command: npx wrangler deploy
✨ Read 28 files from the assets directory /opt/buildhome/repo/client
Total Upload: 0.33 KiB / gzip: 0.24 KiB
Deployed sky-trace triggers (0.77 sec)
  https://sky-trace.sweet-sky-4167.workers.dev
✨ Success! Build completed.
```

### 问题分析

本次部署实际上使用了 `npx wrangler deploy`——这是 **Cloudflare Workers** 的部署命令，而非 **Cloudflare Pages** 的构建流程。

| 现象                   | 原因                                                |
| ---------------------- | --------------------------------------------------- |
| 只上传了 28 个原始文件 | 直接上传 `client/` 源码，**未执行** `npm run build` |
| 单次上传仅 0.33 KiB    | 资产文件极小，说明只上传了配置/入口，而非编译产物   |
| 浏览器无法渲染地图     | `.vue` 文件需经 Vite 编译，浏览器无法直接解析       |

### Workers vs Pages 的核心区别

| 特性     | Cloudflare Workers           | Cloudflare Pages                         |
| -------- | ---------------------------- | ---------------------------------------- |
| 本质定位 | 无服务器计算（运行 JS 逻辑） | Jamstack 静态托管（分发 HTML/JS/CSS）    |
| 构建能力 | 需手动打包后上传产物         | **内置 CI/CD**，自动执行 `npm run build` |
| 适用场景 | API 代理、请求改写、KV 存储  | Vue/React 前端应用托管                   |

**结论**：前端应迁移至 **Cloudflare Pages**；Workers 仅用于 FR24 代理。

---

## 3. FR24 403 问题背景

FlightRadar24 于近期更新了 Cloudflare Challenge 防护，常规 User-Agent 轮换方案已无效，服务器 IP 频繁收到 `403 Forbidden`。

社区 Issue [#96] 提出使用 Cloudflare Worker 作为代理的解决方案：

- **原理**：请求经由 Cloudflare 边缘节点转发，FR24 难以封禁 Cloudflare 自身的出口 IP
- **免费额度**：Workers 免费套餐每日 100 000 次请求，远超项目需要
- **SDK**：使用 [`ddima16-flightradarapi`](https://github.com/DimaD16/FlightRadarAPI) fork，支持 `proxy_url` 参数

安装：

```bash
pip uninstall FlightRadarAPI
pip install ddima16-flightradarapi
```

---

## 4. FR24 代理 Worker 部署

### 4.1 部署方式

通过 Cloudflare 1-click Deploy 按钮部署代理脚本：

[![Deploy to Cloudflare](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/DimaD16/cloudflare-workers-fr24-proxy/tree/main)

部署完成后，Worker 分配地址：

```
https://sky-trace-562.sweet-sky-4167.workers.dev
```

### 4.2 验证代理可用性

在浏览器访问：

```
https://sky-trace-562.sweet-sky-4167.workers.dev/?url=https://www.google.com
```

页面能加载即代表代理正常转发请求。

### 4.3 后端集成

在 `.env` 中配置代理地址（已通过 `settings.fr24_proxy_url` 读取）：

```env
FR24_PROXY_URL=https://sky-trace-562.sweet-sky-4167.workers.dev/?url=
```

Python 初始化方式（由 `unified_pipeline.py` 内部处理）：

```python
from FlightRadar24 import FlightRadar24API
fr = FlightRadar24API(proxy_url=settings.fr24_proxy_url)
```

> Worker 代理在国内环境下同样受益：服务器无需科学上网，所有 FR24 请求均经由 Cloudflare 边缘节点发出。

---

## 5. 前端迁移至 Cloudflare Pages（2026-05-11）

### 5.1 配置修改

在 Cloudflare Pages 控制台重新关联 GitHub 仓库，并修改 Build Settings：

| 配置项                 | 旧值（错误）               | 新值（正确）                     |
| ---------------------- | -------------------------- | -------------------------------- |
| Root Directory         | `/`（仓库根目录）          | `client`                         |
| Build command          | 无 / `npx wrangler deploy` | `npm run build`                  |
| Build output directory | 无                         | `dist`                           |
| Deploy command         | `npx wrangler deploy`      | （Pages 不需要，由平台自动处理） |

### 5.2 成功构建日志

```
Using v2 root directory strategy
Detected the following tools from environment: npm@10.9.2, nodejs@22.16.0
Installing project dependencies: npm clean-install --progress=false
  added 103 packages in 5s
Executing user command: npm run build
  vite v5.4.21 building for production...
  ✓ 103 modules transformed.
  dist/index.html                   0.40 kB │ gzip:   0.27 kB
  dist/assets/index-DaNiv2Ae.css   70.44 kB │ gzip:  10.45 kB
  dist/assets/index-CGUWL9zY.js   977.38 kB │ gzip: 285.73 kB
  ✓ built in 4.48s
Uploaded 3 files (2.36 sec)
✨ Upload complete!
Success: Assets published!
Success: Your site was deployed!
```

### 5.3 关键指标对比

| 指标           | 第一次（Workers 误部署）      | 第二次（Pages 正确部署）        |
| -------------- | ----------------------------- | ------------------------------- |
| 上传文件数     | 28 个源码文件                 | 3 个编译产物（HTML + CSS + JS） |
| 上传体积       | 0.33 KiB                      | ~1 MB（完整编译产物）           |
| 是否执行构建   | ❌ 否                          | ✅ 是（Vite 4.48s）              |
| 是否可访问地图 | ❌ 否（浏览器无法解析 `.vue`） | ✅ 是                            |

### 5.4 Vite 构建警告说明

```
(!) Some chunks are larger than 500 kB after minification.
Consider using dynamic import() to code-split the application
```

此警告来源于 MapLibre GL JS 等大型地图库被打包进了单一 chunk（约 977 kB）。  
**对当前项目无需立即处理**——Cloudflare CDN 的 gzip 传输仅约 286 kB，首屏加载时间在正常范围内。  
若后续需要优化，可在 `vite.config.ts` 中使用 `build.rollupOptions.output.manualChunks` 拆分 MapLibre 为独立 chunk。

---

## 6. 部署后配置

### 6.1 CORS 配置

前端运行在 Pages 域名（`https://sky-trace.pages.dev`）下，FastAPI 后端需允许跨域：

```python
# server/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sky-trace.pages.dev",   # Cloudflare Pages 前端
        "http://localhost:5173",          # 本地开发
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 6.2 前端 API 地址

前端代码中的后端 API 地址需从 `localhost:8000` 改为云服务器公网 IP 或域名：

```
VITE_API_BASE_URL=https://<your-server-ip-or-domain>:8000
```

---

## 7. 最终架构

```
用户浏览器
    │
    ▼
Cloudflare Pages（静态 CDN 分发）
https://sky-trace.pages.dev
    │  HTTP API / WebSocket
    ▼
云服务器 FastAPI 后端（8000 端口）
    │ FR24 数据采集（通过代理）
    ▼
Cloudflare Worker（代理节点）
https://sky-trace-562.sweet-sky-4167.workers.dev/?url=
    │
    ▼
FlightRadar24（绕过 403 封禁）
```

| 组件           | 平台              | 作用                                     |
| -------------- | ----------------- | ---------------------------------------- |
| 前端 Vue 3 SPA | Cloudflare Pages  | 托管编译后的 `dist/` 产物，全球 CDN 加速 |
| FR24 代理      | Cloudflare Worker | 转发 FR24 请求，绕过服务器 IP 封禁       |
| FastAPI 后端   | 私有云服务器      | 数据采集、持久化、WebSocket 推送         |

---

## 8. 遗留问题与后续

| 问题                     | 状态       | 说明                                                                    |
| ------------------------ | ---------- | ----------------------------------------------------------------------- |
| `wrangler.json` 配置警告 | ⚠️ 可忽略   | Pages 检测到 Workers 配置文件，打印提示但不影响部署                     |
| JS chunk 超过 500 kB     | ⚠️ 低优先级 | gzip 后约 286 kB，暂不影响体验                                          |
| FR24 403 触发后不可自愈  | 🔲 待实现   | 当前退级后不会重试；可加入指数退避重试（见 API 手册 §4.2）              |
| HTTPS 协议一致性         | ✅ 正常     | Cloudflare Pages 强制 HTTPS，后端如使用 HTTP 需配置 Cloudflare SSL 回源 |
