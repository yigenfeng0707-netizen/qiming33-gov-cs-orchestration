# 政企客户一站式服务编排（启明杯 AI 挑战赛 · 赛道三 3-3）

面向电信政企客户的**售前—售中—售后**一站式服务编排参考实现：一个超级数字员工做规划与分诊，
十个 ACS 能力做执行，其中售后故障处置采用「故障定位 ‖ 变更排查 并行 → 隐患排查 串行且吃定位结果」
的依赖显式调度。

**评分载体不是本仓库。** 合规硬门槛要求交付物注册在官方**数字员工工厂**、并在**云网智能工作台**演示。
那部分已真实完成：10 个 `zj.govcs.*` ACS 均已发布，超级数字员工「政企一站式」（员工25）挂载全部 10 个
并发布 V3，六步演示在同一会话内跑通（员工被以 `mcp__dep_mcp__dep_zj_25` 真实调用、沙箱产出交付文件、
真并行起两个子 Agent）。本仓库开源的是**设计、契约与可运行的编排参考实现**。

## 快速开始

```bash
cd prototype && python orchestrator.py     # Python ≥3.10，零第三方依赖
```

三段演示依次覆盖售前（方案+预评估）→ 售中（卡单→升级 L2）→ 售后（并行调度+主动关怀+闭环回写），
末尾打印三条时序/数据依赖自检断言。

同一份编排可切数据源（需 `pip install pymysql` + 主办方共享库只读账号，凭据不入仓库）：

```bash
cd prototype && python orchestrator.py --db            # 十个能力改为真库只读 SELECT
cd mock-data && python run_verify_live.py              # 21 条自检在真库逐条复核
```

数据源切换只发生在 `AcsTransport.dispatch()` 一个分叉点（传入 `bus.handlers`），
编排逻辑与时序断言两种模式共用。默认不带 `--db`，保证仓库离线可复现。

## 目录

| 路径 | 内容 | 许可 |
|---|---|---|
| `prototype/orchestrator.py` | 编排内核参考实现：阶段识别、状态机、并行→串行调度、调度自检 | Apache-2.0 |
| `prototype/mock_db.py` | 真库数据层（可选）：把九个能力换成主办方共享库的只读 SELECT，含只读与单库双重约束 | Apache-2.0 |
| `knowledge-samples/*.html` | 5 篇脱敏领域知识（流程规范 / 政企案例 / 解决方案），与知识管理平台已发布标题同名 | CC BY-4.0 |
| `mock-data/` | 脱敏 mock 业务库（主办方 09-27 已建库）：10 表 / 79 行 / 21 条自检，含离线校验器 `check_mock_data.py` 与真库校验器 `run_verify_live.py` | CC BY-4.0（数据）+ Apache-2.0（校验脚本） |
| `solution-3-3.md` | 方案主文档：架构图、状态机、核心伪代码、演示脚本、风险表 | CC BY-4.0 |
| `factory-config-3-3.md` | 平台侧实测记录：工厂/工作台/知识平台/工具链的字段、配方与坑 | CC BY-4.0 |
| `open-source-design.md` | 开源说明：抽象在哪、边界在哪、换真实后端要改哪一行 | CC BY-4.0 |
| `contest-rules-notes.md` | 赛制要点与待办 | CC BY-4.0 |
| `LICENSE` / `LICENSE-docs.md` | 代码 / 文档与知识样例的许可 | — |

**不随包发布**（以 `.gitignore` 为准）：`evidence/`、`evidence-toolchain-bugs*`（含平台内网地址与原始抓包，单独提交给主办方接口人）、
`MySQL数据库访问.txt`（仅指路说明，凭据不在仓库内）、`待主办方确认事项.txt`、`materials/`、`_ppt_shots/`、`_ppt_check/`（PPT 渲染核对产物，可重出）、`ppt/`、
`3-3-路演PPT-v1.pptx`、`submission-materials.md`（含平台地址与内部账号信息）、`prototype/*.txt`（演示运行输出，可重跑）。

## 能力契约（ACS）

主智能体只认契约，不认实现。任何组织把自己已有的开通/故障/变更系统包一层 ACS，即可挂进同一编排器。

| code | 阶段 | 关键入参 | 返回 |
|---|---|---|---|
| `zj.govcs.orchestrator` | 分诊 | `intent` | 阶段判定 + 下游编排 |
| `zj.govcs.proposal` / `.precheck` | 售前 | 客户/需求 | 方案建议 / 资源预评估 |
| `zj.govcs.order` / `.stuck` | 售中 | `orderId` | 开通进度 / 卡单原因与升级 |
| `zj.govcs.faultloc` / `.change` | 售后（并行） | 客户/设备 | 根因与证据 / 变更命中 |
| `zj.govcs.hidden` | 售后（串行） | **`source` = 定位返回值** | 同类隐患扫描范围 |
| `zj.govcs.care` / `.summary` | 主动服务 / 闭环 | 客户画像 | 关怀建议 / 总结与知识回写清单 |

## 已知边界（不掩饰）

1. `prototype/` 的业务 handler 是 **mock**，返回值全部为脱敏样例；单次调用 0.25–0.55s，而真实工作台单步 130–200s。此壳验证的是**编排逻辑与时序约束**，不是性能。
2. 换真实后端只需替换 `AcsTransport.dispatch()` 中的一行调用出口，但**目前被平台侧缺陷阻塞**：`workflow-api/ApiController/postApi` 转发时丢弃请求体，真实后端收不到入参（取证见 `evidence-toolchain-bugs.md`，已提交主办方）。缺陷修复前，工厂中 10 个 ACS 的端点只能指向回显服务。
3. 知识库→数字员工的 RAG 消费通路四条路径已自查排除，待主办方给口径（详见 `factory-config-3-3.md`「一·补9」）。因此本实现中的知识检索尚未接进 `proposal` / `hidden`。

## 数据合规

业务数据全链路仅使用脱敏 mock（`示例客户A`、`MOCK-CUST-0001`、`MOCK-ORD-*`、`MOCK-DEVICE-A07`、`CHG-*`），
不含真实客户、工号、凭据、手机号或邮箱；`prototype/`、`knowledge-samples/` 与 `mock-data/` 内**零**平台地址、零账号信息。
`mock-data/03_verify.sql` 第 17~19 条是对"手机号形态串 / IP 形态串 / 非 MOCK 前缀编码"的机器自查，随数据一起交付供主办方复核。

⚠️ **对外发布前需做一遍脱敏处理**：设计文档（`solution-3-3.md`、`factory-config-3-3.md`、`contest-rules-notes.md`）
为留证需要，记录了大赛官方平台的主机地址/端口与参赛账号姓名。这些属主办方环境信息，
公开发布（如推到公网仓库）前要么征得主办方同意，要么把 IP 替换为 `<平台主机>` 占位符。
提交包内（交给评委，非公网）可保留原样。
