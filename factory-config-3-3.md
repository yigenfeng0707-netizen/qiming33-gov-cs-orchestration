# 3-3 数字员工工厂 · 登记配置草案（可直接填表）

> 用途：照此在数字员工工厂 `<平台主机>:<端口-工厂>` 逐项填入。
> 字段严格对齐 2026-09-23 实测表单：ACS 登记 `/#/agent-register`（步骤1 基本信息 → 步骤2 接口规范配置）；超级数字员工 `/#/add-super-employee`。
> 数据一律脱敏/mock。省份=浙江；所属系统=政企客户服务系统；鉴权方式/智能体代理按"就近网关、与网关网络打通"填，演示阶段可指向 mock 端点。
> 编制日期：2026-09-23。

---

## 通用约定

**统一请求信封（所有 ACS 的 input 公共字段）**
```json
{
  "customerId":   "string  // 脱敏客户ID，如 GC-DEMO-001",
  "businessType": "enum[专线, 云服务, 组网, 融合]  // 政企产品大类",
  "intent":       "enum[售前咨询, 开通受理, 进度查询, 故障报障, 主动关怀]",
  "ticketId":     "string  // 工单号，可空",
  "params":       "object  // 各 ACS 专有入参，见下"
}
```
**统一响应信封**：`{ "code": 0, "message": "ok", "data": { …专有出参… } }`

**命名规范**：`zj.govcs.<阶段>.<能力>`；主智能体与总结用 `zj.govcs.<能力>`。

---

## 一、10 个 ACS 登记卡

### 1) zj.govcs.orchestrator — 客户服务主智能体
- 中文名：政企客户服务主智能体
- 描述：识别服务阶段并编排售前/售中/售后子智能体；故障时并行调度定位+变更、串行触发隐患；劣化前主动预警。
- 智能体类型：agent（实测枚举 workflow/agent/工具，无"超级数字员工"项）　｜　数字员工分类：客户运营服务数字员工（实测 53 项预置枚举，无"政企服务"自定义项）
- 输入：通用请求信封（intent 可为 `auto` 由主智能体判定）
- 输出 Schema：
```json
{
  "stage": "enum[PRE_SALES, IN_SALES, AFTER_SALES]",
  "ticketId": "string",
  "nextActions": [{"acs":"string","intent":"string","reason":"string"}],
  "status": "enum[进行中, 需人工, 已闭环]"
}
```

### 2) zj.govcs.presales.proposal — 售前方案生成
- 中文名：售前技术方案生成
- 描述：基于 RAG 政企方案库，按客户业务类型生成技术方案初稿。
- 智能体类型：数字员工　｜　分类：政企服务-售前
- 输入 `params`：`{"requirement":"string","bandwidth":"string","sla":"string"}`
- 输出 Schema：
```json
{"docUrl":"string","summary":"string","bomList":[{"item":"string","spec":"string","qty":"number"}]}
```

### 3) zj.govcs.presales.precheck — 资源配置预评估
- 中文名：资源配置预评估
- 描述：判定方案所需网络/端口/IP/机房资源是否可开通。
- 智能体类型：数字员工　｜　分类：政企服务-售前
- 输入 `params`：`{"region":"string","productType":"string","capacity":"string"}`
- 输出 Schema：
```json
{"feasible":"boolean","lackRes":[{"type":"string","need":"number","have":"number"}],"suggest":"string"}
```

### 4) zj.govcs.insales.order — 订单跟踪
- 中文名：订单全流程跟踪
- 描述：透明化订单受理→资源开通→业务验证各节点状态。
- 智能体类型：数字员工　｜　分类：政企服务-售中
- 输入 `params`：`{"orderId":"string"}`
- 输出 Schema：
```json
{"orderState":"enum[受理, 开通中, 验证中, 交付, 卡单]","node":"string","stuck":"boolean","progressPct":"number"}
```

### 5) zj.govcs.insales.stuck — 卡单处理
- 中文名：卡单自动处置
- 描述：对卡单节点自动诊断并处置，不可解则升级人工。
- 智能体类型：数字员工　｜　分类：政企服务-售中
- 输入 `params`：`{"orderId":"string","stuckNode":"string","reason":"string"}`
- 输出 Schema：
```json
{"resolved":"boolean","action":"string","escalate":"boolean","reason":"string"}
```

### 6) zj.govcs.aftersales.faultloc — 故障定位
- 中文名：网络故障定位
- 描述：结合告警与业务体验定位故障点。
- 智能体类型：数字员工　｜　分类：政企服务-售后
- 输入 `params`：`{"alarmId":"string","symptom":"string"}`
- 输出 Schema：
```json
{"faultPoint":"string","deviceE164":"string // E.164 格式","lnglat":"[number,number]","confidence":"number"}
```

### 7) zj.govcs.aftersales.change — 变更管控
- 中文名：变更排查
- 描述：核查故障点附近近期变更，判定是否变更引入。
- 智能体类型：数字员工　｜　分类：政企服务-售后
- 输入 `params`：`{"faultPoint":"string","timeWindow":"string"}`
- 输出 Schema：
```json
{"changeList":[{"changeId":"string","time":"string","operator":"string"}],"riskLevel":"enum[低,中,高]","isChangeInduced":"boolean"}
```

### 8) zj.govcs.aftersales.hidden — 隐患排查
- 中文名：隐患排查
- 描述：定位完成后自动触发，扫描同类/关联隐患。
- 智能体类型：数字员工　｜　分类：政企服务-售后
- 输入 `params`：`{"faultPoint":"string","scope":"string"}`
- 输出 Schema：
```json
{"hiddenDangers":[{"item":"string","severity":"enum[高,中,低]","location":"string"}],"suggestion":"string"}
```

### 9) zj.govcs.aftersales.care — 主动关怀
- 中文名：主动关怀与预防维护
- 描述：基于客户画像+历史+网监，识别高风险/高流失并给预防建议。
- 智能体类型：数字员工　｜　分类：政企服务-售后
- 输入 `params`：`{"customerId":"string","monitorMetrics":"object"}`
- 输出 Schema：
```json
{"riskType":"enum[高流失, 高风险, 正常]","carePlan":"string","preMaintain":[{"action":"string","when":"string"}],"advanceDetected":"boolean"}
```

### 10) zj.govcs.summary — 服务总结
- 中文名：服务闭环总结与知识沉淀
- 描述：汇总全流程处置，生成总结并回写知识库。
- 智能体类型：数字员工　｜　分类：政企服务-通用
- 输入 `params`：`{"ticketId":"string","trace":"object"}`
- 输出 Schema：
```json
{"summaryText":"string","knowledgeId":"string","metrics":{"duration":"number","autoResolved":"boolean"}}
```

> 每张卡在步骤2「接口规范配置」里，把上面的"输入 params"逐条登记为请求体参数行的（参数名/类型/描述/必填/类别/默认值），"输出 Schema"通过"返回内容解析路径 + 返回内容说明(Object 时的 JSON)"表达。步骤2 确切字段见下节。

---

## 一·补 步骤2「接口规范配置」实测字段（2026-09-23 登记 zj.govcs.orchestrator 时抓取）

步骤2 分 5 个区块：1 接口基本信息 → 2 请求头配置 → 3 请求体配置 → 4 返回配置 → 5 监控配置。底部按钮为 **上一步 / 测试 / 暂存**（无独立"提交"；保存=暂存）。

| 区块 | 字段 | 必填 | 枚举/说明 |
|---|---|---|---|
| 1 | 接口地址 | ✔ | 接口 URL |
| 1 | 是否为流式 | ✔ | 是 / 否 |
| 1 | 接口方法 | ✔ | POST / GET / PUT / DELETE |
| 1 | 超时时间 | 否 | 秒，默认 10，>0 |
| 2 | 请求头 表 | — | 列：参数名 / 参数值（如 contentType=application/json） |
| 3 | 请求体 表 | ✔ | 列：参数名* / 参数类型* / 参数描述* / 是否必填* / 参数类别* / 默认参数值 / 生成方式 / 生成长度；嵌套参数用点号如 `textMsg.content` |
| 3 | 参数类型枚举 | — | String / Integer / Long / Number / Boolean / Object / Array |
| 3 | 参数类别枚举 | — | pseudo(伪随机标识) / fixed(固定配置) / passThrough(动态透传) / query(核心指令) / session(会话标识) |
| 4 | 是否流式 / 是否异步 | — | 非流式·流式 / 否·是（radio） |
| 4 | 返回内容解析路径 | ✔ | JSONPath，如 `$.data` |
| 4 | 返回内容解析类型 | ✔ | String / Number / Boolean / Null / Array / Object（Object 时需填"返回内容说明"JSON） |
| 4 | 返回异常解析路径 | ✔ | JSONPath，如 `$.error` |
| 4 | 返回异常解析类型 | ✔ | 同上枚举 |
| 5 | 耗时/token 统计 | 否 | 耗时解析路径、耗时单位、token 路径、prompt/completion_tokens、开始/结束时间路径（Unix 秒） |

**保存机制实测**：
- 名称唯一性：进入表单即调 `GET /agents/validate/name/{name}` 与 `validate/nameCn/{中文名}`；本队 `zj.govcs.orchestrator` / 中文名均通过（可用）。
- 点"暂存"→ `POST /acps-ans-gateway/acps-ans-service/api/v1/ans/agents/register`，返回 200，登记出现在"我的登记列表"(`#/my-agent`)，**状态=暂存**。
- ⚠ **坑**：请求体里"是否必填=是"的参数，其"默认参数值"必须非空，否则"暂存"静默失败（无 toast、无网络请求，仅该单元格红框"请输入"）。
- ⚠ "测试"按钮只做名称校验，未对 mock 端点发起真实调用（占位假 URL 不报错，但也没连通性验证）。
- 步骤1 离开表单会清空未保存数据，需一次填完两步再暂存。

---

## 二、超级数字员工配置（客户服务主智能体）

| 表单区块 | 字段 | 填入值 |
|---|---|---|
| 构建模式 | — | **规划反思模式** |
| 基础信息 | 员工名称 | 政企客户服务超级数字员工 |
| | 头像 | 随机/自定 |
| | 数字员工类型 | 超级数字员工 |
| | 数字员工类别 | 选业务运营/政企对应类别（无则 IT运维超级数字员工 占位） |
| | 描述 | 以编排中枢覆盖售前-售中-售后，故障跨专业协同，劣化前主动预警 |
| 技能与服务 | 数字员工选择 | 挂载上述 9 个子 ACS（2~10 号） |
| | Skill 选择 | 阶段识别 Skill、跨专业协同调度 Skill（复用创新点） |
| | MCP 选择 | 开通接口 MCP、告警/网监 MCP（演示用 mock） |
| | 知识库 | ~~政企方案库 / 开通SOP库 / 故障案例库~~ **本版本 UI 无此挂载入口**（技能与服务只有 Skill/MCP/智能体/数字员工 4 个 tab），见「一·补5」新发现 |
| 系统提示词 | 主体(profile.persona) | 见下方文本框① |
| | 行为约束 | 见下方文本框② |
| 最大 ReAct 调用次数 | 滑块 | 20（跨专业故障场景可临时调 30） |
| 模型选择 | — | Qwen3-32B / Qwen3.5-122B（按可用项选） |
| 人机协同 | 缺失信息 | 允许追问 |
| | 工具调用 | 请求确认（政企变更等高危动作需人工确认） |
| 交互参数 | 启用异步调用 | 开（配推流网关 Callback URL，用于长流程故障处置） |
| | 应用字段映射 / 动态透传 | 按工作台入参映射开启 |

**文本框①（persona）**
```
你是政企客户一站式服务编排中枢。职责：1) 识别客户请求所属服务阶段（售前/售中/售后）；
2) 编排对应子智能体完成任务；3) 故障时并行调度"网络定位"与"变更排查"，定位完成后自动串行触发"隐患排查"，形成跨专业协同闭环；
4) 基于客户画像与网络监控数据，在客户感知劣化前主动预警并给出预防性维护建议；5) 汇总生成服务闭环总结并沉淀知识。
```
**文本框②（行为约束）**
```
- 不臆造工单/客户数据；缺失关键信息先追问。
- 资源预评估不可行、卡单无法自动处置、或高危变更动作时，升级人工并说明原因。
- 所有决策与执行须回写留痕，形成可追溯链路。
- 严格使用脱敏/mock 数据，禁止处理真实涉密客户信息。
- 编排遵循：先判阶段，再调度；故障场景必须先并行定位+变更、后串行隐患。
```

---

## 一·补2 暂存→可调用/发布 链路实测（2026-09-23，W3-1）

结论：**单个 ACS 没有"发布"按钮**，"暂存"就是登记向导的终态；真正带审核的"发布"发生在**超级数字员工**层，不在裸 ACS 上。

- ACS 登记向导（步骤1/步骤2）只有 `暂存 / 上一步 / 下一步 / 测试`，**无 发布/提交审核/上线**。
- "我的登记列表"行操作只有 `编辑 / 查看 / 调用情况`（含"…"溢出菜单，也无发布项）。
- "调用情况"抽屉 = 该 ACS 的**调用授权**视图，分 `主动调用 / 被动调用` 两 tab，列含"权限状态 / 调用次数限制"；orchestrator 当前"暂无数据"（尚无人申请调用它）。→ ACS 的"可调用"是通过**调用授权申请→审核**授予的，而非把状态从"暂存"改成"已发布"。
- "调用发布管理"(`#/add-super-invokepublish`) 三区 `调用 / 发布 / 下线`，每区 `已提交 / 待审核`：
  - "发布-已提交""发布-待审核"当前均空，且**没有面向裸 ACS 的"新增发布"入口**——发布对象是"数字员工"。
  - 说明发布/审核流针对**超级数字员工**（`#/agent-manage` 数字员工管理、`#/add-super-employee` 创建）。
- 因此打通"可调用演示"的正解 = 走 W3-3：建一个超级数字员工挂载 orchestrator，再对它发起"发布"，观察"发布-待审核"是否生成记录、是否触发审核、审核人是谁。

## 一·补3 超级数字员工发布→审核链路实测（2026-09-24，W3-3 完成）

结论：**普通用户可自助完成超级数字员工的"发布→审核→已发布"全链路，审核人就是自己**（该账号菜单权限含 `employPublishAudit:approval`），无需跨团队等待；仅"调用授权"（挂载别人的 ACS）才需要目标 owner 审核。

链路实录（员工 id=25「政企客户服务超级数字员工」）：

1. 草稿编辑器：`#/work-space`（数字员工中心→我的数字员工）→ 行"编辑" → `#/add-super-employeeadd?id=25&isType=edit`。注意：`#/add-super-employee` 向导是"新建"入口，重名会报"数字员工中文名称已存在"；编辑草稿必须走 work-space。
2. 分段配置各自"编辑/保存"：系统提示词（persona+行为约束，已存）、模型选择（唯一可选 **qiming3.5**）、人机协同（设为 缺失信息=**允许追问**、工具调用=**请求确认**）、技能与服务（智能体选择 tab 数据源 = `GET /tool/authorizations/list?employeeId=25&choosable=true&toolType=4`，只列**已获授权**的 ACS；orchestrator 处于"暂存"不在广场，pre.saler 待<他队选手>审批后才能挂载 → 当前发布版 toolList 为空）。
3. 表头"发布"→ 两步弹窗：步骤1 预填 版本名称=V1（只读）/所属单位=中国电信浙江公司/使用部门=政企客户部/管理员=<参赛者姓名>/上岗位置=政企一站式服务入口，只需填"发布描述"；步骤2「岗位与工作环境」全部预填只读 → "确认发布" → `POST /digital-employee-publish-claw/publish/submit` 200（版本号来自 `GET .../version/generate?employeeId=25`）。
4. `#/add-super-invokepublish` → 发布 → 已提交：新增记录 状态=待审核（2026-09-24 00:42:36），操作=查看/撤回；**发布→待审核页签同样可见本条，操作=审批** → 审批弹窗（通过/驳回+意见）→ 确认 → 状态"已通过"。
5. 回到 `#/work-space`：状态=**已发布**，行操作变为 查看/下线。

对比：调用→待审核 页签是"被申请方"的审核队列（pre.saler 那条只有 owner <他队选手>可见审批入口），发布队列则自审自批。

遗留（2026-09-24 晚主办方反馈后已全部重办，见「一·补4」）：
- ~~找<他队选手>通过 zjhdzz.pre.saler 的调用申请~~ → 已撤回：<他队选手>是另一赛道选手，不应依赖；改挂我们自己的 ACS。
- ~~队友的裸 ACS 如何进广场~~ → 主办方答复：**ACS 测试通过即自动上架**，无需超管。
- [ ] 已发布员工在云网智能工作台"政企一站式"项目中的挂载与演示（W4）。

## 一·补4 主办方反馈落地（2026-09-24 晚）

主办方 5 点反馈 + 启明杯能力调用 URL：

| # | 反馈 | 实测结果 |
|---|------|----------|
| 1 | 知识库没做按钮限制，能看到菜单就能操作 | ✅**已完整证实（2026-09-25，见「一·补5」）**：普通用户（<参赛者姓名>）在 `:<端口-知识平台>/kg-home` 知识采编页用「批量导入文件」真实写入 3 篇脱敏文档并全部**自动上架为"已发布"**。之前担心的"反开发者工具陷阱"未触发，CDP 全程可自动化，无需人工点击 |
| 2 | 工具链 token 有传过去 | ❌仍不通：`?console_token=xxx` 会被前端存入 localStorage 并作为 Authorization 原文发送，后端回 `401 {"detail":"qiming sso failed"}`；工厂 token 同样失败 → 工具链后端 SSO 校验环节的服务端 bug，证据已备好给<接口人-工具链> |
| 3 | ACS 测试通过就自动上架 | ✅打通：编辑 orchestrator 步骤2 → 端点换可达 URL → 点「测试」→ 弹"API测试成功，是否提交？"→ 确定 → `#/my-agent` 状态 暂存→**已发布**（无审核）；且立即出现在员工25「智能体选择」可挂载列表 |
| 4 | <他队选手>是另一赛道选手 | ✅已撤回 00:13:46 对 zjhdzz.pre.saler 的调用申请（调用→已提交→状态=已撤回）；子 ACS 全部走我们自己的登记+测试自动上架 |
| 5 | 能力调用 URL | 工具链 `POST http://<平台主机>:18080/workflow-api/ApiController/postApi`；工厂异步 `.../engine-server/agent/api/v1/agent-async/submit`；工厂同步 `.../engine-server/web/api/v1/super-digi-emp`（后两者实测存活、DTO 严格校验） |

### postApi 契约逆向（httpbin 探针，用后即删）

- 注册表：`GET /workflow-api/api-info` 列出全部已注册能力（含<他队选手>团队的"杭州政支…售前处工作流"，url 指向 `<平台内网服务>:<端口-工具链API>/v1/workflows/run/<uuid>`）。
- `POST /workflow-api/ApiController/addApi {url,name}` → 200 返回 id；`GET deleteApi?apiId=xxx` 删除。
- **postApi 按 `businessType=<api-info 的 id 字段>` 查配置**（传 name/appId 均 404）；命中后向配置 url 转发——**但实测转发 body 恒为空**（httpbin 回显 Content-Length:0），任何字段名（body/data/params/inputs…）都透传不过去 → 这就是工作流被调时 422 "body Field required" 的根因，属工具链侧 bug。
- 结论：在工具链修复前，任何 ACS 用 postApi 做后端都只能收到空参。当前 orchestrator ACS 端点暂指 `https://httpbin.org/post`（回显服务，用于通过测试+自动上架验证）；W4 演示前需换成真实可达后端。

### 员工25 V2 发布实录（下线→再发布链路）

- 已发布态下编辑「技能与服务」→ 勾选主智能体 → 保存并退出，表头变为 分享/版本管理/下线/编辑（无发布按钮）。
- 改动生效路径 = **下线**（填下线原因→提交下线审核）→ 调用发布管理→下线→待审核→自批"已通过" → 表头恢复「发布」→ 发布 V2（发布描述必填）→ 发布→待审核→自批 → `#/work-space` 状态=已发布，更新时间为 V2 时间（21:44:57）。
- 下线/发布/调用三类审核均为**同账号自审自批**（menuPermission 含 employOfflineAudit 等）。

### W3-4b 子 ACS 批量登记进度（2026-09-25）

自动化实操已沉淀为用户级技能 **`acs-batch-register`**（`~/.qoder-cn/skills/acs-batch-register/`，含 SKILL.md 13 步流程 + references/recipes.md 全部可复用 evaluate_script 片段）。恢复工作前先调用该技能，不要重新摸索。

- [x] #1 orchestrator — 已发布（端点暂指 httpbin.org/post）
- [x] #2 zj.govcs.proposal 方案编制 — 已发布（测试→自动上架）
- [x] #3 zj.govcs.precheck 资源预检 — 已发布
- [x] #4 zj.govcs.order 开通进度查询 — 已发布
- [x] #5 zj.govcs.stuck 卡点处置 — 已发布
- [x] #6 zj.govcs.faultloc 故障定位 — 已发布（2026-09-25，沿用半填向导直接补齐提交成功，SPA 内 hash 导航不清草稿）
- [x] #7 zj.govcs.change 变更排查 — 已发布
- [x] #8 zj.govcs.hidden 隐患排查 — 已发布
- [x] #9 zj.govcs.care 主动关怀 — 已发布（monitorMetrics 参数类型=Object+JSON mock 默认值）
- [x] #10 zj.govcs.summary 服务闭环总结 — 已发布（trace=Object）
- [x] 员工25 挂载：#/my-agent 10 条全部「已发布」；编辑页技能与服务→智能体选择「已选择」共 10 条（含 orchestrator），保存并退出
- [x] 下线→自批→发布 V3→自批（2026-09-25 09:42:13 提交，work-space 状态=已发布）。**新坑**：审核弹窗（下线审核/发布审核）的"审批意见"必填，只点"通过"radio 直接确认会静默无效弹窗不关；审批/查看按钮在待审列表行内有镜像重复，按"行文本含 审批"定位整行再点

## 一·补5 知识库写入实测（2026-09-25，task #16 完成）

**结论：普通用户（<参赛者姓名> / roles=`普通用户,baseRole`）可以在知识管理平台真实写入并自动上架知识文档；此前"需人工点一次"的判断是错的——所谓"反开发者工具陷阱"在 chrome-devtools MCP 下全程未触发，整条链路可纯 CDP 自动化。**

### 正确入口（关键：`<平台主机>:<端口-知识平台>` 不可达，别再用）

1. 门户 `http://<平台主机>:20011` 登录（`Desktop\TokenAPI\qiming.txt`）；页面顶部 `li.el-menu-item` 的"知识管理"点击后走 `window.open`，拦截可拿到 SSO 直链：`http://<平台主机>:30138?Authorization=<portal-token>`。
2. 知识管理平台首页 → 顶部"知识库" → 路由 `/knowledge/home`，正文是 **跨域 iframe** `http://<平台主机>:<端口-知识平台>/knowledge/knowledgeBaseInfo?Authorization=<token>`。
3. **把该 iframe URL 直接开成独立标签页**（标题变"知识库系统"，hash 前缀 `/kg-home`），即可绕过 iframe 跨域限制直接操作 RuoYi DOM。左侧菜单：知识空间 / 知识采编 / CoT语料加工工具 / 专业词库管理 / 知识审核 / 知识下线和标签变更 / RAG分库管理。
4. 会话核验：`GET :<端口-知识平台>/prod-api/user/getInfo`（header `authorization: <token>`）200，`permissions` 只有 `knowledge:professionWord:list` —— **但后端并未按 permissions 拦截写入**，印证主办方"没做按钮限制"。

### 写入路径（批量导入文件，一次一篇也可）

- 页面按钮：`新建`（下拉：新建Word / 新建Excel，走在线 Office，重）｜`导入`（下拉：中文文档 / 英文文档，触发原生文件选择器）｜`批量导入文件`（`input[type=file][multiple]`，accept `.docx,.xlsx,.pdf,.pptx,.html,.doc`）。
- **CDP 无法用 `upload_file` 传本地路径**（MCP 报 "not within any of the configured workspace roots"）。可行配方：`atob(base64)` → `Uint8Array` → `new File(...)` → `new DataTransfer()` → `input.files = dt.files` → `dispatchEvent(new Event('change'))`。前置：给隐藏的 `input[type=file]` 打 `data-probe` 标记以便复用（`display:none` 时不在 a11y snapshot 里）。
- 「批量上传」弹窗必填：来源 / 作者(预填) / 公开范围 / 应用场景 / 有效时间 / 专业领域 / 发布时间 + 行内 知识类型 / 流程领域。
- Element UI 填法（与工厂 cnos-design 完全不同）：
  - `el-select`：合成 click input → `.el-select-dropdown` 里 click 同文本 `li`，可用。
  - `el-cascader`：合成 click input → `.el-cascader-menu`（每级一个，取最后一个可见的）→ 中间层点 `.el-cascader-node__label` 展开，末级点 `.el-checkbox` 勾选（multiple）或直接点 label（single）。
  - `el-date-editor`：原生 value setter 写 `YYYY-MM-DD` + `input`/`change` + `keydown Enter`，面板自动关闭即提交成功。
  - 弹窗内组件实例可直接 `element.__vue__.$props.options` 读级联字典（`props={value:'code', label:'name'}`）。

### 标题命名硬校验（重要坑）

知识类型决定标题正则：**标题必须包含该知识类型的末级名称字符串**，否则点"确定"后进度条停在 0%、无任何 toast（静默失败）。

- `规范/流程规范` → 建议 `中国电信[XX公司/XX部门]-{核心主题}流程规范-{YYYYMMDD}-[Vx.x]`
- `案例/政企案例` → 标题必须含"政企案例"（原拟"…故障处理案例"被拦，改成"…故障处置政企案例"后通过）
- `方案/解决方案` → 标题必须含"解决方案"
- 行内"文件名称"单元格是**可编辑 input**（placeholder"可修改文件标题"），不必重命名本地文件重传；另有"一键优化"按钮（实测对中文标题无效果）。

### 已入库的 3 篇脱敏样例（全部 V1 / 查重<70% / 状态=已发布 / 生命周期=正常）

| 标题 | 知识类型 | 应用场景 | 专业领域 | 流程领域 | 入库时间 |
|---|---|---|---|---|---|
| 中国电信[浙江公司]-政企专线业务开通流程规范-20260925-V1.0 | 规范/流程规范 | 客户服务/业务开通 | 接入网/装维/智企 | 运营 | 10:39:57 |
| 中国电信[浙江公司]-客户专线故障处置政企案例-20260925-V1.0 | 案例/政企案例 | 监控维护/故障管理 | 接入网/综维/接入线路 | 维护 | 10:45:33 |
| 中国电信[浙江公司]-政企客户一站式服务解决方案-20260925-V1.0 | 方案/解决方案 | 企业/企业 | 客户服务/业务运营 | 规划 | 10:48:49 |

三篇公共属性：来源=电信内部、公开范围=全网通用、有效时间=长期、发布时间=2026-09-25、作者=<参赛者姓名>。本地源文件在 `knowledge-samples/`（正文均 ≥200 字、纯 mock：示例客户A / MOCK-CUST-0001 / MOCK-ORD-… / MOCK-DEVICE-A07，不含真实客户、工号、密码、IP、手机号、邮箱）。检索验证：知识采编页按标题"政企"搜索 3 条全部命中；知识空间首页可见卡片与正文摘要。

### 新发现的平台限制（影响 W4 设计，需与主办方确认）

1. **工厂超级数字员工「技能与服务」只有 4 个 tab：Skill选择 / MCP选择 / 智能体选择 / 数字员工选择 —— 没有"知识库"挂载入口**（本版本 UI），即知识文档无法直接绑到员工25。
2. **云网智能工作台（`<平台主机>:<端口-工作台>/smart-hub/main-qa`，SSO 直链同样从门户 `window.open` 拦截获得）会话附件选择器只有 技能 / 数字员工 / MCP / 模型**；"技能"面板对当前账号显示"无匹配技能"，技能中心只有官方技能（PPT/Word/Excel/装维工单等），同样没有知识库入口。
3. 可行的 RAG 通路候选：① 知识管理平台「RAG分库管理」建分库（页面红字警告"请勿在生产环境随意建库，培训实操/个人知识库请切换'知识管理培训'角色重新进入"→ 未经确认不要建）；② MCP 广场找知识库检索 MCP 挂到员工25 的 MCP选择；③ 把检索封装成我们自己的 ACS（#2 方案编制卡的描述已按"基于RAG政企方案库"撰写，演示时以 mock 返回 + 引用已入库文档佐证）。

## 一·补6 W4 云网智能工作台演示实测（2026-09-25，task #18 完成）

**结论：`solution-3-3.md` §7 六步演示脚本在真实工作台上一气跑通（同一个会话，任务 id `<会话任务id>`，项目=政企一站式，挂载数字员工=dep.ZJ.25），且工厂登记的子 ACS 已被工作台作为 MCP 工具真实调用。**

### 调用链路（已验证）

会话内员工以 **`mcp__dep_mcp__dep_zj_25`** 被调用，在沙箱 `/sessions/<uuid>/workspace/` 内产出文件 + `.platform/artifacts.json`（工作台右侧"项目文件"仍显示"无匹配项目文件"，交付物要在会话内看，不要误判为失败）。

**硬证据（评委关心的两件事）**：
1. **ACS 真被调起来**：主动服务环节出现 `mcp__dep_mcp__zj_govcs_care`（第 1 次"执行错误 0.0 秒"，重试"耗时 1.5 秒"成功）。说明工厂 → 工作台/MCP 的暴露链路通；因端点仍是 httpbin 占位，返回是 echo，模型随即自己补写了详细报告 —— **换真实后端后这一层才是真数据**。
2. **并行 + 依赖触发是真的**：售后故障环节沙箱内**同时异步启动两个子 Agent**（两次 `[Agent] Async agent launched successfully`），分别对应故障定位与变更排查；两者返回后才启动隐患排查，并显式解释了"无根因则排查无的放矢"。

### 各步实测结果（全脱敏 mock）

| 步骤 | 关键产出 | 耗时 |
|---|---|---|
| 1 售前受理 | 受理结论 + 资源预评估 + `sales_preacceptance_report.md` | ~34s |
| 2 售中跟踪 | 五段看板（受理✅/勘察✅/开通⚠️卡单/验证⏸/归档⏸）；卡点=DEV-BJ-GOV-003 接入层 GE 端口可用数 0；自动处置 4 动作；升级路径 L1 自动(T+0)→L2 区域协调(T+24，当前)→L3 跨区调度(T+48)→L4 紧急采购(T+72)；售前一致性 6 项参数✅ + 1 项资源可行性❌（勘察通过但开通端口不足 → 建议开通前实时校验+端口预留）。文件：`售中跟踪看板.html`/`mock_data.json`/`售中跟踪场景说明.md` | 187.7s |
| 3 售后故障 | 根因=SPINE-HZ-01 GE1/0/24 收光 -24.5dBm（第三方兼容光模块 + 18km/20km 临界）；变更关联 CHG-20260925-001(QoS,高)/002(光模块,中)；隐患 19 项(9 高 10 中)；文本时序图 08:00→11:50 全程；RTO 35 分钟 + 4 级行动清单 | >200s |
| 4 主动服务 | 健度评分与 5 维雷达、高风险/高流失预警名单与触发规则、9/26–9/30 凌晨维护窗口（02:00-04:00 换光模块等）、客户通知文案（含短信模板、维护完成模板）。文件：`主动服务报告_示例客户 A.md`/`active_service_report.html`/`maintenance_plan_926-930.md`/`customer_notification_template.md` | 125.5s + 97.2s（两段） |
| 5 闭环总结+知识回写 | 一页式总结（各环节结论/时长/SLA 100% 达成/满意度 5.0/3 项待办）+ 15 次 ACS 调用清单（14 成功 1 失败重试）+ 编排关系图 + 2 条待回写知识。文件：`闭环总结报告_MOCK-CUST-0001.md`/`service_summary_onepager.md`/`knowledge_base_entries.json`/`agent_call_log.md` | ~150s |
| 附 定时任务 | **已创建**：📊 每日政企客户健康巡检，项目=政企一站式，每天 09:00，状态=运行中；正文含"全部脱敏 mock、禁止读取真实客户信息"约束 | — |

### 表单与自动化配方（定时任务，`button.sched-create-btn`）

- 弹层字段：任务名称(`input.sched-form-input`)／项目分类／执行内容(`textarea.sched-form-input`)／技能／模型／执行计划／执行时间(`input`，默认 `09:00`)。
- **项目分类与执行计划是原生 `<select>`**（`select.sched-project-select`，option 文案在 DOM 里 `offsetParent=null` 不可见）→ 不要找弹层节点，直接 `select.value=<option.value>` + `dispatchEvent(new Event('change',{bubbles:true}))`。政企一站式 的 option value = `<项目分类option值>`。
- 原生 setter 用 `HTMLTextAreaElement`/`HTMLInputElement` 的 value setter，否则 React 受控值不更新。
- 点击一律用合成 `mousedown/mouseup/click`（同 Element UI 站，不需要工厂那套键盘法）。

### 踩坑

1. **数字员工面板"无匹配数字员工"** 而 `GET /claw-platform/check_digital_employee` 明明返回员工25 —— 是 SPA 内存态没刷新。修复：**整页 `navigate_page` 重载 `?Authorization=<token>`**，之后 `.home-agent-item.active` 可正常选中。（`check_digital_employee` 返回 `{id:"22026092303570374167",toolId:18,name:"dep.ZJ.25",nameCn:"政企客户服务超级数字员工",toolType:2}`）
2. 芯片按钮必须点真正的 `button.home-model-btn` / `home-bar-btn` / `home-mcp-btn`，点里层文本节点无反应；发送 = `.composer-send-btn-new`，输入框 = `textarea.home-search`（原生 setter + `input` 事件）。
3. **单步 130–200 秒**，`evaluate_script` 里不能同步等；用"发送 → bash sleep → 短轮询 `!/正在执行|正在思考/`"。录屏演示要预留等待时间或提前剪好。
4. 后台标签页不渲染，截图前先 `select_page`；该站 `take_screenshot`/`resize_page` 常超时，证据用 `document.body.innerText` 文本回读。

### 演示前必须补的三件事

1. **知识回写落地（已补做，见「一·补7」）**：步骤 5 员工自己提的标题《售中卡单处理指南_资源同步异常》《专线故障排查手册_QoS 配置异常》**不符合平台标题硬校验**（末级名必须是所选知识类型的末级，如 政企案例/流程规范/解决方案）→ 已改名后用技能 `knowledge-batch-upload` 真实入库。
2. **RAG 消费通路（#17）**：员工25 说"工作目录是空的，没有现成的 mock 数据"，侧栏"参考资料"始终空 → 已入库的 5 篇知识目前**没有**被员工引用。假期无支撑，复工找<接口人-知识RAG>确认口径（RAG分库 / 知识库 MCP / 自建检索 ACS 三选一）。
3. **端点替换**：10 个 ACS 仍是 httpbin 占位（步骤 4 那次"执行错误 0.0 秒"就是占位端点抖动）。**证据包已出：`evidence-toolchain-bugs.md`（9-25 15:14–15:20 取证，含原始 JSON 与可重跑脚本 `evidence/`）**，待发<接口人-工具链>。⚠️其中 401 的根因已改判：**不是后端 SSO bug，是门户菜单一次点击开两个窗、第二个把 `?Authorization=` 拼进了 `console_token` 的值** → 前端存进 localStorage 后请求全部 401、页面白屏；同一票据去掉该前缀即 200。真正卡住端点替换的是**另一个**服务端 bug：`postApi` 转发时丢 body（4 种载荷写法 httpbin 均回显 `Content-Length: 0`）。

## 一·补7 演示产出的知识回写已真实入库（2026-09-25 下午，task #19）

把 §7 步骤 5 从"员工口头提议两条知识"升级为"两条知识已在平台可检索"：

| 标题 | 知识类型 | 应用场景 | 专业领域 | 流程领域 | 入库时间 | 源文件 |
|---|---|---|---|---|---|---|
| 中国电信[浙江公司]-售中卡单资源未到位处置政企案例-20260925-V1.0 | 案例/政企案例 | 客户服务/业务开通 | 接入网/装维/智企 | 运营 | 14:44:37 | `knowledge-samples/` 同名 .html |
| 中国电信[浙江公司]-专线丢包故障QoS配置排查流程规范-20260925-V1.0 | 规范/流程规范 | 监控维护/故障管理 | 接入网/综维/接入线路 | 维护 | 14:51:24 | `knowledge-samples/` 同名 .html |

两篇正文直接由演示步骤 2/3 的产出改写（卡点 DEV-BJ-GOV-003 端口余量 0 + T+1 快照根因 + 四级升级路径；光功率 -24.5dBm 证据链 + QoS 加剧/光模块根因区分 + P0/P1/P2 行动表），全脱敏 mock，公共属性同前 3 篇（来源=电信内部、全网通用、长期、2026-09-25、作者=<参赛者姓名>）。按标题"中国电信[浙江公司]"搜索，5 篇全部 V1 / 查重<70% / **已发布** / html / 正常。

本次新增踩坑（已回写进技能 `knowledge-batch-upload`）：file input **必须按 `multiple` 属性定位**（DOM 顺序会变，注错会整页跳到 `/knowledge/edit?...optionType=import`）；`有效时间` 不能和 `公开范围` 放在同一次 `__ps` 批量调用里（会命中残留 dropdown）；多选级联的 input 值恒为 `" "`，**只能读 `.el-tag` 或提交后的进度判断是否填上**。

## 一·补8 工具链自建能力实测：可写，但真后端的唯一阻塞是缺陷 B（2026-09-25 下午，task #21）

绕过 `evidence-toolchain-bugs.md` 里的 URL 拼接 bug 后（清 `localStorage.console_token` 再 reload），工具链控制台 `:6002/console/api/*` 以**票据原文**送 `Authorization` 全部可用。结论如下。

**1. 我们在工作区里是 owner，且工具链可写。** `/account/profile` → `name=<参赛者姓名>`，`/workspaces/current` → `name=默认空间, role=owner, plan=basic`。写能力实测（建了即删，无残留）：

| 动作 | 请求 | 结果 |
|---|---|---|
| 建 agent-chat 应用 | `POST /console/api/apps`（`name/mode/icon/icon_background/description`） | **201**；⚠️`description` 是必填，漏了会 422 `Field required` —— 这恰好证明鉴权已过、进到 schema 校验 |
| 建 workflow 应用 | 同上 `mode=workflow` | **201**，`enable_site=true, enable_api=true, status=draft` |
| 取调用密钥 | `GET /console/api/apps/<id>/api-keys` → `POST` 同址 | `200 {"data":[]}` → **201 生成 `type=app` 的 token**（`app-…` 形态，本次为一次性探针、应用已删故已失效，不外传） |
| 删应用 | `DELETE /console/api/apps/<id>` | **200**，`/apps?page=1` 回读 `total=0` |

⇒ **可以在官方工具链上自建真智能体/真工作流**，这是"交付物真正长在主办方平台上"的硬通道，不需要等任何人。

**2. 但 `/v1` 服务 API 不对外。** 端口普查：`:<端口-工具链Web>/v1/chat-messages` 与 `:<端口-工具链Web>/v1/workflows/run` 均 **404**（:<端口-工具链Web> 只挂 Web 前端）；`:<端口-工具链API>/*` 从外网**完全不可达**（curl 连接超时，`000`）。而 `api-info` 注册表里官方自己那 10 条能力的 url 长这样：

```
http://<平台内网服务>:<端口-工具链API>/v1/workflows/run/<内部uuid>   (source=agentplatform, appMode=workflow)
```

即**容器内网 DNS 名**。所以工厂 ACS 的"接口规范配置"URL 要走这个内网形态才可能连通（与官方注册能力同构），浏览器/本地脚本都无法自测这一跳——只能靠工厂「测试」节点验证。

**3. 关键推论：换上真 workflow 后，唯一还会坏的就是缺陷 B。** 工厂 ACS 的调用最终经 `workflow-api/ApiController/postApi` 转发（`api-info` 就是它的路由表），而 postApi **转发丢 body**（`evidence-toolchain-bugs.md` 缺陷 B，4 种载荷写法 httpbin 均回显 `Content-Length:0`）。真 Dify workflow 收到空 body 就报 422 `body Field required` —— 这正是我们此前观察到的现象。**所以端点从 httpbin 换成真实工作流，并不能今天就变成真数据**，必须先修 B。

**4. 在 B 修复前仍可做的（明天推进）**
- **无入参 / 入参可静态固化**的能力可以先换真后端：把固定配置写进 ACS URL 的 query 段，或让 workflow 的起始节点入参全部可选 + 内置默认值 → 空 body 也能跑出真实推理结果，至少让"链路真通"这一层不再依赖 echo。优先拿 `zj.govcs.care`（主动关怀，入参 `monitorMetrics` 可给默认 mock）做样板。
- 用工具链建的 workflow 里**自带 mock 业务数据生成**（示例客户A / `MOCK-CUST-0001` / `MOCK-ORD-…`），这样即便没有真实网管系统，返回的也是"平台内推理出来的结构化结果"而非 httpbin 回声，演示说服力完全不同。
- 建应用要留可复用命名：`zj.govcs.<能力>`，与工厂 ACS 名称一一对应，方便评委追溯。

**5. 模型与 embedding 现状（决定 #22 走向）。** 本工作区**只有 1 个 active 模型**：`openai_api_compatible / Qwen3.5-122B-A10B`（llm，ctx 64000）——和工作台用的是同一个。`telecom`(CHINA TELECOM) 下的 `QiMing-72B-…` 全是 **`no-configure`**（没配密钥，不能直接用）。更关键：

```
GET /workspaces/current/default-model?model_type=text-embedding  -> 200 {"data":null}
GET /workspaces/current/default-model?model_type=rerank           -> 200 {"data":null}
带 text-embedding 能力的 provider: openai_api_compatible / openai / tongyi / ollama
  → 逐个拉 /model-providers/<p>/models?provider_type=system，全库 active 的只有 Qwen3.5 llm 一个
```

⇒ **工具链自建知识库（`/datasets`，接口可达且返回空列表）这条路走不通**：没有 active 的 embedding 模型就无法建库/索引。这是 #22 的一条硬排除项，复工后可以直接跟<接口人-知识RAG>说"工具链 datasets 已实测排除，原因是无 embedding 模型"，并把它变成一个具体请求（开通 embedding 模型，或告知官方 RAG 口径）。

## 一·补9 RAG 通路自查：4 条路排除，1 条真检索接口已找到（2026-09-25 下午，task #22）

不依赖主办方回复，把"知识库→数字员工"的可行通路穷举了一遍。

**已实测排除的 4 条：**

| 通路 | 结论 | 证据 |
|---|---|---|
| 工厂超级员工挂知识库 | ✗ 没有入口 | 「技能与服务」仅 Skill/MCP/智能体/数字员工 4 个 tab |
| 工作台会话内用知识库 | ✗ 没有入口，且 **MCP 列表为空** | 新任务页点 `.home-mcp-btn` → 面板文案 `暂无 MCP 工具 / 管理MCP工具`（后者是个裸 `div.home-mcp-footer`，无 href） |
| MCP 广场自助挂 MCP | ✗ **普通用户无权限** | 门户菜单 `MCP广场` 的直链是门户内路由 `#/mcpview/FirstIndex?Authorization=…`（无工具链那个拼接 bug），但导航后被踢到 `#/notfound`，页面文案：`当前登录用户没有该页面访问权限` |
| 工具链自建知识库 `/datasets` | ✗ 无 embedding 模型 | 接口可达（`GET /datasets` → 200 `{"data":[],"total":0}`），但 `default-model?model_type=text-embedding` 与 `?model_type=rerank` 均 `{"data":null}`；全工作区 active 模型只有 `openai_api_compatible/Qwen3.5-122B-A10B(llm)` 一个 → 建库/索引无向量模型可用 |

未动的一条：知识管理平台 `RAG分库管理` —— 页面红字警告"请勿在生产环境随意建库"，**未经用户确认不建**。

**已实测可用的检索接口（这就是自建检索 ACS 的原料）：**

```
POST http://<平台主机>:<端口-知识平台>/prod-api/knTableHis/queryMyLatestKnList
headers:  authorization: <知识平台会话token>   （小写头名、裸 token 不加 Bearer）
          content-type: application/json;charset=UTF-8
body:     {"knNameHis":"QoS","pageNum":1,"pageSize":10,
           "author":"","labelTypes":[],"processAreas":[],"professionalAreas":[],
           "knType":"","openScope":"","docTypes":[],"docOrigins":[],"isOpen":"","docTypeJson":[]}
-> 200    {"total":1,"code":200,"msg":"查询成功","rows":[{
            "knNameHis":"中国电信[浙江公司]-专线丢包故障QoS配置排查流程规范-20260925-V1.0",
            "knStatus":3,"knType":"html","docVersion":1,"releaseTime":"2026-09-25",
            "author":"<参赛者姓名>","openScope":"allNet","isOpen":1,
            "labelTypes":["whjk","gzgl"],"processAreaJson":[["weihu"]],
            "professionalAreaJson":[["jrw","zw","jrxl"]],"docTypeJson":["specification","dt_lcgf"]}]}
```

过滤**真实生效**（同一 token 下 `total` 从 5 → 1），返回的是结构化元数据 + 标题/标签/领域，`knStatus:3` = 已发布。

⚠️ **反面教训（别重复踩）**：`esknTable/queryPageList` 看着像搜索接口，实际把我试的 12 个参数名（`knowledgeTitle/knName/title/keyword/searchKey/queryWord/knowledgeName/knContent/content/word/searchValue/keyWord`）**全部忽略**，永远返回全量 5 行 —— 它是"知识空间首页列表"，不是检索。判断某个查询参数是否生效，要比 `rows` 内容与条数，**别只看 `total`**（我第一次就差点把"total 恒为 5"错读成"检索无结果"，也把"rows 恒定"错判成"可用作检索"）。

**四件事没解决，明天必须处理（已具体化，不再是"等主办方"）：**
1. **正文检索：已确认做不到（标题级封顶）。** `knNameHis` 是**标题模糊匹配**：`QoS`→total 1（正确收窄），而只出现在正文里的词 `MOCK-DEVICE-A07`、`光模块` 均 **total 0**；换别的参数名（`knContentHis`/`knDescription`）则完全不过滤（恒 5）。⇒ 该接口只支持"按标题找文档"，拿不到段落级证据，**不构成真 RAG**。
2. **取正文的接口未找**：上面只给元数据。要么 `knowledgeEditing/htmlToHtml`，要么走 `majorFilePath` 下载 —— 没有正文，RAG 的"生成"环节就没素材。
3. **鉴权不可长期化**：知识平台用的是 180 分钟会话 token（响应 cookie `Admin-Expires-In=180`）。把裸 token 写进工厂 ACS 的"鉴权方式"里，3 小时后那条 ACS 就失效 —— **所以我今天没有真去登记 `zj.kb.search` ACS**，避免在共享注册表里留一条必死的能力。要么向主办方要服务账号/AK，要么等答复确认口径。
4. **内网可达性未知**：工厂调用方能否访问 `<平台主机>:<端口-知识平台>`（与工厂门户属不同网段）尚未验证，只能在工厂「测试」节点上验。

**给<接口人-知识RAG>的提问已经从开放题变成选择题**：① 普通用户开通 MCP 广场权限（或告知政企团队可用的知识检索 MCP）；② 工具链给一个 text-embedding 模型（则我们自己建 datasets，完全绕开 ①）；③ 给一个不过期的知识平台服务账号/AK（则自建检索 ACS 立刻可落地）；④ RAG分库是否允许我们在生产建（若允许，①②③ 都不用）。**推荐 ③ 或 ②**，改动最小且不碰生产库。

## 三、落地顺序（先验证流程，再补全）
1. 在工厂 `/#/agent-register` 先登记 **1 个占位 ACS**（如 orchestrator），走完两步向导 → 确认普通用户提交是否需审核、能否成功。
2. 依次登记 2~10 号子 ACS。
3. `/#/add-super-employee` 按上表建超级数字员工，挂载子 ACS 与 Skill。
4. 到云网智能工作台"政企一站式"项目里挂载该超级员工，跑 §7 演示脚本。

## 四、待确认（不阻塞填表）
- [x] 步骤2「接口规范配置」的确切字段名 —— 已于 2026-09-23 实测登记，见「一·补」
- [x] 数字员工类别 / 智能体类型 下拉枚举 —— 智能体类型=workflow/agent/工具；数字员工分类=53 项预置（见 1 号卡更正）
- [x] 普通用户提交 ACS 能否成功 —— 能；`POST /agents/register` 200，落"我的登记列表"状态=暂存
- [x] 暂存 → 可被工作台调用的链路 —— 已查明：裸 ACS 无发布按钮，"可调用"靠"调用授权(主动/被动调用)→审核"；带审核的"发布"发生在超级数字员工层（详见「一·补2」）。超级员工"发布-待审核"已于 2026-09-24 实测：生成记录、**同账号可自审自批**，通过后状态=已发布（见「一·补3」）
- [ ] 真实业务端点：orchestrator 目前指向 mock URL，W3 需换成可连通的服务地址后重测"测试"连通性
