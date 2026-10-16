# Sky-Trace

Sky-Trace 是一个航班信息跟踪平台，采用 **Cloudflare Pages 静态前端 + 云服务器 FastAPI 后端** 的公网可访问架构

当前生产状态（2026-10-16 核验）：原 AutoDL 实例已释放，正式站点暂时仅提供天地图浏览及中英文切换；实时航班、统计和历史回放暂停。开发环境仍可连接本地后端。恢复方式见[前端发布与服务停用记录](./docs/前端发布与服务停用记录-20261013.md)，本次代码检查和提交范围见[提交前全局核验](./docs/提交前全局核验-20261016.md)。

## 1. 技术栈说明

### 1.1 版本基线
- Python: 3.10+
- Node.js: 20.19+ 或 22.12+（与 Vite 运行要求一致）
- npm: 10+

### 1.2 核心组件
- 后端服务: FastAPI, Uvicorn, aiohttp, APScheduler
- 前端界面: Vue3, TypeScript, Vite, Pinia
- 可视化: MapLibre GL JS（天地图底图及中文注记、本地 GeoNames 英文地名）, ECharts
- 数据存储: SQLite
- 可选代理: Cloudflare Worker（用于 FR24 补充数据代理）
- 部署: Cloudflare Pages（前端，https://sky-trace.pages.dev/），云服务器（后端）

---

## 2. 系统架构

```
┌─────────────────────────────────────────────┐
│         前端（Vue3 + TypeScript + Vite）      │
│  构建后部署至 Cloudflare Pages 等静态托管      │
└──────────────┬──────────────────────────────┘
               │  HTTP REST + WebSocket（公网）
               ▼
┌─────────────────────────────────────────────┐
│     后端（FastAPI + Uvicorn）                 │
│  部署至云服务器（公网 IP / 域名）              │
│  SQLite 持久化 + 三层统一采集管道              │
└──────────────┬──────────────────────────────┘
               │
               ▼
  外部 API: OpenSky Network / OpenWeather / AirLabs
             \ 可选 FR24 Worker 代理
```

通信方式：
- client ↔ server：HTTP REST（查询/统计）+ WebSocket（实时推送）
- 前端通过环境变量 `VITE_API_BASE_URL` 指向后端公网地址

---

## 3. 快速启动指南

按后端 → 前端的顺序执行。

### 3.1 后端启动（Python）

**最简方式**（已安装 Python 3.10+，在 `server` 目录下执行）：

```powershell
cd server
pip install -r requirements.txt
python run.py
```

`run.py` 会自动读取同目录下的 `.env`（若存在），默认监听 `http://127.0.0.1:8000`。  
验证：`http://127.0.0.1:8000/api/v1/health` → 响应中的 `data.status="ok"`、`data.db="ok"`。

**推荐：使用虚拟环境**（避免污染系统 Python）：

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

**等价启动方式**（需手动指定 host/port）：

```powershell
cd server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000   # 本地
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000     # 云服务器公网
```

#### 3.1.1 配置文件（可选，另说）

首次使用或需要真实数据源时，再配置 `server/.env`：

```powershell
cd server
copy .env.development.example .env
```

用编辑器打开 `server/.env`，按需填写（不填也能启动，部分功能会降级）：

| 字段                                          | 申请地址                                                               |
| --------------------------------------------- | ---------------------------------------------------------------------- |
| `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` | https://opensky-network.org → Account → API Clients → 创建客户端后复制 |
| `OPENWEATHER_API_KEY`                         | https://openweathermap.org/api                                         |
| `AIRLABS_API_KEY`                             | https://airlabs.co/                                                    |

云服务器部署时，将 `APP_HOST=0.0.0.0`，并在安全组放行 **8000** 端口；`CORS_ALLOW_ORIGINS` 需包含前端域名（如 `https://sky-trace.pages.dev`）。

> `.env` 已在 `.gitignore` 中排除，不会被提交。  
> 更多字段与日志说明见 [docs/启动说明与运行指南.md](docs/启动说明与运行指南.md)。

### 3.2 前端启动（Vue3）

```powershell
cd client
npm install
npm run dev -- --host 127.0.0.1 --strictPort   # 开发服务器：http://127.0.0.1:5173
npm run build   # 生产构建，产物在 dist/（可直接部署至 Pages）
```

底图已统一切换为天地图。请在 `client/.env.development.local` 配置 `VITE_TIANDITU_KEY`，生产环境使用 `.env.production.local` 或部署平台变量。核实当前地图服务的审图号后配置 `VITE_MAP_APPROVAL_NUMBER`；不同底图编号可用 `VITE_MAP_APPROVAL_VECTOR` / `IMAGERY` / `TERRAIN` 分别指定。未配置 Key 时显示中性画布，不会回退到其他地图。详细说明及软著补正材料要求见 [地图页面配置说明](docs/地图页面配置说明文档.md)。

中英文地名随底图面板中的语言设置切换：中文使用天地图官方注记，英文使用本地 GeoNames 数据，包含 236,046 条城市、城镇及其他聚居地记录，部分名称使用拉丁字母音译；放大后按视野加载更多地名。数据来源、许可证、覆盖范围和更新方法见上述说明。

本地开发通常使用 `client/.env.development`（已含 `VITE_API_BASE_URL`、`VITE_WS_URL`）。  
当前生产配置保持后端停用：

```
VITE_BACKEND_ENABLED=false
VITE_API_BASE_URL=
VITE_WS_URL=
```

重新租用服务器并验证后，设置 `VITE_BACKEND_ENABLED=true`，同时配置新的 HTTPS API 与 WSS 地址，重新构建。开发环境默认启用本地后端。Cloudflare Pages 的 Production 环境已经保存浏览器 Key 和停用配置；Preview 环境未配置 Key，只显示中性画布。真实 Key 仅放本地忽略文件或平台环境变量。

---

## 4. 后端数据采集架构

Sky-Trace 后端使用**三层统一采集管道**，前端不直接调用第三方 API：

| 层     | 数据源          | 内容                                     | 采集频率（开发档）  |
| ------ | --------------- | ---------------------------------------- | ------------------- |
| 实时层 | OpenSky Network | 全球航班位置/速度/高度/机型类别          | 90 秒/次            |
| 环境层 | OpenWeather     | DB 枢纽天气 + AQI + **GRD 5° 动态网格**  | 300 秒/次           |
| 商业层 | AirLabs + FR24  | 航班号/起降机场/机型/航司（FR24 后台补） | 86400 秒 + 后台循环 |

### 4.1 主要 API 端点

| 端点                              | 说明                               |
| --------------------------------- | ---------------------------------- |
| `GET /api/v1/flights`             | 航班列表                           |
| `GET /api/v1/weather-grid`        | 活跃 5° 天气网格单元（GRD）        |
| `GET /api/v1/playback`            | 历史回放帧                         |
| `GET/PUT /api/v1/places/names`    | 地名简繁缓存同步                   |
| `GET /api/v1/datahub/status`      | 三层采集状态                       |
| `GET /api/v1/datahub/weather`     | 枢纽 + GRD 天气缓存                |
| `GET /api/v1/datahub/air_quality` | 枢纽 AQI + 污染物                  |
| `GET /api/v1/datahub/snapshot`    | 聚合快照                           |
| `WS  /api/v1/ws/flights`          | 实时推送 WebSocket（广播节流 ≥2s） |

---

## 5. 项目架构简述

- **client（Vue）**：地图 / 统计 / 回放三页，MapLibre + Pinia，构建后部署至 Cloudflare Pages
- **server（Python）**：统一采集管道、SQLite 持久化、WS 与 REST，部署至云服务器
- **worker（可选）**：Cloudflare Worker 代理 FR24 请求，不属于主系统运行必需组件

## 6. 文档导航

完整索引见 **[docs/README.md](docs/README.md)**。常用：

- [启动说明与运行指南](docs/启动说明与运行指南.md)
- [系统前后端全面修复与优化](docs/系统前后端全面修复与优化.md)
- [技术栈设计与架构说明](docs/技术栈设计与架构说明.md)
- [工程骨架说明](docs/工程骨架说明.md)
- [前端页面说明文档](docs/前端页面说明文档.md)
- [后端统一采集与双配置使用说明](docs/后端统一采集与双配置使用说明.md)
- [开发日志](docs/log.md)

## 7. 建议开发顺序

1. 后端 `python run.py`，确认 health / flights / datahub。
2. 前端 `npm run dev`，确认 WS 与地图渲染。
3. 配置天地图应用 Key、核实当前服务审图信息，以及按需配置航班数据 API Key 和 FR24 Worker。
4. `npm run build` 部署前端；后端 `0.0.0.0:8000` + CORS 含 Pages 域名。
