# Sky-Trace 第三方 API 参考手册

> 整理时间：2025-06 / 更新：2026-05  
> 覆盖范围：OpenSky Network、OpenWeatherMap、AirLabs v9、**FlightRadar24 (ddima16-flightradarapi)**、**MapTiler Cloud**、**Stadia Maps**  
> 文档目的：汇总所有可调用端点、字段说明、额度限制，并标注对本项目的潜在价值

---

## 目录

1. [OpenSky Network API](#1-opensky-network-api)
2. [OpenWeatherMap API](#2-openweathermap-api)
3. [AirLabs API v9](#3-airlabs-api-v9)
4. [FlightRadar24 (ddima16-flightradarapi)](#4-flightradar24-ddima16-flightradarapi)
5. [MapTiler Cloud API（地图底图，主）](#5-maptiler-cloud-api地图底图主)
6. [Stadia Maps API（地图底图，备）](#6-stadia-maps-api地图底图备)
7. [新机会与建议](#7-新机会与建议)

---

## 1. OpenSky Network API

**根地址：** `https://opensky-network.org/api`  
**认证方式：** OAuth2 Client Credentials（已废弃 Basic Auth）  
**令牌端点：** `https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token`  
令牌有效期 30 分钟，请求头：`Authorization: Bearer <token>`

### 1.1 额度说明（信用点系统）

三类端点（`/states/*`、`/tracks/*`、`/flights/*`）各有独立配额桶，互不影响。

| 用户类型                | 配额   | 周期   |
| ----------------------- | ------ | ------ |
| 匿名（按 IP）           | 400    | 每日   |
| 注册用户                | 4,000  | 每日   |
| 活跃馈送者（≥30% 在线） | 8,000  | 每日   |
| 授权用户                | 14,400 | 每小时 |

**`/states/all` 消耗点数（按 bbox 面积）：**

| 面积                   | 消耗 |
| ---------------------- | ---- |
| ≤25 sq° 或仅序列号查询 | 1    |
| 25–100 sq°             | 2    |
| 100–400 sq°            | 3    |
| >400 sq° 或全球        | 4    |

> 我们 BBOX `21°–26°N, 108°–116°E` = 5°×8° = 40 sq° → **每次调用消耗 2 点**

**`/flights/*` 和 `/tracks/*` 消耗点数（按跨越的日历天数）：**

| 时间跨度    | 消耗      |
| ----------- | --------- |
| 实时 / <24h | 4         |
| 1–2 天      | 30        |
| 3–10 天     | 60×N      |
| 11–25 天    | 120–480×N |

响应头 `X-Rate-Limit-Remaining` 显示剩余额度；超限返回 `429`，`X-Rate-Limit-Retry-After-Seconds` 指示等待秒数。

---

### 1.2 `GET /states/all` — 全网状态向量（**当前已用**）

**参数：**

| 参数                      | 类型   | 说明                              |
| ------------------------- | ------ | --------------------------------- |
| `time`                    | int    | Unix 时间戳（可选，匿名用户忽略） |
| `icao24`                  | string | 过滤特定 ICAO24 地址，可多次      |
| `lamin/lamax/lomin/lomax` | float  | WGS84 bounding box                |
| `extended`                | int    | 设为 1 时返回 category 字段       |

**响应 `states` 数组字段（按索引）：**

| 索引 | 字段              | 类型   | 说明                                |
| ---- | ----------------- | ------ | ----------------------------------- |
| 0    | `icao24`          | string | ICAO 24bit 地址（hex）              |
| 1    | `callsign`        | string | 呼号（8字符，可为 null）            |
| 2    | `origin_country`  | string | 根据 ICAO 地址推断的国家            |
| 3    | `time_position`   | int    | 最后位置更新的 Unix 时间戳          |
| 4    | `last_contact`    | int    | 最后接收信号的 Unix 时间戳          |
| 5    | `longitude`       | float  | WGS-84 经度                         |
| 6    | `latitude`        | float  | WGS-84 纬度                         |
| 7    | `baro_altitude`   | float  | 气压高度（米）                      |
| 8    | `on_ground`       | bool   | 是否在地面                          |
| 9    | `velocity`        | float  | 地速（m/s）                         |
| 10   | `true_track`      | float  | 航向（度，顺时针，北=0）            |
| 11   | `vertical_rate`   | float  | 垂直速率（m/s，正=爬升）            |
| 12   | `sensors`         | int[]  | 贡献接收器 ID                       |
| 13   | `geo_altitude`    | float  | 几何高度（米）                      |
| 14   | `squawk`          | string | 应答机代码                          |
| 15   | `spi`             | bool   | 特殊用途指示器                      |
| 16   | `position_source` | int    | 0=ADS-B, 1=ASTERIX, 2=MLAT, 3=FLARM |
| 17   | `category`        | int    | 飞机类别（需 extended=1）           |

**`category` 枚举值（extended=1）：**

| 值  | 类别                     |
| --- | ------------------------ |
| 0   | 无信息                   |
| 2   | 轻型（<15500 lbs）       |
| 3   | 小型（15500–75000 lbs）  |
| 4   | 大型（75000–300000 lbs） |
| 5   | 高尾流大型（如 B-757）   |
| 6   | 重型（>300000 lbs）      |
| 7   | 高性能（>5g，400kts）    |
| 8   | 旋翼机                   |
| 14  | 无人机（UAV）            |

---

### 1.3 `GET /states/own` — 自有传感器状态向量

无额度限制（需认证）。参数同 `/states/all`，多支持 `serials`（按接收器过滤）。

---

### 1.4 `GET /flights/all` — 时间段内全部航班

| 参数    | 必须 | 说明                            |
| ------- | ---- | ------------------------------- |
| `begin` | ✅    | 开始 Unix 时间戳                |
| `end`   | ✅    | 结束 Unix 时间戳（区间 ≤2小时） |

响应为 JSON 数组，每条航班含 `icao24`、`callsign`、`estDepartureAirport`、`estArrivalAirport`、起止时间等字段。  
⚠️ 仅前一天及更早数据（批次处理，非实时）。消耗 4 点（实时）。

---

### 1.5 `GET /flights/aircraft` — 按飞机查航班历史

| 参数     | 必须 | 说明                    |
| -------- | ---- | ----------------------- |
| `icao24` | ✅    | ICAO24 地址（小写）     |
| `begin`  | ✅    | 开始时间戳              |
| `end`    | ✅    | 结束时间戳（区间 ≤2天） |

---

### 1.6 `GET /flights/arrival` — 按机场查到达航班

| 参数      | 必须 | 说明                    |
| --------- | ---- | ----------------------- |
| `airport` | ✅    | 机场 ICAO 代码（大写）  |
| `begin`   | ✅    | 开始时间戳              |
| `end`     | ✅    | 结束时间戳（区间 ≤2天） |

---

### 1.7 `GET /flights/departure` — 按机场查出发航班

参数同 `/flights/arrival`。区间需跨越至少2天（UTC）。

---

### 1.8 `GET /tracks/all` — 按飞机查轨迹（实验性）

| 参数     | 必须 | 说明                               |
| -------- | ---- | ---------------------------------- |
| `icao24` | ✅    | ICAO24 地址                        |
| `time`   | ✅    | 0=获取实时轨迹；或航班中任意时间戳 |

**响应字段：**

| 字段        | 说明                                                         |
| ----------- | ------------------------------------------------------------ |
| `icao24`    | ICAO 地址                                                    |
| `startTime` | 第一个航点的时间戳                                           |
| `endTime`   | 最后一个航点的时间戳                                         |
| `callsign`  | 呼号                                                         |
| `path`      | 航点数组 `[time, lat, lon, baro_alt, true_track, on_ground]` |

限制：最多 30 天历史数据；实验性端点，可能随时停用。  
消耗 4 点（实时轨迹）。

---

## 2. OpenWeatherMap API

**根地址：** `https://api.openweathermap.org/data/2.5/`  
**认证方式：** `appid=YOUR_API_KEY`（查询参数）  
**免费配额：** 1,000 次/分钟，60 次/分钟（具体视套餐）  
**通用参数：**

| 参数    | 说明                                                           |
| ------- | -------------------------------------------------------------- |
| `units` | `standard`（开氏度）/ `metric`（摄氏度）/ `imperial`（华氏度） |
| `lang`  | 语言代码，如 `zh_cn`                                           |
| `mode`  | `json`（默认）/ `xml`                                          |

---

### 2.1 `GET /weather` — 当前天气（**当前已用**）

```
https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=metric
```

**响应字段：**

| 字段                    | 说明                            |
| ----------------------- | ------------------------------- |
| `coord.lon / .lat`      | 经纬度                          |
| `weather[].id`          | 天气状况代码                    |
| `weather[].main`        | 天气组（Rain, Snow, Clouds 等） |
| `weather[].description` | 详细描述                        |
| `weather[].icon`        | 图标 ID                         |
| `main.temp`             | 气温（metric: °C）              |
| `main.feels_like`       | 体感温度                        |
| `main.pressure`         | 气压（hPa）                     |
| `main.humidity`         | 湿度（%）                       |
| `main.sea_level`        | 海平面气压（hPa）               |
| `main.grnd_level`       | 地面气压（hPa）                 |
| `visibility`            | 能见度（米，最大 10000）        |
| `wind.speed`            | 风速（m/s）                     |
| `wind.deg`              | 风向（度，气象惯例）            |
| `wind.gust`             | 阵风（m/s）                     |
| `clouds.all`            | 云量（%）                       |
| `rain.1h`               | 最近1小时降雨量（mm）           |
| `snow.1h`               | 最近1小时降雪量（mm）           |
| `dt`                    | 数据计算时间（Unix UTC）        |
| `sys.country`           | 国家代码                        |
| `sys.sunrise / .sunset` | 日出/日落时间（Unix UTC）       |
| `timezone`              | UTC 偏移（秒）                  |

---

### 2.2 `GET /forecast` — 5天/3小时预报

```
https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={key}&units=metric&cnt={n}
```

返回最多 40 个时间点（5天×8个/天），每点间隔3小时。

**`list[]` 核心字段：**

| 字段         | 说明                       |
| ------------ | -------------------------- |
| `dt`         | 预报时间（Unix UTC）       |
| `dt_txt`     | 预报时间（ISO 字符串）     |
| `main.*`     | 同当前天气 main 字段       |
| `weather[]*` | 同当前天气 weather 字段    |
| `wind.*`     | 同当前天气 wind 字段       |
| `clouds.all` | 云量                       |
| `visibility` | 能见度（米）               |
| `pop`        | 降水概率（0~1）            |
| `rain.3h`    | 过去3小时降雨量（mm）      |
| `snow.3h`    | 过去3小时降雪量（mm）      |
| `sys.pod`    | 时段（`d`=白天, `n`=夜晚） |

可选参数 `cnt` 限制返回时间点数量。

---

### 2.3 `GET /air_pollution` — 当前空气质量（**免费可用**）

```
http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={key}
```

**响应字段：**

| 字段                      | 说明                                         |
| ------------------------- | -------------------------------------------- |
| `list[].main.aqi`         | AQI 综合指数：1=优，2=良，3=中，4=差，5=极差 |
| `list[].components.co`    | CO 浓度（μg/m³）                             |
| `list[].components.no`    | NO 浓度（μg/m³）                             |
| `list[].components.no2`   | NO₂ 浓度（μg/m³）                            |
| `list[].components.o3`    | O₃ 浓度（μg/m³）                             |
| `list[].components.so2`   | SO₂ 浓度（μg/m³）                            |
| `list[].components.pm2_5` | PM2.5 浓度（μg/m³）                          |
| `list[].components.pm10`  | PM10 浓度（μg/m³）                           |
| `list[].components.nh3`   | NH₃ 浓度（μg/m³）                            |
| `list[].dt`               | Unix 时间戳（UTC）                           |

**AQI 各污染物阈值（OpenWeather 标准）：**

| 级别 | AQI | SO₂     | NO₂     | PM10    | PM2.5 | O₃      | CO          |
| ---- | --- | ------- | ------- | ------- | ----- | ------- | ----------- |
| 优   | 1   | <20     | <40     | <20     | <10   | <60     | <4400       |
| 良   | 2   | 20–80   | 40–70   | 20–50   | 10–25 | 60–100  | 4400–9400   |
| 中   | 3   | 80–250  | 70–150  | 50–100  | 25–50 | 100–140 | 9400–12400  |
| 差   | 4   | 250–350 | 150–200 | 100–200 | 50–75 | 140–180 | 12400–15400 |
| 极差 | 5   | ≥350    | ≥200    | ≥200    | ≥75   | ≥180    | ≥15400      |

### 2.4 `GET /air_pollution/forecast` — 空气质量预报

参数同当前空气质量，返回4天小时级预报数据（字段结构相同）。

### 2.5 `GET /air_pollution/history` — 历史空气质量

```
http://api.openweathermap.org/data/2.5/air_pollution/history?lat={lat}&lon={lon}&start={unix}&end={unix}&appid={key}
```

历史数据从 2020-11-27 起可用。

---

## 3. AirLabs API v9

**根地址：** `https://airlabs.co/api/v9/`  
**认证方式：** `api_key=YOUR_KEY`（查询参数）  
**免费套餐：** 1,000 次/月（**每次 HTTP 请求消耗 1 次，与返回数据量无关**）  
**响应格式：** Free 计划返回 `{"request":{...}, "response":[...]}` 包裹结构

---

### 3.1 `GET /flights` — 实时航班追踪（**当前已用，批量**）

```
https://airlabs.co/api/v9/flights?bbox=21.0,108.0,26.0,116.0&api_key=KEY
```

**bbox 格式：** `SW-lat,SW-lon,NE-lat,NE-lon`（注意：与 OpenSky lamin,lamax,lomin,lomax 顺序不同）

**请求参数：**

| 参数                | 必须 | 说明                                   |
| ------------------- | ---- | -------------------------------------- |
| `api_key`           | ✅    | API Key                                |
| `bbox`              | 可选 | 边界框过滤                             |
| `zoom`              | 可选 | 地图缩放级别 0–11（减少返回密度）      |
| `hex`               | 可选 | 按 ICAO24 过滤                         |
| `reg_number`        | 可选 | 按注册号过滤                           |
| `airline_icao/iata` | 可选 | 按航空公司过滤                         |
| `flight_icao/iata`  | 可选 | 按航班号过滤                           |
| `flight_number`     | 可选 | 按纯数字航班号过滤                     |
| `dep_icao/iata`     | 可选 | 按出发机场过滤                         |
| `arr_icao/iata`     | 可选 | 按到达机场过滤                         |
| `flag`              | 可选 | 按国家 ISO-2 代码过滤                  |
| `_fields`           | 可选 | 指定返回字段（逗号分隔）               |
| `_view`             | 可选 | `object`（默认）或 `array`（节省带宽） |

**响应字段：**

| 字段            | Free 可用 | 说明                                      |
| --------------- | --------- | ----------------------------------------- |
| `hex`           | ✅         | ICAO24 地址                               |
| `reg_number`    |           | 飞机注册号                                |
| `flag`          | ✅         | 国家 ISO-2 代码                           |
| `lat`           | ✅         | 实时纬度                                  |
| `lng`           | ✅         | 实时经度                                  |
| `alt`           |           | 高度（米）                                |
| `dir`           | ✅         | 航向（度）                                |
| `speed`         |           | 水平速度（km/h）                          |
| `v_speed`       |           | 垂直速率（km/h）                          |
| `squawk`        |           | 应答机代码                                |
| `flight_icao`   |           | 航班 ICAO 代码                            |
| `flight_iata`   |           | 航班 IATA 代码                            |
| `flight_number` |           | 纯数字航班号                              |
| `airline_icao`  |           | 航空公司 ICAO                             |
| `airline_iata`  |           | 航空公司 IATA                             |
| `aircraft_icao` | ✅         | 机型 ICAO（如 B738）                      |
| `dep_icao`      |           | 出发机场 ICAO                             |
| `dep_iata`      | ✅         | 出发机场 IATA                             |
| `arr_icao`      |           | 到达机场 ICAO                             |
| `arr_iata`      |           | 到达机场 IATA                             |
| `updated`       |           | 最后信号 Unix 时间戳                      |
| `status`        |           | 航班状态：`scheduled`/`en-route`/`landed` |

---

### 3.2 `GET /flight` — 单条航班详情（**含时刻信息**）

```
https://airlabs.co/api/v9/flight?flight_iata=AA6&api_key=KEY
```

**请求参数：**

| 参数          | 必须   | 说明           |
| ------------- | ------ | -------------- |
| `flight_icao` | 二选一 | 航班 ICAO 代码 |
| `flight_iata` | 二选一 | 航班 IATA 代码 |

> 返回最近一班（实时/已排班/已降落），若需查同号全天多班请用 `/schedules`

**额外响应字段（相比 `/flights`）：**

| 字段                | Free 可用 | 说明                                  |
| ------------------- | --------- | ------------------------------------- |
| `dep_terminal`      |           | 出发航站楼                            |
| `dep_gate`          |           | 出发登机口                            |
| `dep_time`          | ✅         | 出发时间（机场时区）                  |
| `dep_time_ts`       |           | 出发 Unix 时间戳                      |
| `dep_time_utc`      |           | 出发 UTC 时间                         |
| `dep_estimated`     |           | 最新预计出发时间                      |
| `dep_estimated_utc` |           | 最新预计出发 UTC 时间                 |
| `arr_terminal`      |           | 到达航站楼                            |
| `arr_gate`          |           | 到达登机口                            |
| `arr_baggage`       |           | 行李转盘号                            |
| `arr_time`          | ✅         | 到达时间（机场时区）                  |
| `arr_estimated`     |           | 最新预计到达时间                      |
| `duration`          |           | 预计飞行时间（分钟）                  |
| `dep_delayed`       |           | 出发延误（分钟）                      |
| `arr_delayed`       |           | 到达延误（分钟）                      |
| `cs_airline_iata`   |           | 代码共享航空公司 IATA                 |
| `cs_flight_iata`    |           | 代码共享航班 IATA                     |
| `model`             |           | 飞机全型号名称                        |
| `manufacturer`      | ✅         | 制造商                                |
| `type`              |           | 飞机类型（landplane/helicopter 等）   |
| `engine`            |           | 发动机类型（jet/piston/turboprop 等） |
| `engine_count`      |           | 发动机数量                            |
| `built`             |           | 出厂年份                              |
| `age`               |           | 机龄（年）                            |
| `msn`               |           | 制造序列号                            |

---

### 3.3 `GET /schedules` — 机场实时时刻表

```
https://airlabs.co/api/v9/schedules?dep_iata=PEK&api_key=KEY
```

最多返回未来10小时内的航班，实时反映登机口/登机队列状态。

**请求参数（至少提供一个查询条件）：**

| 参数                | 说明                                                   |
| ------------------- | ------------------------------------------------------ |
| `dep_iata/icao`     | 出发机场                                               |
| `arr_iata/icao`     | 到达机场                                               |
| `airline_iata/icao` | 航空公司                                               |
| `flight_icao/iata`  | 具体航班号                                             |
| `limit`             | 最多 50（Free），1000（付费按机场），200（按航空公司） |
| `offset`            | 分页偏移                                               |

**响应字段（含实际时间，比 `/flight` 更全面）：**

| 字段            | Free 可用    | 说明                                      |
| --------------- | ------------ | ----------------------------------------- |
| `dep_time`      | ✅            | 计划出发时间（机场时区）                  |
| `dep_estimated` |              | 预计出发时间                              |
| `dep_actual`    |              | 实际出发时间                              |
| `arr_time`      | ✅            | 计划到达时间                              |
| `arr_estimated` |              | 预计到达时间                              |
| `arr_actual`    |              | 实际到达时间                              |
| `dep_delayed`   |              | 出发延误（分钟）                          |
| `arr_delayed`   |              | 到达延误（分钟）                          |
| `status`        |              | `scheduled`/`cancelled`/`active`/`landed` |
| 其他字段        | 同 `/flight` | 航站楼、登机口、行李转盘等                |

---

### 3.4 `GET /airlines` — 航空公司数据库

```
https://airlabs.co/api/v9/airlines?iata_code=CZ&api_key=KEY
```

**请求参数：** `iata_code`、`icao_code`、`callsign`、`name`、`country_code`、`_fields`

**响应字段：**

| 字段                | Free 可用 | 说明             |
| ------------------- | --------- | ---------------- |
| `name`              | ✅         | 航空公司名称     |
| `iata_code`         | ✅         | IATA 代码        |
| `icao_code`         | ✅         | ICAO 代码        |
| `callsign`          |           | ICAO 呼号        |
| `country_code`      |           | 国家 ISO-2       |
| `is_scheduled`      |           | 是否为定期航班   |
| `is_passenger`      |           | 是否为客运       |
| `is_cargo`          |           | 是否为货运       |
| `is_international`  |           | 是否运营国际航线 |
| `total_aircrafts`   |           | 机队总数         |
| `average_fleet_age` |           | 平均机龄（年）   |
| `accidents_last_5y` |           | 近5年事故次数    |
| `crashes_last_5y`   |           | 近5年坠机次数    |
| `website`           |           | 官网             |

**航空公司 Logo：**
- 中尺寸：`https://airlabs.co/img/airline/m/{IATA}.png`
- 小尺寸：`https://airlabs.co/img/airline/s/{IATA}.png`

---

### 3.5 `GET /airports` — 机场数据库

```
https://airlabs.co/api/v9/airports?iata_code=PEK&api_key=KEY
```

**请求参数：** `iata_code`、`icao_code`、`city_code`、`country_code`、`_fields`

**响应字段：**

| 字段               | Free 可用 | 说明                     |
| ------------------ | --------- | ------------------------ |
| `name`             | ✅         | 机场名称                 |
| `iata_code`        | ✅         | IATA 代码                |
| `icao_code`        | ✅         | ICAO 代码                |
| `lat`              | ✅         | 纬度                     |
| `lng`              | ✅         | 经度                     |
| `alt`              |           | 跑道海拔（英尺）         |
| `city`             |           | 所在城市                 |
| `city_code`        |           | 城市 IATA 代码           |
| `timezone`         |           | 时区（如 Asia/Shanghai） |
| `country_code`     | ✅         | 国家 ISO-2               |
| `names`            |           | 多语言名称 map           |
| `runways`          |           | 跑道数量                 |
| `departures`       |           | 年出发航班总数           |
| `connections`      |           | 连接机场总数             |
| `is_major`         |           | 是否为大都市主要机场     |
| `is_international` |           | 是否提供国际航班         |
| `phone`            |           | 联系电话                 |
| `website`          |           | 官网                     |

---

### 3.6 `GET /routes` — 全球航线数据库（**静态数据**）

```
https://airlabs.co/api/v9/routes?dep_iata=PEK&arr_iata=SHA&api_key=KEY
```

**注意：** 此数据为非实时计划数据，表示航空公司实际运营的航线。结合 `/schedules` 可预测未来排班。

**请求参数（至少提供一个）：** `dep_iata/icao`、`arr_iata/icao`、`airline_iata/icao`、`flight_icao/iata`、`flight_number`  
`limit`：Free 50，付费最多 500；`offset`：分页

**响应字段：**

| 字段                | Free 可用 | 说明                                |
| ------------------- | --------- | ----------------------------------- |
| `airline_icao/iata` | ✅         | 航空公司代码                        |
| `flight_icao/iata`  | ✅         | 航班代码                            |
| `flight_number`     | ✅         | 纯数字航班号                        |
| `dep_iata/icao`     |           | 出发机场                            |
| `dep_time`          |           | 出发时间（机场本地）                |
| `dep_time_utc`      |           | 出发时间（UTC）                     |
| `dep_terminals`     |           | 可能的出发航站楼列表                |
| `arr_iata/icao`     |           | 到达机场                            |
| `arr_time`          |           | 到达时间（机场本地）                |
| `arr_terminals`     |           | 可能的到达航站楼列表                |
| `duration`          |           | 预计飞行时长（分钟）                |
| `days`              |           | 运营日：sun/mon/tue/wed/thu/fri/sat |
| `aircraft_icao`     |           | 最近使用的机型                      |
| `updated`           |           | 最后更新时间                        |

---

### 3.7 其他 AirLabs 端点（参考）

| 端点             | 说明                   | 套餐要求 |
| ---------------- | ---------------------- | -------- |
| `GET /delays` ☆  | 实时延误数据           | 付费     |
| `GET /alert` ✔   | 航班预警订阅           | 有限免费 |
| `GET /nearby`    | 按坐标查附近机场       | 免费     |
| `GET /fleets`    | 机队数据库（机型详情） | 免费     |
| `GET /suggest`   | 名称自动补全建议       | 免费     |
| `GET /cities`    | 城市数据库             | 免费     |
| `GET /countries` | 国家数据库             | 免费     |

---

## 4. FlightRadar24 (ddima16-flightradarapi)

**Python SDK：** [`ddima16-flightradarapi`](https://github.com/dimad16/FlightRadarAPI)（DimaD16 非官方 fork，支持 `proxy_url` 参数）  
**安装：** `pip install ddima16-flightradarapi`  
**认证方式：** 无需 API Key（非官方 SDK，模拟浏览器行为）  
**代理要求：** 直连 `*.flightradar24.com` 在国内受限；需通过 Cloudflare Worker 代理（见 `FR24_PROXY_URL` 配置）  
**地理限制：** 单次 bounding box 查询服务端约限制 1 500 条返回；需分区查询并去重  
**配额限制：** 无官方限制，但高频请求会触发 IP 封禁（403 Forbidden）

---

### 4.1 主要方法

#### `get_flights(bounds=...)` — 分区航班位置列表（**当前已用，实时层第二数据源**）

```python
from FlightRadar24 import FlightRadar24API
fr = FlightRadar24API(proxy_url="https://<worker>.workers.dev/?url=")
zone = {"tl_y": 72.57, "tl_x": -16.96, "br_y": 33.57, "br_x": 53.05}
bounds = fr.get_bounds(zone)
flights = fr.get_flights(bounds=bounds)
```

**返回 `Flight` 对象列表，可用字段（`get_flights()` 基础查询，无需登录）：**

| 字段                       | 类型  | 说明                                     | 商业价值 |
| -------------------------- | ----- | ---------------------------------------- | -------- |
| `id`                       | str   | FR24 内部 Flight ID                      |          |
| `icao_24bit`               | str   | ICAO24 地址（hex，对应 OpenSky icao24）  | ★★★      |
| `latitude`                 | float | 实时纬度（WGS-84）                       | ★★★      |
| `longitude`                | float | 实时经度（WGS-84）                       | ★★★      |
| `heading`                  | int   | 航向（度，顺时针）                       | ★★       |
| `altitude`                 | int   | **高度（英尺）**（注：OpenSky 单位为米） | ★★       |
| `ground_speed`             | int   | 地速（节 kts）                           | ★★       |
| `vertical_speed`           | int   | 垂直速率（英尺/分钟）                    | ★        |
| `squawk`                   | str   | 应答机代码                               |          |
| `on_ground`                | bool  | 是否在地面                               | ★        |
| `time`                     | int   | 位置时间戳（Unix UTC）                   |          |
| `callsign`                 | str   | ATC 呼号（如 CCA101）                    | ★★★      |
| `number`                   | str   | 航班号（如 CA101，含航司前缀）           | ★★★      |
| `airline_iata`             | str   | 航空公司 IATA 代码（如 CA）              | ★★★      |
| `airline_icao`             | str   | 航空公司 ICAO 代码（如 CCA）             | ★★       |
| `aircraft_code`            | str   | 机型 ICAO 代码（如 B738、A320）          | ★★★      |
| `registration`             | str   | 飞机注册号（尾号，如 B-5678）            | ★★★      |
| `origin_airport_iata`      | str   | 出发机场 IATA（如 PEK）                  | ★★★      |
| `destination_airport_iata` | str   | 目的地机场 IATA（如 SHA）                | ★★★      |

> ⚠️ `altitude` 单位为**英尺**（ft），与 OpenSky `baro_altitude`（米）不同，pipeline 中直接存储为 `altitude_ft`。

**与 AirLabs `/flights` 的比较：**

| 特性          | FR24 (free)    | AirLabs (free)           |
| ------------- | -------------- | ------------------------ |
| 每日调用次数  | 无硬性限制     | 1000 次/月               |
| 全球覆盖      | ✅ 分区采集     | ✅ bbox 查询              |
| 出发/到达机场 | ✅ IATA         | ✅ IATA + ICAO            |
| 机型          | ✅ ICAO         | ✅ ICAO                   |
| 航班号        | ✅ 含航司前缀   | ✅                        |
| 注册号        | ✅              | ❌ Free 不返回            |
| 航班状态      | ❌ 无 status    | ✅ scheduled/en-route 等  |
| 高度速度精度  | ✅ 高（ADS-B）  | 中等                     |
| **结论**      | 商业层第二来源 | 商业层主来源（quota 少） |

---

#### `get_flight_details(flight_id)` — 单条航班完整详情（按需调用）

```python
details = fr.get_flight_details(flight.id)
flight.set_flight_details(details)
```

调用后 `Flight` 对象新增字段（需额外 HTTP 请求）：

| 字段                          | 说明                                           |
| ----------------------------- | ---------------------------------------------- |
| `aircraft_model`              | 机型全称（如 Boeing 737-800）                  |
| `aircraft_age`                | 机龄（年）                                     |
| `aircraft_country_id`         | 注册国                                         |
| `aircraft_images`             | 飞机照片列表                                   |
| `airline_name`                | 航空公司全名                                   |
| `airline_short_name`          | 航空公司简称                                   |
| `airport.origin.*`            | 出发机场完整信息（名称、ICAO、坐标、时区等）   |
| `airport.destination.*`       | 目的地机场完整信息                             |
| `time_details`                | 出发/到达时间、延误信息                        |
| `status_text` / `status_icon` | 航班状态文字和图标 ID                          |
| `trail`                       | 历史轨迹点列表 `[lat, lng, alt, spd, ts, ...]` |

> ⚠️ 频繁调用 `get_flight_details` 会显著增加被封禁风险，建议仅对用户主动查询的航班按需调用，**不应在后台批量调用**。

---

#### `get_zones()` — 全球地理分区（参考用）

```python
zones = fr.get_zones()  # 返回含 subzones 的嵌套 dict
```

> 本项目不使用动态 zones，改用静态 25 区域表（`_FR24_ZONES`）以减少额外 API 调用。

---

### 4.2 反封禁设计（当前 pipeline 实现）

**双层随机 sleep：**

| 层级    | 时机                     | 随机范围    | 目的                       |
| ------- | ------------------------ | ----------- | -------------------------- |
| Layer 1 | 每两个相邻 zone 请求之间 | 1.0 – 4.0 s | 请求分散在 60-70 s 窗口    |
| Layer 2 | 全部 25 区域采集完成后   | 20 – 30 s   | 采集结束后冷却，总周期≈90s |

**403 自动退级：**
- 任意 zone 返回 HTTP 403 Forbidden 时，立即停止采集
- 设置 `_fr24_disabled = True`，清空缓存
- Realtime 层自动退级为 OpenSky 单数据源
- 不会无限重试，避免进一步触发封禁

**其他可选加固策略（当前未实现）：**

| 策略                    | 原理                                                                                                                 | 成本         | 推荐场景            |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------ | ------------------- |
| 分区顺序随机化          | 每轮 `random.shuffle(_FR24_ZONES)` 打乱 25 个区域的遍历顺序，使流量模式无规律                                        | 零额外请求   | 低风险，可直接启用  |
| 指数退避重试            | 首次 403 时先等 60 s 重试一次，再等 120 s 再重试一次，三次失败后才触发退级；短暂封禁（如 IP 轮换后的临时拦截）可自愈 | 零额外请求   | 封禁频率较高时      |
| 区域跳跃（Skip on 429） | 收到 429 Too Many Requests 时跳过当前 zone，不中断整轮采集                                                           | 零额外请求   | 热门区域限速时      |
| CF Worker IP 轮换       | 在多个 Cloudflare Workers 账号/Workers Route 之间随机路由，避免单 Worker IP 被 FR24 长期封禁                         | 多个 CF 账号 | 长期生产环境        |
| UA/Headers 随机化       | 每次请求随机选取合理的 `User-Agent`、`Accept-Language`，使指纹特征更分散（SDK 层修改）                               | 零额外请求   | FR24 通过指纹检测时 |

---

## 5. MapTiler Cloud API（地图底图，主）

**官方文档：** https://docs.maptiler.com/cloud/api/  
**根地址：** `https://api.maptiler.com`  
**认证方式：** 所有请求统一附加 `?key=YOUR_MAPTILER_API_KEY` 查询参数  
**免费配额：** 100,000 tile loads / 月（超额返回 `429`）  
**错误码：** `403` = Key 无效或未授权；`429` = 月度配额耗尽  
**Key 保护建议：** 生产环境在 MapTiler Cloud 控制台为 API Key 绑定允许的 HTTP Origin，防止被盗用；开发环境可保持无限制

---

### 5.1 Style JSON（**当前已用**）

```
GET https://api.maptiler.com/maps/{mapId}/style.json?key=KEY
```

返回完整的 MapLibre GL 样式描述，包含底图所有图层、数据源、Sprite 与字体引用。  
MapLibre 在初始化时自动加载此 URL 并解析各资源路径。

**本项目使用的 `mapId`：**

| mapId              | 显示名称 | 说明                         |
| ------------------ | -------- | ---------------------------- |
| `dataviz-dark`     | 专业深色 | 深色配色，专为数据可视化设计 |
| `dataviz`          | 专业浅色 | 浅色配色，同系列             |
| `streets-v2-dark`  | 街道深色 | 含街道标注的深色街道底图     |
| `satellite-hybrid` | 卫星影像 | 真彩色卫星影像叠加道路标注   |

---

### 5.2 矢量/栅格 Tile

| 格式 | 端点                                     | 说明                 |
| ---- | ---------------------------------------- | -------------------- |
| 矢量 | `/maps/{mapId}/{z}/{x}/{y}.pbf?key=KEY`  | Protocol Buffer 格式 |
| 栅格 | `/maps/{mapId}/{z}/{x}/{y}.png?key=KEY`  | PNG 栅格瓦片         |
| JPEG | `/maps/{mapId}/{z}/{x}/{y}.jpg?key=KEY`  | JPEG 栅格（卫星图）  |
| WebP | `/maps/{mapId}/{z}/{x}/{y}.webp?key=KEY` | WebP 栅格            |

> Tile URL 由 Style JSON 中的 `sources` 字段自动定义，MapLibre 会自动请求，无需手动构造。

---

### 5.3 Sprite（图标精灵图）

```
GET https://api.maptiler.com/maps/{mapId}/sprite.json?key=KEY      # 图标元数据
GET https://api.maptiler.com/maps/{mapId}/sprite.png?key=KEY       # 图标图集（1x）
GET https://api.maptiler.com/maps/{mapId}/sprite@2x.json?key=KEY   # 高清元数据
GET https://api.maptiler.com/maps/{mapId}/sprite@2x.png?key=KEY    # 高清图集（2x）
```

Sprite URL 同样由 Style JSON 中 `sprite` 字段声明，MapLibre 自动加载。

---

### 5.4 字体（Glyph / Font）

```
GET https://api.maptiler.com/fonts/{fontstack}/{start}-{end}.pbf?key=KEY
```

`fontstack` 为逗号分隔的字体栈（如 `Noto Sans Regular,Noto Sans Italic`），由 Style JSON `glyphs` 字段指定。MapLibre 自动按需请求字形 PBF。

---

### 5.5 TileJSON 元数据

```
GET https://api.maptiler.com/maps/{mapId}/tiles.json?key=KEY
```

返回 TileJSON 规范对象，包含 tile URL 模板、bounds、minzoom/maxzoom、attribution 等信息。

---

### 5.6 Sky-Trace 代理机制

由于国内直连 `api.maptiler.com` 可能受限，项目通过以下链路代理所有 MapTiler 流量：

```
浏览器 → transformRequest() 重写 URL
  → /maptiler-proxy/{path}?{qs}
  → Vite Dev Proxy / FastAPI 后端 /api/v1/tiles/maptiler/{path}
  → Node.js/aiohttp（读取环境变量 HTTP_PROXY）
  → https://api.maptiler.com
```

`transformRequest` 拦截所有以 `https://api.maptiler.com` 开头的请求（Tiles、Fonts、Sprites、Style JSON），重写为本地代理路径。

---

## 6. Stadia Maps API（地图底图，备）

**官方文档：** https://docs.stadiamaps.com/  
**根地址（所有资源）：** `https://tiles.stadiamaps.com`  
**认证方式（二选一）：**
- 查询参数：`?api_key=YOUR-API-KEY`
- 请求头：`Authorization: Stadia-Auth YOUR-API-KEY`
- 本地开发（`localhost`）：无需 Key，但受严格限速

**免费层限制：** 仅限非商业用途（开发、学术、评估）；月度积分耗尽时返回 `429`，不自动续期；不得用于商业产品  
**⚠️ ToS 限制：** 服务条款明确**禁止代理（Proxying）和批量下载**。本项目使用代理访问仅用于规避国内网络访问受限的开发场景，请勿在生产公开部署中使用此方式  
**错误码：** `401` = 认证失败；`403` = 当前套餐不含此 API；`429` = 配额耗尽

---

### 6.1 Style JSON（**当前已用**）

```
GET https://tiles.stadiamaps.com/styles/{style}/style.json?api_key=KEY
```

**本项目使用的 `style` ID：**

| style                 | 显示名称 | 说明                       |
| --------------------- | -------- | -------------------------- |
| `alidade_smooth_dark` | 深色平滑 | 极简深色底图，适合数据叠加 |
| `alidade_smooth`      | 浅色平滑 | 极简浅色底图               |
| `alidade_satellite`   | 卫星影像 | 卫星影像底图               |

**其他可用样式（参考）：**

| style               | 说明                        |
| ------------------- | --------------------------- |
| `outdoors`          | 户外地形图，含等高线        |
| `stamen_toner`      | 高对比黑白底图（Stamen 系） |
| `stamen_terrain`    | 地形底图（Stamen 系）       |
| `stamen_watercolor` | 水彩风格艺术底图            |
| `osm_bright`        | OpenStreetMap 亮色底图      |

---

### 6.2 矢量 Tile

```
GET https://tiles.stadiamaps.com/data/{source}/{z}/{x}/{y}.mvt?api_key=KEY
```

Tile URL 由 Style JSON 的 `sources` 字段自动给出，MapLibre 自动请求，无需手动构造。

---

### 6.3 字体（Glyph）与 Sprite

> **重要：** Stadia Maps 的字体（Glyph PBF）与 Sprite 均由 `tiles.stadiamaps.com` 提供，**不使用** `fonts.stadiamaps.com`（该域名仅供 Web 字体下载，不服务地图渲染资源）。

```
# 字体 Glyph PBF
GET https://tiles.stadiamaps.com/fonts/{fontstack}/{start}-{end}.pbf?api_key=KEY

# Sprite 元数据
GET https://tiles.stadiamaps.com/sprites/{style}.json?api_key=KEY
GET https://tiles.stadiamaps.com/sprites/{style}.png?api_key=KEY
GET https://tiles.stadiamaps.com/sprites/{style}@2x.json?api_key=KEY
GET https://tiles.stadiamaps.com/sprites/{style}@2x.png?api_key=KEY
```

Style JSON 中的 `glyphs` 与 `sprite` 字段均已指向 `tiles.stadiamaps.com`，MapLibre 自动按需加载。

---

### 6.4 Sky-Trace 代理机制

所有 Stadia Maps 资源（Style、Tiles、Fonts、Sprites）均通过同一代理链路：

```
浏览器 → transformRequest() 重写 URL
  → /stadia-proxy/{path}?{qs}
  → Vite Dev Proxy / FastAPI 后端 /api/v1/tiles/stadia/{path}
  → Node.js/aiohttp（读取环境变量 HTTP_PROXY）
  → https://tiles.stadiamaps.com
```

`transformRequest` 拦截所有以 `https://tiles.stadiamaps.com` 开头的请求，覆盖 Tiles、Fonts、Sprites 及 Style JSON，无需额外配置其他子域名代理。

---

## 7. 新机会与建议

### 5.1 高价值新功能（可立即实现）

#### ✅ 5.1.1 空气质量叠加层（OpenWeather `/air_pollution`）

- **不消耗 AirLabs 额度，完全免费（OpenWeather 免费套餐覆盖）**
- 为航班所在区域提供 AQI + PM2.5/PM10/O₃/NO₂/CO 数据
- 应用场景：高污染天气时在前端地图显示特殊标记；为飞行员/分析员提供能见度参考
- **实现建议：** 在 `unified_pipeline.py` 中新增 `_collect_air_quality()` 方法，以 BBOX 中心点（纬度≈23.5, 经度≈112）每小时请求一次

> **✅ 已实现（2026-05-12）**
> - `unified_pipeline.py` 的 `_collect_environment()` 已对 20 个枢纽机场并发采集空气质量，与天气数据分离存入 `_air_quality_cache`
> - 新增 `GET /api/v1/datahub/air_quality` 端点，返回 IATA 键字典（含 `aqi`、`pm2_5`、`pm10`、`components`）
> - 前端新增 `fetchAirQuality()` → `store.airQualityData`，地图工具栏 AQI 按钮切换圆形叠加层
> - AQI 等级色阶：1=`#00e400`（优良）/ 2=`#ffff00`（良好）/ 3=`#ff7e00`（轻度）/ 4=`#ff0000`（中度）/ 5=`#8f3f97`（重度）

#### ✅ 5.1.2 航班延误信息（AirLabs `/flight` 单条详情）

- 当前批量 `/flights` 已返回基础状态，但不含延误分钟数
- 对特定关注航班可调用 `/flight?flight_iata=XX`，获取 `dep_delayed`、`arr_delayed`
- **节约额度建议：** 仅对状态异常的航班（非 `en-route`）触发单条查询

> **✅ 已实现（2026-05-12）**
> - 未使用单条详情查询（节约额度），改为从 AirLabs 批量 `/flights` 数据中提取 `dep_time`/`arr_time` 字段
> - `FlightBrief`/`FlightDetail` 新增 `dep_time`/`arr_time`/`airline_iata`，通过 `_commercial` 内存缓存实时富集到 WS 快照
> - `flight_details_extra` 表新增对应列，支持重启后恢复
> - 前端 `FlightDetailCard.vue` 展示"计划起飞"/"计划到达"两行，`FlightDetail` schema 已扩展

#### ✅ 5.1.3 离港/到港机场时刻表（AirLabs `/schedules`）

- 可展示某机场未来10小时的出发/到达队列
- 结合 OpenSky 实时位置，可验证某航班是否已按时起飞
- **实现建议：** 对项目监控的主要机场（如 ZGGG 广州、ZGSZ 深圳）每小时轮询一次

> **✅ 已实现（2026-05-12）**
> - `unified_pipeline.py` 新增 `fetch_airport_schedules(iata, direction)` 方法，内置 5 分钟内存缓存（`_schedules_cache`）
> - 调用 AirLabs `/schedules?iata={IATA}&direction={dep|arr}`，按需查询，无主动轮询（节约额度）
> - 新增后端端点 `GET /api/v1/airports/{iata}/schedules?direction=dep|arr`
> - 新增前端 `SchedulePanel.vue` 组件：点击地图机场标记自动触发，支持离港/到港 Tab 切换，含状态色标与航司 Logo

#### ✅ 5.1.4 飞机扩展分类（OpenSky `extended=1`）

- 在现有 `/states/all` 请求中加入 `extended=1`，**不增加额外额度消耗**
- 可获得飞机类别字段（商用大型、旋翼机、无人机等）
- **实现建议：** 修改 `_collect_realtime()` 的 bbox 请求，追加 `extended=1`

> **✅ 已实现（2026-05-12）**
> - `_collect_realtime()` 已对 OpenSky `/states/all` 追加 `extended=1` 参数
> - states 数组 index 17 即为 `aircraft_category`（0=unknown, 2=light, 4=large, 6=heavy, 8=rotorcraft, 14=UAV）
> - `FlightBrief` 新增 `aircraft_category: int | None`，随 WS 快照推送至前端
> - 前端 `FlightBrief` 类型已包含 `aircraft_category?: number`，`StatsView.vue` 可按类别统计

#### 🔶 5.1.5 静态航线数据库本地缓存（AirLabs `/routes`）

- 一次性下载华南区域主要机场的所有航线数据，本地存储
- 用于丰富前端"常规航线"展示，无需实时调用
- **额度评估：** 按机场逐一下载，每机场 1 次请求（Free 50条/次），可覆盖 ZGSZ/ZGGG/ZGHA/ZGKL 等约10个机场 → 消耗约 10 次额度

#### ✅ 5.1.6 航空公司 Logo 展示（AirLabs 静态图片）

- `https://airlabs.co/img/airline/m/{IATA}.png` **无需 API Key，完全免费**
- 直接在前端使用，为航班卡片添加航空公司 Logo
- **无额度消耗**

> **✅ 已实现（2026-05-12）**
> - `FlightBrief`/`FlightDetail` 均含 `airline_iata` 字段，由商业层（AirLabs/FR24）富集
> - `FlightDetailCard.vue` 右上角展示 48×48px Logo，`<img @error>` 自动隐藏加载失败的图片
> - `FlightListPanel.vue` 每行显示 20px Logo 缩略图
> - `SchedulePanel.vue` 时刻表每行显示对应航司 Logo
> - URL 格式：`https://airlabs.co/img/airline/m/{airline_iata}.png`

#### 🔶 5.1.7 机场元信息本地缓存（AirLabs `/airports`）

- 一次性拉取华南主要机场的坐标、时区、名称
- 用于前端地图标注机场图标，免于每次查询
- **额度评估：** 约 10–20 次请求，一次性消耗

#### ✅ 5.1.8 FR24 商业数据作为 AirLabs 第二来源（**已实现**）

- **无额外 API 调用，完全免费**：`get_flights()` 基础查询已包含出发/到达机场、机型、航班号、注册号
- 覆盖范围远超 AirLabs：FR24 分区查询 ~12 000 架次 vs AirLabs bbox 查询仅覆盖配置区域
- **已实现：** `_fr24_background_loop` 在每轮采集后自动调用 `upsert_detail_extra`，以 `source="fr24"` 写入商业层字段
- AirLabs 仍作为主商业来源（提供 `status` 字段），FR24 作为补充（提供 `registration` 等 AirLabs Free 不返回的字段）

---

### 5.2 中期建议（需更多开发）

#### 5.2.1 5天天气预报集成（OpenWeather `/forecast`）

- 当前仅使用实时天气；预报数据可为“未来航班是否受天气影响”提供参考
- 响应包含降水概率（`pop`）、风速、能见度，对航班管理场景有价値

#### 5.2.2 历史航班轨迹（OpenSky `/tracks/all`）

- 对特定 icao24 查询实时或历史轨迹（`time=0` 为实时）
- 可实现“航班实时轨迹回放”功能
- **注意：** 实验性端点，消耗 4 点/次

#### 5.2.3 按机场查历史到离港（OpenSky `/flights/arrival` + `/flights/departure`）

- 结合本地主要机场 ICAO，可拉取前一天实际到离港数据
- 用于统计分析、准点率计算等

---

### 5.3 额度使用建议汇总

| API                        | 当前消耗                          | 优化建议                                                  |
| -------------------------- | --------------------------------- | --------------------------------------------------------- |
| AirLabs（1000次/月）       | 每日1次批量 `/flights` = 31次/月  | 剩余约969次，可用于 `/routes` 静态缓存 + 异常航班单条详情 |
| OpenSky（4000点/日）       | 每N秒1次 `/states/all` = 约2点/次 | bbox 40sq° → 2点/次，1小时可调用约2000次                  |
| OpenWeather（1000次/分钟） | 现有气象查询                      | 免费额度充裕，可放心添加 `/air_pollution`                 |
| FR24（无官方限制）         | 25区域 / ~90s 一轮 = ~960次/日    | 双层 sleep 规避封禁；403 触发后自动退级                   |

---

*文档基于官方公开文档整理，部分字段在免费套餐下可能返回 null 或缺失。建议在集成前通过实际 API 响应验证字段覆盖率。*
