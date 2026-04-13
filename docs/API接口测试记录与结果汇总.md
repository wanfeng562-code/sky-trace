# API 接口测试记录与结果汇总

## 1. 目的
本文件用于沉淀课程项目中的接口测试过程与证据，覆盖“API 搜索 -> 测试代码实现 -> 测试结果落盘 -> 结论分析”的完整链路。

## 2. 搜索来源
- 原始搜索记录：`docs/API搜索与记录.md`
- 重点对象：OpenSky、AeroDataBox、Aviationstack、OpenWeatherMap
- 地图可视化库可用性检查：Leaflet、CesiumJS、AntV L7
- 特殊说明：Mapbox 因 IP 限制无法完成注册，已标记并移出自动测试。

## 3. 测试代码与配置位置
- 测试目录：`interface_tests/`
- 聚合执行器：`interface_tests/run_all.py`
- 接口测试脚本：`interface_tests/clients/test_*.py`
- 密钥配置：`interface_tests/.env`
- 结果输出目录：`interface_tests/results/`

## 4. 执行步骤（标准）
```powershell
cd interface_tests
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python run_all.py
```

## 5. 结果文件说明
每次执行将自动生成：
- `api_test_report_YYYYMMDD_HHMMSS.json`：结构化原始结果，便于后续统计和脚本分析
- `api_test_report_YYYYMMDD_HHMMSS.md`：可直接粘贴到课程报告的测试证据
- `latest.json` / `latest.md`：最近一次执行结果快照

## 6. 测试轮次记录表（建议维护）
| 轮次 | 执行时间         | 执行人 | 通过数/总数 | 失败接口                                           | 报告文件                                                   |
| ---- | ---------------- | ------ | ----------- | -------------------------------------------------- | ---------------------------------------------------------- |
| R1   | 2026-04-13 12:17 | 项目组 | 4/8         | AeroDataBox, Aviationstack, Mapbox, OpenWeatherMap | interface_tests/results/api_test_report_20260413_041744.md |
| R2   | 2026-04-13 13:01 | 项目组 | 4/7         | AeroDataBox, Aviationstack, OpenWeatherMap         | interface_tests/results/api_test_report_20260413_050119.md |
| R3   | 2026-04-13 13:29 | 项目组 | 7/7         | 无                                                 | interface_tests/results/api_test_report_20260413_052927.md |

## 7. 单接口结论模板
### 接口名称：OpenSky
- 调用目标：验证实时航班状态可获取
- 关键配置：`OPENSKY_USERNAME` / `OPENSKY_PASSWORD` / `OPENSKY_BBOX`
- 结果概述：PASS/FAIL
- 证据文件：`interface_tests/results/api_test_report_xxx.md`
- 问题与处理：例如限流、返回为空、字段缺失

## 8. 结论与后续动作
- 可用于项目正式联调的接口：OpenSky、AeroDataBox、Aviationstack、OpenWeatherMap。
- 可用于前端地图展示的库：Leaflet、CesiumJS、AntV L7（npm 可用性检查通过）。
- 受限于配额/权限的接口：当前轮次未触发权限错误，但第三方接口仍存在配额与限流风险，需在答辩演示前再进行一次临近时间复测。
- 需要替代或降级策略的接口：Mapbox 因 IP 限制无法完成注册，已从自动测试清单移出，当前以 Leaflet/CesiumJS/L7 方案覆盖。

## 9. 报告引用建议
在课程 Word 报告中，建议将本文件用于“测试过程说明”，并附上：
- `docs/API搜索与记录.md`（搜索依据）
- `interface_tests/results/latest.md`（最新测试结果，当前为 20260413_052927 轮次）
- `interface_tests/results/api_test_report_20260413_052927.md`（全通过轮次固定证据）
- 关键失败截图与修复记录（如有）

## 10. 后端可视化与字段解读入口
- 后端数据可视化页面：`http://127.0.0.1:8000/debug/flights-dashboard`
- 汇总统计接口：`/api/v1/flights/summary`
- 航班列表接口：`/api/v1/flights?page=1&page_size=500`
- 字段含义、用途、使用方式说明文档：`docs/后端数据可视化与字段说明.md`
