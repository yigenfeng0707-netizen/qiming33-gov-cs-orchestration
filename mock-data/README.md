# mock-data —— 启明杯 3-3 脱敏 mock 业务库（提交主办方建库）

按主办方口径准备：**模拟数据发送至 <主办方接口人邮箱>，技术老师统一建库上传，再把查看账号回传**。
本目录即"随邮件发出去的那包数据"，MySQL 8.0 语法，导入后即可作为 3-3 十个 ACS 能力的真实数据底座。

**发出去只需两个东西**：附件 `qiming33-mock-sql.zip`（4 个文件）+ 正文粘贴 `邮件正文-发主办方.txt`。
`check_mock_data.py` 是我方仓库自用的离线校验器，不随邮件发送。

## 文件

| 文件 | 作用 |
|---|---|
| `01_schema.sql` | 建库 `qiming33_mock` + 10 张 `mock_*` 表（全部带 COMMENT 说明字段语义） |
| `02_data.sql` | 79 行业务数据，客户/电路/设备/工单/快照/告警/变更/历史单/画像/知识台账 |
| `03_verify.sql` | 21 条自检，导入后执行，**全 PASS 才算数据没被改坏**；末尾附 3 条路演现场查询 |
| `check_mock_data.py` | 离线校验器（零依赖）：把上面两个 SQL 解析回数据、用 Python 复算那 21 条断言 |
| `run_verify_live.py` | 真库校验器：连主办方已导入的 `qiming33_mock` 执行 `03_verify.sql`，逐条打印（只读） |

## 为什么先跑 `check_mock_data.py`

发邮件当时我方出口 IP 被 `<平台主机>:<端口-DB>` 以 `1045 Access denied` 拒绝，SQL 没法在真库上试跑。
所以在发出之前把语法与数据自洽性用另一种方式验一遍，不把"能不能导入"的风险丢给技术老师
（9-27 主办方回传只读账号后，同一套断言已在真库跑通，见文末"真库回归"）：

```bash
cd mock-data && python check_mock_data.py     # 退出码 0 = 全部通过
```

2026-09-25 现状：**10 张表 / 79 行 / 21 条断言全通过**。并且做过变异测试，确认这套校验不是"永远 PASS"：

| 故意注入的错误 | 被哪条断言抓到 |
|---|---|
| 多加第 8 台同批次光模块设备 | 03（在网 19 台）、04（同批次 7 台） |
| 删掉一条历史告警 | 10（近 90 天 5 条）、10b（画像与明细一致） |
| 把某条电路的客户键改成不存在的值 | 13（外键孤儿） |
| 在合同号里塞一个 11 位手机号形态串 | 17（涉密自查） |
| 把 A07 的 QoS 配平（等于根因消失） | 05（配置≠实测恰好 1 台且为 A07） |
| 删掉主卡单工单 | 06、20 |
| 把一条告警的 10 个值截成 8 个 | 结构检查（值个数与列清单不符） |

## 数据设计的核心约束：演示里报的数字必须能 SELECT 出来

路演与工作台演示会讲到这些数字，它们不该是硬编码的话术，而应从本库复算：

| 演示口径 | 复算方式 |
|---|---|
| 隐患排查扫描 19 台在网政企接入设备 | `SELECT COUNT(*) FROM mock_device WHERE role='政企接入' AND status='在网'` |
| 同批次光模块在网 7 台（隐患数） | `... WHERE optics_batch_no='OPTIC-B2024-07'` |
| 故障根因"QoS 策略与实际带宽不匹配" | `WHERE qos_configured_mbps <> qos_actual_mbps` → 唯一命中 `MOCK-DEVICE-A07`（100/80） |
| 入向丢包 3.20%、P1 | `mock_alarm` `MOCK-ALM-0001` |
| 变更排查命中 2 条（1 根因 + 1 加剧） | `mock_change.effect_on_alarm IN ('根因','加剧')` |
| 卡单"资源未到位"可复算 | `mock_resource_snapshot`：`available_t1=0` 而 `available_now>0`（T+1 脏快照） |
| 主动服务画像 风险中高/流失中、近 90 天 5 告警 6 工单 | `mock_care_profile` 与 `mock_alarm`/`mock_ticket` 明细一致（第 21 条断言专门校验这点） |
| 闭环产出 5 篇知识已发布 | `mock_knowledge_writeback`，标题与知识管理平台已发布标题**逐字相同** |

## 与 10 个 ACS 的对应

`proposal/precheck` ← customer+circuit+resource_snapshot ｜ `order/stuck` ← order+resource_snapshot ｜
`faultloc` ← alarm+device ｜ `change` ← change ｜ `hidden` ← device（批次扫描）｜
`care` ← care_profile+ticket+alarm ｜ `summary` ← knowledge_writeback。
`orchestrator` 只读 `mock_order`/`mock_alarm` 做阶段分诊。

## 真库回归（2026-09-27，主办方已导入）

技术老师回信"脚本已运行"并回传只读账号后，用 `run_verify_live.py` 在真库上跑了同一套 21 条：

```bash
cd mock-data && python run_verify_live.py     # 凭据读 Desktop/TokenAPI/qiming-mysql.txt，不入库
```

结果：**`VERSION=8.0.45`、`DATABASE()=qiming33_mock`、10 表 79 行、21/21 全 PASS**（逐条打印）。
同一套 SQL 离线复算与真库执行两条路都通，说明我方的解析器与 MySQL 的语义没有偏差。
真库校验器同样验过"能红"：只在客户端把第 01 条的期望从 10 改成 11，结果仅该一条变 FAIL
（服务端零写入 —— 我方账号本来也只有 SELECT）。永远绿的校验不算校验。

编排壳也接上了真库：

```bash
cd prototype && python orchestrator.py        # 本地硬编码 mock，离线可跑（回归不变，3/3 PASS）
cd prototype && python orchestrator.py --db   # 十个能力改为真库只读 SELECT（一次演示 12 条查询）
```

数据源切换只在 `AcsTransport.dispatch()` 一个分叉点完成（`bus.handlers`），编排逻辑与时序断言两种模式共用。

**主办方四条回执的落点**：① 脚本已运行 → 本节即回归证据；② 无命名规范 → `mock_*` 命名保留；
③ 赛后回收 → 录屏与材料不得把该库当长期依赖，`--db` 只是加分演示，默认模式离线可跑；
④⑤ 后续改动以邮件提交 SQL → 我方无写权限，模块层拒绝非 `SELECT/WITH` 且会话级 `READ ONLY`。

**⚠️ 越权授权提示**：`SHOW GRANTS` 显示该只读账号另有 `agent` / `agnet` / `zj_hdzz` 三库的 SELECT 权限，
那是其他参赛队的赛道数据。本目录与 `prototype/mock_db.py` 一律不访问：连接固定 `database=qiming33_mock`，
SQL 不写跨库限定名。

## 合规

全部数据由参赛队自行编造：客户名为"示例客户A~J"，编码统一 `MOCK-` 前缀，机房为"浙北机房01"这类虚构命名，
设备型号 `H-Access-2100` 等为假型号；**不含真实客户、工号、密码、手机号、邮箱、真实 IP 或真实网元数据**。
第 17~19 条断言就是针对这三类形态做的自查，随数据一起交付，便于主办方复核。
