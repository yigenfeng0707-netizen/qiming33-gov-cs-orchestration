"""启明杯 3-3 政企客户一站式服务编排 —— 编排内核参考实现（脱敏 mock）

对齐 solution-3-3.md §8 伪代码：阶段识别 + 状态机 + 跨专业并行/串行调度。
本文件是可开源的"设计与源码"部分，不替代数字员工工厂注册（合规载体仍是工厂 ACS + 员工25）。
"""

from __future__ import annotations

import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

# ---------------------------------------------------------------- mock 数据（禁止真实客户信息）
# 两条链路分属不同客户，与主办方库 qiming33_mock 的实际归属一致：
#   售后故障链 示例客户A / MOCK-CIR-0001 / MOCK-DEVICE-A07；售中卡单链 示例客户I / MOCK-CIR-0010
CUSTOMER = {"custCode": "MOCK-CUST-0001", "custName": "示例客户A", "product": "100M 政务云专线 + 云主机"}
FAULT = {"circuit": "MOCK-CIR-0001", "device": "MOCK-DEVICE-A07", "region": "浙江"}
STUCK_ORDER = {"orderId": "MOCK-ORD-20260925-001", "custCode": "MOCK-CUST-0009", "custName": "示例客户I"}

# ---------------------------------------------------------------- ACS 传输层
# 真环境：POST 到工厂登记的 ACS 端点。工具链 postApi 转发丢 body 修复前，这里保持本地 mock。
@dataclass
class AcsTransport:
    latency: tuple[float, float] = (0.25, 0.55)
    handlers: dict | None = None          # None → 本地 HANDLERS；传入则整条链路换数据源
    _log: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def dispatch(self, code: str, payload: dict) -> dict:
        cost = random.uniform(*self.latency)
        rec = {"acs": code, "t0": time.monotonic(), "payload": payload}
        time.sleep(cost)
        rec["t1"] = time.monotonic()
        out = (self.handlers or HANDLERS)[code](payload, cost)
        rec["result"] = out
        with self._lock:
            self._log.append(rec)
        return {**out, "_acs": code, "_cost": round(cost, 3)}


# ---------------------------------------------------------------- 十个能力（与工厂 ACS 一一对应）
HANDLERS: dict[str, callable] = {}


def capability(code):
    def deco(fn):
        HANDLERS[code] = fn
        return fn
    return deco


@capability("zj.govcs.proposal")
def _proposal(ctx, cost):
    return {"ok": True, "plan": f"{CUSTOMER['product']} 技术方案 v1",
            "sla": "RTO 35 分钟", "items": ["专线接入", "云主机 4C8G", "QoS 策略"]}


@capability("zj.govcs.precheck")
def _precheck(ctx, cost):
    return {"ok": True, "resList": {"port": "GE/1/0/3", "vlan": 2011}, "lackRes": []}


@capability("zj.govcs.order")
def _order(ctx, cost):
    return {"orderId": STUCK_ORDER["orderId"], "node": "资源配置确认", "stuck": ctx.get("force_stuck", False)}


@capability("zj.govcs.stuck")
def _stuck(ctx, cost):
    return {"resolved": False, "reason": "资源未到位", "detail": "T+1 资源快照导致端口可用数显示为 0",
            "escalate_to": "L2 跨专业处置", "actions_taken": ["资源快照刷新", "同环设备复用校验", "临时端口预占"]}


@capability("zj.govcs.faultloc")
def _faultloc(ctx, cost):
    return {"cause": "QoS 策略与实际带宽不匹配", "device": FAULT["device"], "severity": "P1",
            "evidence": ["入向丢包 3.2%", "队列 5 丢弃计数增长"]}


@capability("zj.govcs.change")
def _change(ctx, cost):
    return {"hit": True, "changes": [{"id": "CHG-20260925-001", "effect": "加剧", "scope": "QoS 模板下发"},
                                     {"id": "CHG-20260924-002", "effect": "根因", "scope": "光模块批次替换"}]}


@capability("zj.govcs.hidden")
def _hidden(ctx, cost):
    return {"scanned": 19, "risks": [{"item": "同批次光模块在网数", "count": 7, "level": "高"}],
            "based_on": ctx.get("source", {}).get("cause", "")}


@capability("zj.govcs.care")
def _care(ctx, cost):
    return {"riskLevel": "中高", "churn": "中", "suggest": "两周内安排预防性维护 + 带宽复勘"}


@capability("zj.govcs.summary")
def _summary(ctx, cost):
    return {"closed": True, "writeback": ["售中卡单资源未到位处置政企案例", "专线丢包故障QoS配置排查流程规范"]}


# ---------------------------------------------------------------- 编排内核
STAGES = ("售前", "售中", "售后")


def classify_stage(intent: str) -> str:
    if any(k in intent for k in ("故障", "丢包", "告警", "卡单", "开通")):
        return "售后" if any(k in intent for k in ("故障", "丢包", "告警")) else "售中"
    return "售前"


def fault_coordination(bus: AcsTransport, ctx: dict) -> dict:
    """技术创新点：定位 ‖ 变更并行，两者全部返回后才串行触发隐患排查。"""
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_f = pool.submit(bus.dispatch, "zj.govcs.faultloc", ctx)
        f_c = pool.submit(bus.dispatch, "zj.govcs.change", ctx)
        fault, change = f_f.result(), f_c.result()          # await_all
    hidden = bus.dispatch("zj.govcs.hidden", {"source": fault})   # 依赖定位结果
    return {"fault": fault, "change": change, "hidden": hidden}


def orchestrator(bus: AcsTransport, request: dict) -> dict:
    intent = request["intent"]
    stage = classify_stage(intent)
    trace = {"intent": intent, "stage": stage, "steps": []}

    if stage == "售前":
        trace["steps"].append(bus.dispatch("zj.govcs.proposal", request))
        pre = bus.dispatch("zj.govcs.precheck", request)
        trace["steps"].append(pre)
        if not pre["ok"]:
            trace["result"] = {"escalated": "人工兜底", "lackRes": pre["lackRes"]}
            return trace

    elif stage == "售中":
        order = bus.dispatch("zj.govcs.order", request)
        trace["steps"].append(order)
        if order["stuck"]:
            r = bus.dispatch("zj.govcs.stuck", request)
            trace["steps"].append(r)
            if not r["resolved"]:
                trace["result"] = {"escalated": r["escalate_to"], "reason": r["reason"],
                                    "actions_taken": r["actions_taken"]}
                return trace

    else:
        trace["fault_coordination"] = fault_coordination(bus, request)
        trace["steps"] += [trace["fault_coordination"][k] for k in ("fault", "change", "hidden")]

    if request.get("proactive"):
        trace["steps"].append(bus.dispatch("zj.govcs.care", request))

    trace["result"] = bus.dispatch("zj.govcs.summary", request)
    return trace


# ---------------------------------------------------------------- 时序自检 + 演示
def verify_parallel_then_serial(bus: AcsTransport) -> list[str]:
    log = {r["acs"]: r for r in bus._log}
    f, c, h = log["zj.govcs.faultloc"], log["zj.govcs.change"], log["zj.govcs.hidden"]
    carried = h["payload"].get("source")
    checks = [
        ("故障定位与变更排查时间窗重叠（真并行）", f["t0"] < c["t1"] and c["t0"] < f["t1"]),
        ("隐患排查在两路全部返回后才启动（依赖串行）", h["t0"] >= max(f["t1"], c["t1"]) - 1e-6),
        ("隐患排查入参即故障定位的返回值（数据依赖成立，非仅时间先后）",
         isinstance(carried, dict)
         and carried.get("_acs") == "zj.govcs.faultloc"
         and all(carried.get(k) == v for k, v in f["result"].items())),
    ]
    return [f"{'PASS' if ok else 'FAIL'}  {name}" for name, ok in checks]


def show_timeline(trace: dict) -> None:
    print(f"\n意图: {trace['intent']}")
    print(f"阶段识别: {trace['stage']}")
    for s in trace["steps"]:
        cost = s.get("_cost")
        print(f"  - {s.get('_acs', '?'):<26} {cost}s  "
              + json.dumps({k: v for k, v in s.items() if k not in ('_acs', '_cost')},
                           ensure_ascii=False)[:110])
    if "fault_coordination" in trace:
        print("  ★ 并行→串行时序已验证（见下方自检）")
    print(f"  结果: {json.dumps(trace['result'], ensure_ascii=False)[:180]}")


def main() -> int:
    random.seed(20260925)
    live = "--db" in sys.argv
    print("=" * 78)
    print("启明杯 3-3｜政企客户一站式服务编排｜本地参考实现（脱敏 mock，不替代工厂注册）"
          if not live else
          "启明杯 3-3｜政企客户一站式服务编排｜数据源 = 主办方共享库 qiming33_mock（只读）")
    print("=" * 78)

    bus = AcsTransport()
    db = None
    if live:
        from mock_db import CAPS, MockDb
        db = MockDb.connect()
        bus.handlers = {code: (lambda p, c, f=fn: f(db, p)) for code, fn in CAPS.items()}
        print(f"数据源：{db.where}  授权：仅 SELECT\n")

    for req in (
        {"intent": "示例客户A 申请 100M 政务云专线 + 云主机，请受理并给出方案与资源预评估", "proactive": False},
        {"intent": "示例客户I 的订单 MOCK-ORD-20260925-001 已受理，跟踪开通进度（端口资源未到位卡单）",
         "force_stuck": True, "proactive": False},
        {"intent": "示例客户A 的专线 MOCK-CIR-0001 出现持续丢包告警，请排查", "proactive": True},
    ):
        t0 = time.monotonic()
        trace = orchestrator(bus, req)
        trace["_wall"] = round(time.monotonic() - t0, 2)
        show_timeline(trace)
        print(f"  墙钟: {trace['_wall']}s")
        if "fault_coordination" in trace:
            print("\n  调度时序自检:")
            for line in verify_parallel_then_serial(bus):
                print("   ", line)
    print("\n注：真环境单步响应 130–200s（平台侧模型推理），本壳仅验证编排逻辑与时序约束。")
    if db:
        print(f"\n本次演示共向真库发出 {len(db.queries)} 条只读查询：")
        for sql, args, n in db.queries:
            print(f"  [{n:>2} 行] {sql[:96]}"
                  + (f"  ← {args}" if args else ""))
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
