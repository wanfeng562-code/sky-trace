# Sky-Trace

Sky-Trace 是一个面向课程大作业的航班信息跟踪平台，采用 Qt 桌面壳 + Vue3 可视化界面 + Python 数据服务的混合架构。

## 1. 技术栈说明

### 1.1 版本基线
- Python: 3.10+
- Node.js: 20 LTS+
- npm: 10+
- Qt for Python: PySide6 6.7+

### 1.2 核心组件
- 桌面端: PySide6, Qt WebEngine, Qt WebChannel
- 后端服务: FastAPI, Uvicorn, aiohttp, APScheduler
- 前端界面: Vue3, TypeScript, Vite, Pinia
- 可视化: MapLibre GL JS / Leaflet, ECharts
- 数据存储: SQLite

---

## 2. 快速启动指南

按后端 → 前端的顺序执行。

### 2.1 后端启动（Python）

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

#### 2.1.1 配置 API Key

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

#### 2.1.2 启动服务

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证地址：`http://127.0.0.1:8000/api/v1/health`

### 2.2 前端启动（Vue3）

```powershell
cd client
npm install
npm run dev     # 开发服务器：http://localhost:5173
npm run build   # 生产构建
```

---

## 3. 后端数据采集架构

Sky-Trace 后端使用**三层统一采集管道**，前端不直接调用第三方 API：

| 层     | 数据源          | 内容                   | 采集频率              |
| ------ | --------------- | ---------------------- | --------------------- |
| 实时层 | OpenSky Network | 全球航班位置/速度/高度 | 90 秒/次（~960次/日） |
| 环境层 | OpenWeather     | 20 全球枢纽天气 + AQI  | 5 分钟/次，并发拉取   |
| 商业层 | AirLabs         | 航班号/机型/起降机场   | 每日 1 次批量         |

### 3.1 主要 API 端点

| 端点                              | 说明                                                              |
| --------------------------------- | ----------------------------------------------------------------- |
| `GET /api/v1/flights`             | 航班列表                                                          |
| `GET /api/v1/datahub/status`      | 三层采集状态                                                      |
| `GET /api/v1/datahub/weather`     | 20 枢纽天气（IATA 键字典）                                        |
| `GET /api/v1/datahub/air_quality` | 20 枢纽 AQI + 污染物                                              |
| `GET /api/v1/datahub/snapshot`    | 聚合快照（status + flights + weather + air_quality + commercial） |
| `WS  /api/v1/ws/flights`          | 实时推送 WebSocket                                                |

---

## 4. 项目架构简述

- **client（Vue）**：地图、航班轨迹、数据面板等 UI 交互
- **server（Python）**：航班数据采集、清洗、缓存与接口服务
- **desktop（Qt）**：桌面应用壳层，加载前端页面并管理本地系统能力

通信方式：
- client ↔ server：HTTP（查询/统计）+ WebSocket（实时推送）
- desktop ↔ client：Qt WebChannel（窗口控制、配置读写、导出等）
- desktop ↔ server：Qt 进程管理（拉起/监控后端健康状态）

## 4. 文档导航

- 技术栈与架构说明: docs/技术栈设计与架构说明.md
- 协作规范与工作流: docs/协作开发规范与工作流.md
- 工程骨架说明: docs/工程骨架说明.md
- 启动说明与运行指南: docs/启动说明与运行指南.md
- API接口测试记录与结果汇总: docs/API接口测试记录与结果汇总.md
- 后端数据可视化与字段说明: docs/后端数据可视化与字段说明.md
- 后端统一采集与双配置使用说明: docs/后端统一采集与双配置使用说明.md
- 开发日志: docs/log.md
- 课程报告要求: docs/大作业报告要求.md

## 5. 建议开发顺序

1. 后端先提供最小可用接口（航班列表 + 实时推送）。
2. 前端对接地图展示与基础筛选。
3. Qt 壳层集成前端构建产物并打通本地能力。
4. 联调后补充回放、统计和异常检测。
