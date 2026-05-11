# Sky-Trace

Sky-Trace 是一个面向课程大作业的航班信息跟踪平台，采用 **Gitee/GitHub Pages 静态前端 + 云服务器后端** 的公网可访问架构。

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
- 部署: Gitee Pages / GitHub Pages（前端），云服务器（后端）

---

## 2. 系统架构

```
┌─────────────────────────────────────────────┐
│         前端（Vue3 + TypeScript + Vite）      │
│  构建后部署至 Gitee Pages / GitHub Pages      │
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

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

#### 3.1.1 配置 API Key

```powershell
copy .env.development.example .env
```

用编辑器打开 `server/.env`，填写以下四个占位符：

| 字段                                          | 申请地址                                                               |
| --------------------------------------------- | ---------------------------------------------------------------------- |
| `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` | https://opensky-network.org → Account → API Clients → 创建客户端后复制 |
| `OPENWEATHER_API_KEY`                         | https://openweathermap.org/api                                         |
| `AIRLABS_API_KEY`                             | https://airlabs.co/                                                    |

> `.env` 已在 `.gitignore` 中排除，不会被提交。  
> 请勿在可提交文件（如 `.env.development.example`）中填写真实 Key。

#### 3.1.2 启动服务

```powershell
# 本地开发
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 云服务器部署（监听公网所有接口）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

验证地址：`http://<服务器IP>:8000/api/v1/health`

### 3.2 前端启动（Vue3）

```powershell
cd client
npm install
npm run dev     # 开发服务器：http://localhost:5173
npm run build   # 生产构建，产物在 dist/（可直接部署至 Pages）
```

前端通过 `.env` 文件配置后端地址：
```
VITE_API_BASE_URL=http://<云服务器IP>:8000
VITE_MAPTILER_KEY=<MapTiler API Key>
```

---

## 4. 后端数据采集架构

Sky-Trace 后端使用**三层统一采集管道**，前端不直接调用第三方 API：

| 层     | 数据源          | 内容                   | 采集频率              |
| ------ | --------------- | ---------------------- | --------------------- |
| 实时层 | OpenSky Network | 全球航班位置/速度/高度 | 90 秒/次（~960次/日） |
| 环境层 | OpenWeather     | 20 全球枢纽天气 + AQI  | 5 分钟/次，并发拉取   |
| 商业层 | AirLabs         | 航班号/机型/起降机场   | 每日 1 次批量         |

### 4.1 主要 API 端点

| 端点                              | 说明                                                              |
| --------------------------------- | ----------------------------------------------------------------- |
| `GET /api/v1/flights`             | 航班列表                                                          |
| `GET /api/v1/datahub/status`      | 三层采集状态                                                      |
| `GET /api/v1/datahub/weather`     | 20 枢纽天气（IATA 键字典）                                        |
| `GET /api/v1/datahub/air_quality` | 20 枢纽 AQI + 污染物                                              |
| `GET /api/v1/datahub/snapshot`    | 聚合快照（status + flights + weather + air_quality + commercial） |
| `WS  /api/v1/ws/flights`          | 实时推送 WebSocket                                                |

---

## 5. 项目架构简述

- **client（Vue）**：地图、航班轨迹、数据面板等 UI 交互，构建后部署至 Gitee/GitHub Pages
- **server（Python）**：航班数据采集、清洗、缓存与接口服务，部署至云服务器

## 6. 文档导航

- 技术栈与架构说明: docs/技术栈设计与架构说明.md
- 协作规范与工作流: docs/协作开发规范与工作流.md
- 工程骨架说明: docs/工程骨架说明.md
- 启动说明与运行指南: docs/启动说明与运行指南.md
- API接口测试记录与结果汇总: docs/API接口测试记录与结果汇总.md
- 后端数据可视化与字段说明: docs/后端数据可视化与字段说明.md
- 后端统一采集与双配置使用说明: docs/后端统一采集与双配置使用说明.md
- 开发日志: docs/log.md
- 课程报告要求: docs/大作业报告要求.md

## 7. 建议开发顺序

1. 后端先提供最小可用接口（航班列表 + 实时推送）。
2. 前端对接地图展示与基础筛选。
3. 联调后补充回放、统计和异常检测。
4. 前端 `npm run build` 产物部署至 Gitee/GitHub Pages，后端部署至云服务器。
