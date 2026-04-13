# Sky-Trace API 接口契约文档模板

## 1. 文档信息
- 文档版本：v0.1.0
- 维护人：项目负责人（后端）
- 最近更新：2026-04-13
- 适用范围：client 与 server 联调

## 2. 约定与原则
- 基础路径：/api/v1
- 协议：HTTP + WebSocket
- 数据格式：application/json
- 时间格式：UTC ISO 8601（例如 2026-04-12T14:30:00Z）
- 字段命名：snake_case
- 单位：速度 knot，高度 feet，经纬度 WGS84

## 3. 通用响应结构（HTTP）

### 3.1 成功响应模板
```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

### 3.2 失败响应模板
```json
{
  "code": 1001,
  "message": "invalid parameter",
  "data": null,
  "request_id": "8f3a7a8f-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

## 4. 接口清单

| 接口名称 | 方法 | 路径                              | 说明                     | 状态 |
| -------- | ---- | --------------------------------- | ------------------------ | ---- |
| 航班列表 | GET  | /api/v1/flights                   | 查询航班列表（支持筛选） | TODO |
| 航班详情 | GET  | /api/v1/flights/{flight_id}       | 查询单航班详情           | TODO |
| 航班轨迹 | GET  | /api/v1/flights/{flight_id}/track | 查询轨迹点列表           | TODO |
| 服务健康 | GET  | /api/v1/health                    | 服务可用性检查           | TODO |
| 实时推送 | WS   | /api/v1/ws/flights                | 推送实时航班增量         | TODO |

## 5. 接口详情模板

以下模板按每个接口复制一节。

---

### 5.x 接口名称：航班列表
- 方法：GET
- 路径：/api/v1/flights
- 负责人：后端 XXX
- 前端调用方：前端 XXX
- 状态：开发中 / 已联调 / 已冻结

#### 5.x.1 请求参数

Query 参数：

| 参数名    | 类型   | 必填 | 默认值 | 示例    | 说明           |
| --------- | ------ | ---- | ------ | ------- | -------------- |
| page      | int    | 否   | 1      | 1       | 页码           |
| page_size | int    | 否   | 100    | 100     | 每页数量       |
| callsign  | string | 否   | -      | CCA1234 | 航班号模糊筛选 |
| min_lat   | float  | 否   | -      | 21.0    | 视口最小纬度   |
| max_lat   | float  | 否   | -      | 26.0    | 视口最大纬度   |
| min_lon   | float  | 否   | -      | 108.0   | 视口最小经度   |
| max_lon   | float  | 否   | -      | 116.0   | 视口最大经度   |

#### 5.x.2 请求示例
```http
GET /api/v1/flights?page=1&page_size=100 HTTP/1.1
Host: 127.0.0.1:8000
```

#### 5.x.3 响应示例
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 2,
    "items": [
      {
        "flight_id": "abc123",
        "callsign": "CCA1234",
        "lat": 23.12,
        "lon": 113.26,
        "heading": 180,
        "speed_kts": 420,
        "altitude_ft": 32000,
        "updated_at": "2026-04-12T14:30:00Z"
      }
    ]
  }
}
```

#### 5.x.4 错误码

| code | message           | 说明         | 处理建议               |
| ---- | ----------------- | ------------ | ---------------------- |
| 1001 | invalid parameter | 参数不合法   | 前端校验并提示         |
| 1002 | upstream timeout  | 上游超时     | 前端提示稍后重试       |
| 1500 | internal error    | 服务内部异常 | 记录 request_id 并排查 |

#### 5.x.5 兼容性说明
- 新增字段：允许
- 删除字段：必须提前一个迭代通知
- 字段类型变更：禁止直接变更，需版本升级

## 6. WebSocket 契约模板

### 6.1 连接信息
- URL：ws://127.0.0.1:8000/api/v1/ws/flights
- 心跳策略：每 20 秒 ping/pong
- 重连策略：指数退避，最大 5 次

### 6.2 消息结构
```json
{
  "event": "flight_update",
  "ts": "2026-04-12T14:30:00Z",
  "data": {
    "flight_id": "abc123",
    "lat": 23.12,
    "lon": 113.26,
    "heading": 180,
    "speed_kts": 420,
    "altitude_ft": 32000
  }
}
```

### 6.3 事件清单

| event         | 说明           | data 结构          |
| ------------- | -------------- | ------------------ |
| snapshot      | 全量快照       | FlightBrief[]      |
| flight_update | 单航班增量更新 | FlightBrief        |
| flight_remove | 航班离线       | { flight_id }      |
| server_notice | 服务通知       | { level, message } |

## 7. 联调验收清单
- 航班列表字段完整且类型正确
- 详情与轨迹字段含义一致
- WebSocket 在断网后可重连
- 错误码与 message 可被前端正确展示
- OpenAPI 文档与实现一致

## 8. 变更记录

| 日期       | 版本   | 变更内容 | 变更人 |
| ---------- | ------ | -------- | ------ |
| YYYY-MM-DD | v0.1.0 | 初始模板 | XXX    |

---
使用建议：每次接口或字段改动，先改本文件再改代码，保证契约先行。
