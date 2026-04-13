# Sky-Trace

Sky-Trace是一个面向课程大作业的航班信息跟踪平台，采用 Qt 桌面壳 + Vue3 可视化界面 + Python 数据服务的混合架构。

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
- 可视化: MapLibre GL JS 或 Leaflet, ECharts
- 数据存储: SQLite

## 2. 快速启动指南

以下为推荐的本地开发流程，按后端 -> 前端顺序执行。

### 2.1 后端启动（Python）

1. 进入后端目录

	cd server

2. 创建虚拟环境

	python -m venv .venv

3. 激活虚拟环境（Windows）

	.venv\\Scripts\\activate

4. 安装依赖

	pip install -r requirements.txt

5. 启动服务（示例）

	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

### 2.2 前端启动（Vue3）

1. 进入前端目录

	cd client

2. 安装依赖

	npm install

3. 启动开发服务器

	npm run dev

4. 构建生产资源

	npm run build

## 3. 项目架构简述

Sky-Trace 采用三层协作：

- client（Vue）负责地图、航班轨迹、数据面板等前端 UI 交互。
- server（Python）负责航班数据采集、清洗、缓存与接口服务。
- desktop（Qt）作为桌面应用壳层，加载前端页面并管理本地系统能力。

通信方式：

- client <-> server:
  - HTTP 用于查询与统计
  - WebSocket 用于实时航班增量推送
- desktop <-> client:
  - Qt WebChannel 用于窗口控制、配置读写、导出等本地能力调用
- desktop <-> server:
  - Qt 可拉起或监控后端进程，统一管理启动顺序与健康状态

## 4. 文档导航

- 技术栈与架构说明: docs/技术栈设计与架构说明.md
- 协作规范与工作流: docs/协作开发规范与工作流.md
- 工程骨架说明: docs/工程骨架说明.md
- 启动说明与运行指南: docs/启动说明与运行指南.md
- API接口测试记录与结果汇总: docs/API接口测试记录与结果汇总.md
- 后端数据可视化与字段说明: docs/后端数据可视化与字段说明.md
- 后端统一采集与双配置使用说明: docs/后端统一采集与双配置使用说明.md
- 课程报告要求: docs/大作业报告要求.md

## 5. 建议开发顺序

1. 后端先提供最小可用接口（航班列表 + 实时推送）。
2. 前端对接地图展示与基础筛选。
3. Qt 壳层集成前端构建产物并打通本地能力。
4. 联调后补充回放、统计和异常检测。
