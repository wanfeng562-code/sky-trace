## 4.27
1. 更新 `.gitignore`，忽略 `server/data/*.db`、`server/data/*.db-wal`、`server/data/*.db-shm` 等 SQLite 数据库相关文件，避免本地运行数据被意外提交。
2. 合并同学前端提交到主分支（Merge branch 'main' of remote）。
3. **OpenSky 认证切换至 OAuth2 Client Credentials**：
   - OpenSky 于 2024 年废弃 Basic Auth，旧 USERNAME/PASSWORD 被当作匿名请求处理（额度降至 400 点/日，全球模式下约 100 次即耗尽）。
   - `config.py` 新增 `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` 配置项。
   - `unified_pipeline.py` 新增 `_get_opensky_auth()`，优先使用 Bearer Token（自动缓存与续期），降级链：OAuth2 → Basic Auth → 匿名。
   - 每次请求记录 `X-Rate-Limit-Remaining` 响应头，启动时在日志输出认证档位警告。
   - `.env` / `.env.development.example` 同步更新，新增 OAuth2 字段说明，移除废弃 Basic Auth 字段。
4. **地图视觉全面升级**（`MapView.vue`）：
   - 底图切换为 **OpenFreeMap liberty**（矢量瓦片，高质量、无需 API Key）。
   - 新增 **AWS Terrarium DEM hillshade** 地形晕渲图层（`hillshade-intensity: 0.35`）。
   - 飞机图标改为 SVG（`plane.svg` 飞行中 / `plane_ground.svg` 地面），通过 HTMLImageElement → Canvas → ImageData 加载，兼容所有浏览器。
   - 地名标注改为**双语**（英文 + 简体中文 `name:zh-Hans` 优先，无繁体混入）。
   - 机场圆点与标签图层移除 `minzoom` 限制，初始加载即可见。
   - 修复图层 z-order：机场 → 高亮机场 → 选中光晕 → 航迹线 → **飞机图标**（最顶层）。
5. **后端 Bug 修复**：
   - 修复 `interval_seconds()` 在 dev 模式下实际返回 30s（`DEV_REALTIME_INTERVAL_SECONDS`）而非预期 90s（`DEV_REALTIME_IDLE_INTERVAL_SECONDS`）的问题。
   - 移除 OpenSky 请求失败时的指数退避逻辑，改为立即 fallback 到 mock 数据。

---

## 4.26
前端（kexiao123）完成航班交互模块全链路：

1. **类型系统扩展**（`types/flight.ts`）
   - 新增 `WeatherInfo`（温度/湿度/风速/风向/能见度/天气描述）。
   - 新增 `FlightDetail`（扩展 `FlightBrief`，含起降机场、机型、飞行状态、`departure_weather` / `arrival_weather`）。
   - 新增 `FlightQueryParams`、`FlightStats` 类型定义。

2. **API 层**（`services/api.ts`）
   - `fetchFlights` 增加 `FlightQueryParams` 可选入参，可按呼号/bbox筛选。
   - 新增 `fetchFlightDetail`：调用 `GET /flights/{id}`，自动将 `last_position` 子字段合并到顶层，组件可直接绑定。
   - 新增 `fetchFlightStats`：调用 `GET /flights/summary/stats`。

3. **状态管理**（`stores/flight.ts`）
   - 新增 `searchKeyword`、`filterStatus`（all/airborne/on_ground）、`flightDetail`、`detailLoading`、`wsOnline`。
   - 新增 `filteredFlights` 计算属性（关键字 + 状态双过滤，列表与地图共用）。
   - 新增 `loadFlightDetail`，带竞态保护（仅写入当前选中 ID 的结果）。
   - socket 类型改为 `{ close: () => void } | null`，`disconnectSocket` 在 `onUnmounted` 正确释放。

4. **WS 断线重连**（`services/ws.ts`）
   - 实现退避重连：`[2s, 4s, 8s, 15s, 30s]`，`onStatusChange` 回调同步 `wsOnline` 状态。
   - 对外返回 `{ close() }` 句柄，供页面卸载时调用。

5. **新增组件**
   - `FlightDetailCard.vue`：浮层详情卡片，显示状态标签（飞行中/地面/计划中/已取消）、运动学参数、起降机场、机型；含关闭按钮。
   - `WeatherBlock.vue`：独立 SFC，以表格形式展示 `WeatherInfo` 字段；拆分为独立文件以解决 Vite runtime-only 构建下内联子组件不渲染（仅显示 `<!>`）的问题。

6. **FlightListPanel 升级**
   - 断线离线横幅（`v-if="!wsOnline"`）。
   - 搜索框实时触发 `emit('search', ...)`。
   - 三态筛选 Tab（全部/飞行中/地面）。
   - 空列表文案提示。

7. **MapView 集成**
   - 挂载 `FlightDetailCard`，绑定 `store.flightDetail` + `store.detailLoading`。
   - 统一 `handleSelectFlight(flightId)` 入口：地图点选与列表行选均走同一路径（同时触发 `selectFlight` + `loadFlightDetail`）。

---

## 4.24
1. **新增后端接口（5 个）**：
   - `GET /api/v1/datahub/weather/nearest`：按经纬度查找最近有有效天气缓存的枢纽，返回天气 + AQI，支持自动降级。
   - `GET /api/v1/datahub/quota`：返回各数据源（OpenSky / OpenWeather / AirLabs）今日调用次数与预算。
   - `GET /api/v1/flights/summary/stats`：聚合统计（总数、飞行中、在地面、分类分布、高度分布、速度分布、呼号前缀分布）。
   - `GET /api/v1/playback`：从 SQLite `flight_snapshots` 表按时间段回放历史机队（限 48h/2000 帧，支持 `interval` 采样间隔）。
   - `GET /api/v1/flights/{id}`：详情接口关联起降机场当前天气（`departure_weather` / `arrival_weather`）。

2. **HTTP 代理支持**：
   - `core/config.py` 新增 `http_proxy: str = ""`，读取 `.env` 中的 `HTTP_PROXY`。
   - `unified_pipeline.py` 所有 `aiohttp.session.get()` 调用加 `proxy=self._proxy` 参数，覆盖 OpenSky、OpenWeather（天气 + 空气质量）、AirLabs 五处外部请求。
   - 国内网络可在 `server/.env` 加 `HTTP_PROXY=http://127.0.0.1:7890` 即可走本地代理。

3. **商业层切换至 AirLabs**：
   - 移除 AeroDataBox、Aviationstack 全部采集逻辑与配置。
   - 新增 AirLabs `/flights` 每日一次批量富集（~30 次/月，节省 97% 额度），解析 `{"request":{...},"response":[...]}` 包裹格式。
   - `config.py` 新增 `AIRLABS_API_KEY / airlabs_base_url / airlabs_enrich_ttl_hours`。

4. **OpenSky 全球模式正式启用**：
   - `OPENSKY_BBOX` 置空 → 全球范围采集（~6000 架/次）。
   - 关闭活跃时间窗口，全天匀速 90 秒轮询（约 960 次/日，3840 点/日，余量充足）。
   - OpenSky `extended=1` 新增 `aircraft_category` 字段。
   - 新增 `DEV_REALTIME_DAILY_BUDGET_CALLS` 软截断上限（1000 次）。

5. **环境层重构（20 枢纽并发采集）**：
   - 新增全球 20 个枢纽坐标静态字典，用坐标接口替换城市名接口，精度更高。
   - `asyncio.Semaphore(5)` 并发拉取，单枢纽失败优雅跳过。
   - 空气质量独立缓存 `_air_quality_cache`（IATA 键字典）。
   - 引入 5 秒重试机制，失败枢纽自动重试一次，成功率从 15/20 提升至 17-18/20。

6. **SQLite 扩展**：
   - 新增 `flight_snapshots` 表（含时间戳索引），支持快照保存、24h TTL 自动清理及回放查询。

7. **日志增强**：
   - OpenSky 回退 mock 时输出 WARNING（不再静默），前缀 `[ExceptionClassName]`，空消息回退显示类名。

---

## 4.22
1. 完成后端全部六项遗留功能：
	- SQLite 持久化层（`db.py`）：建立 `flights`、`tracks`、`flight_details_extra` 三张表，WAL 模式，异步 aiosqlite 驱动。
	- `FlightStore` 重写：航班快照 / 轨迹写入 SQLite；`get_flight()` 从 `flight_details_extra` 自动拼装真实起降机场、机型、状态字段；`get_track()` 支持 `since/until` 时间段查询，回退内存兜底。
	- `BroadcastManager`：进程级 WebSocket 连接注册表，每次 realtime 采集后事件驱动广播全量快照到所有已连接客户端。
	- WebSocket 改为事件驱动：连接时立刻推送初始快照，后续由 pipeline broadcast 驱动；保留心跳 ping 保活；不再每 2 秒全量轮询。
	- `/api/v1/flights` 新增筛选参数：`callsign`（大小写不敏感子串）、`lat_min/lat_max/lon_min/lon_max`（视口过滤）。
	- `/api/v1/flights/{id}/track` 新增 `since/until` ISO 8601 时间段参数，支持历史轨迹回放查询。
2. 商业数据对接激活：
	- 将 API Key 填入 `server/.env`，环境层 / 商业层从 skip 变为真实请求。
	- AeroDataBox 从静态 `TEST_PATH` 改为动态按当前时间构造最近 12 小时窗口。
	- `_enrich_flight_details_from_commercial()` 解析 AeroDataBox arrivals/departures 与 Aviationstack data，写入 `flight_details_extra`，航班详情从此有真实起降机场和机型。
3. `/api/v1/health` 增加 SQLite 连通性检查，返回 `{"db": "ok"}`。
4. 新增 `aiosqlite==0.20.0` 到 `requirements.txt`，已安装验证。
5. 启动验证：OpenSky 96 架、商业数据 2 条记录，均写入 SQLite，服务无错误退出。

## 4.12
1. 完成报告要求文档，相关项目文档（架构说明、协作规范、启动指南）。
2. 建立系统代码骨架，定义模块划分、接口契约和核心数据模型。

## 4.13
1. 完成相关 API 搜索与接口测试闭环，测试结果达到 7/7 通过（R3）。
2. 增加后端可视化与调试能力：
3. 后端架构升级为“统一采集 + 统一缓存 + 统一下发”：
	- 新增统一采集管道 `unified_pipeline`
	- 新增聚合接口 `/api/v1/datahub/status|weather|commercial|snapshot`
	- 前端对接策略调整为“优先访问后端聚合接口，不直接请求第三方”。
4. 完成双配置机制：
	- `APP_PROFILE=development|release`
	- 默认开发配置。
5. 开发档位 OpenSky 轮询策略调整并落地：
	- 08:00 起活跃时段 15s
	- 非活跃时段 40s
	- 按 4000 次/日预算自动计算活跃窗口，当前结束时间约 20:16。
6. 文档同步：更新测试记录、启动指南、技术栈说明、工程骨架、实现思路与进度计划文档。