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