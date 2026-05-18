# Sky-Trace

Sky-Trace 是一个面向课程大作业的航班信息跟踪平台，采用 **Cloudflare Pages 静态前端 + 云服务器 FastAPI 后端** 的公网可访问架构

## 1. 技术栈说明

### 1.1 版本基线
- Python: 3.10+
- Node.js: 20 LTS+
- npm: 10+

### 1.2 核心组件
- 后端服务: FastAPI, Uvicorn, aiohttp, APScheduler
- 前端界面: Vue3, TypeScript, Vite, Pinia
- 可视化: MapLibre GL JS, ECharts
- 数据存储: SQLite
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
验证：`http://127.0.0.1:8000/api/v1/health` → `{"status":"ok","db":"ok"}`。

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
npm run dev     # 开发服务器：http://localhost:5173
npm run build   # 生产构建，产物在 dist/（可直接部署至 Pages）
```

本地开发通常使用 `client/.env.development`（已含 `VITE_API_BASE_URL`、`VITE_WS_URL`）。  
生产构建前改为公网后端地址，例如：

```
VITE_API_BASE_URL=http://<云服务器IP>:8000/api/v1
VITE_WS_URL=ws://<云服务器IP>:8000/api/v1/ws/flights
```

---

## 4. 后端数据采集架构

Sky-Trace 后端使用**三层统一采集管道**，前端不直接调用第三方 API：

| 层     | 数据源          | 内容                                      | 采集频率（开发档）   |
| ------ | --------------- | ----------------------------------------- | -------------------- |
| 实时层 | OpenSky Network | 全球航班位置/速度/高度/机型类别           | 90 秒/次             |
| 环境层 | OpenWeather     | DB 枢纽天气 + AQI + **GRD 5° 动态网格**   | 300 秒/次            |
| 商业层 | AirLabs + FR24  | 航班号/起降机场/机型/航司（FR24 后台补） | 86400 秒 + 后台循环 |

### 4.1 主要 API 端点

| 端点                              | 说明                                                              |
| --------------------------------- | ----------------------------------------------------------------- |
| `GET /api/v1/flights`             | 航班列表                                                          |
| `GET /api/v1/weather-grid`        | 活跃 5° 天气网格单元（GRD）                                       |
| `GET /api/v1/playback`            | 历史回放帧                                                        |
| `GET/PUT /api/v1/places/names`    | 地名简繁缓存同步                                                  |
| `GET /api/v1/datahub/status`      | 三层采集状态                                                      |
| `GET /api/v1/datahub/weather`     | 枢纽 + GRD 天气缓存                                               |
| `GET /api/v1/datahub/air_quality` | 枢纽 AQI + 污染物                                                 |
| `GET /api/v1/datahub/snapshot`    | 聚合快照                                                          |
| `WS  /api/v1/ws/flights`          | 实时推送 WebSocket（广播节流 ≥2s）                                |

---

## 5. 项目架构简述

- **client（Vue）**：地图 / 统计 / 回放三页，MapLibre + Pinia，构建后部署至 Cloudflare Pages
- **server（Python）**：统一采集管道、SQLite 持久化、WS 与 REST，部署至云服务器

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
3. 配置 API Key 与（可选）FR24 Worker、MapTiler。
4. `npm run build` 部署前端；后端 `0.0.0.0:8000` + CORS 含 Pages 域名。
