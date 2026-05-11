# 前端地图与地理可视化 (Vue 侧)

## OpenSky Network(实时位置接口)

    - 注册后免费，频率限制较宽松。(每日四千次调用)
    - 24小时调用则21.6s轮询一次，12小时调用则10.8s轮询一次，能够满足实时性需求。
    - 能够获取实时状态、位置更新、历史轨迹。
    - 链接：https://github.com/openskynetwork/opensky-api

## FlightRadar24 补充数据源（ddima16-flightradarapi fork）
    - FlightRadar24 的非官方 Python SDK（DimaD16 fork），支持 Cloudflare Worker 代理绕过 403
    - 原版：https://github.com/JeanExtreme002/FlightRadarAPI
    - Fork（当前使用）：https://github.com/DimaD16/FlightRadarAPI
    - 安装：`pip install ddima16-flightradarapi`（import 路径与原版相同：`from FlightRadar24 import FlightRadar24API`）
    - 初始化：`FlightRadar24API(proxy_url="https://<your-worker>.workers.dev/?url=")`
    - **Cloudflare Worker 代理**：FlightRadar24 对直接请求返回 403，需部署免费 Worker 代理
      - 部署源：https://github.com/DimaD16/cloudflare-workers-fr24-proxy
      - 一键部署：https://deploy.workers.cloudflare.com/?url=https://github.com/DimaD16/cloudflare-workers-fr24-proxy/tree/main
      - 免费额度：100,000 次/天（Cloudflare Workers 免费计划）
    - 通过解析 FlightRadar24 的数据提供全球航班位置，作为 OpenSky/AirLabs 的补充源
    - 配置：在 `server/.env` 中填写 `FR24_PROXY_URL`；留空则自动禁用该数据源

## AeroDataBox(航班详情与搜索接口)(limit)

    - 每月约 600 次调用(通过rapidapi，分层级限制调用)
    - 获取航班延误统计、航站楼/登机口、机型参数。
    - 链接：https://aerodatabox.com/
    - ![alt text](image.png)

## FlightAware (AeroAPI v3)
行业标杆，数据极其精准。
免费额度：个人/学术账户每月有 $5.00 的免费额度。
字段对应：提供非常详尽的 origin, destination, aircraft_type, status。
优点：它提供的 ident（航班号）匹配率非常高。
但是只能选择一个空域

## Aviationstack(limit)

    - 免费的每月100次调用
    - 获取实时航班查询、历史记录、航线信息。
    - 链接：https://github.com/apilayer/aviationstack

## AirLabs
一个相对小众但对开发者很友好的数据源。
免费额度：每月 1,000 次请求。
特点：它的 flights 接口可以直接返回当前正在飞行的航班详情，非常适合用来补全 OpenSky 的数据。
似乎也有航班位置数据，考虑作为补充数据源。

## Mapbox(地图底图接口)

    - 用于网页上交互式、可自定义矢量地图的 JavaScript 库
    - 链接：https://github.com/mapbox/mapbox-gl-js
    - 当前状态：由于IP限制导致无法完成账号注册，暂不采用并移出接口测试清单。

## Leaflet(地图底图接口)

    - 用于构建强大的交互式地图，注重简洁、性能和可用性。
    - 链接：https://github.com/Leaflet/Leaflet

## CesiumJS(地图底图接口)

    - 用于创建 3D 地球和地图的 JavaScript 库，用于后续的三维可视化开发
    - 链接：https://github.com/CesiumGS/cesium

## AntV L7(地图底图接口)

    - 基于 WebGL 的开源大规模地理空间数据可视分析引擎
    - 链接：https://github.com/antvis/L7

## Turfjs(地理空间分析库)

    - 用于地理空间分析和处理的 JavaScript 库，适合航迹分析、缓冲区计算等。
    - 链接：https://github.com/Turfjs/turf

# 后端增强与实时通信 (Python / Qt 侧)

## WebSocket (FastAPI / Flask-SocketIO)：

    - 实现数据的实时推送。
    - 当 Python 后端从 API 拿到新的位置时，立即推给 Vue 前端，避免页面频繁刷新。

## Aiohttp / HTTPX：

    - 异步 HTTP 客户端库，适合在 FastAPI 中使用。
    - 用于定时从第三方 API 获取数据，支持高并发和超时控制。

# 可视化图表 (数据分析)

## ECharts(Vue-ECharts)：

    - 强大的开源可视化库，适合展示统计数据、趋势图等。
    - 可以在 Vue 中集成，展示航班延误统计、速度分布等。
    - 适合做航班延误率的雷达图、不同航司飞行总里程的柱状图等。

## Canvas-Gauges：

    - 用于创建仪表盘风格的图表，适合展示速度、高度等实时数据。
    - 可以在 Vue 中集成，展示航班当前速度、飞行高度等信息。
    - 适合模拟飞机的高度计、速度仪等物理仪表。

# UI与其他素材
## FontAwesome(图标库)
## Iconfont(阿里巴巴矢量图标库)
plane, take-off, landing, globe, location, speedometer, altitude, etc.

## OpenWeatherMap(天气数据接口)

    - 获取航班所在位置的实时天气数据，增强可视化效果。
    - 链接：https://openweathermap.org/

