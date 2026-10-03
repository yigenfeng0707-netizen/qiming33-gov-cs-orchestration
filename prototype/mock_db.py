"""真库数据层：把编排能力的「硬编码 mock」换成「官方共享库 SELECT」。

对应主办方 9-27 已导入的 qiming33_mock（10 表 79 行，03_verify.sql 21 条全 PASS）。
合规红线：
  - 只读。本模块拒绝执行任何非 SELECT/WITH 开头的语句，连接级再设 READ ONLY 兜底。
  - 只用 qiming33_mock 这一个库。账号在 agent / agnet / zj_hdzz 上也有 SELECT 授权，
    那是他人赛道数据，一律不碰（connect 固定 database=，SQL 不带跨库限定名）。
  - 全表数据均为 MOCK 前缀的脱敏样例，无真实客户信息。

凭据不入库：从 Desktop/TokenAPI/qiming-mysql.txt 读取。
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

import pymysql

CRED = Path.home() / "Desktop" / "TokenAPI" / "qiming-mysql.txt"
READ_ONLY = re.compile(r"^\s*(SELECT|WITH)\b", re.I)
DEMO_DATE = "2026-09-25"      # 演示口径基准日：画像以此行为准，避免随真实时钟漂移
MAIN_CUST = "MOCK-CUST-0001"  # 演示主客户
MAIN_ORDER = "MOCK-ORD-20260925-001"


def read_credentials() -> dict:
    kv = dict(re.findall(r"^(\w+):[ \t]*(.*?)[ \t]*$", CRED.read_text(encoding="utf-8"), re.M))
    host, port, database = re.search(r"//([\d.]+):(\d+)/(\w+)", kv["url"]).groups()
    return {"host": host, "port": int(port), "user": kv["user"], "password": kv["password"],
            "database": database, "charset": "utf8mb4", "connect_timeout": 12}


@dataclass
class MockDb:
    """一次演示一个连接；记录每条命中的 SQL，录屏时可展示「数字来自查询而非硬编码」。"""
    _conn: pymysql.connections.Connection
    schema: str
    where: str = ""
    queries: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def connect(cls) -> "MockDb":
        cred = read_credentials()
        conn = pymysql.connect(**cred)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()")
            if cur.fetchone()[0] < 10:
                raise RuntimeError("qiming33_mock 表数不足：主办方尚未导入或已回收")
            cur.execute("SET SESSION TRANSACTION READ ONLY")
        return cls(_conn=conn, schema=cred["database"],
                   where=f"{cred['database']}@{cred['host']}:{cred['port']} 用户 {cred['user']}")

    def close(self) -> None:
        self._conn.close()

    def q(self, sql: str, args=()) -> list[dict]:
        if not READ_ONLY.match(sql):
            raise PermissionError(f"拒绝非只读语句: {sql[:40]}")
        stmt = " ".join(sql.split())
        # 定位/变更两支并发跑，同一连接须串行化；空 args 要转 None，否则 pymysql 仍去格式化 LIKE 'MOCK-%'
        with self._lock, self._conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(stmt, args or None)
            rows = cur.fetchall()
        self.queries.append((stmt, args, len(rows)))
        return rows

    def one(self, sql: str, args=()) -> dict:
        return self.q(sql, args)[0]

    def anchor(self) -> dict:
        return self.one(
            "SELECT c.cust_code, c.cust_name, c.region, c.main_product, c.service_level,"
            "       ci.circuit_id, ci.circuit_name, ci.bandwidth_mbps, ci.qos_profile"
            "  FROM mock_customer c JOIN mock_circuit ci ON ci.cust_code = c.cust_code"
            " WHERE c.cust_code = %s ORDER BY ci.circuit_id LIMIT 1", [MAIN_CUST])


# ============================ 与工厂 ACS 对应的只读查询 ============================

def proposal(db: MockDb, ctx: dict) -> dict:
    a = db.anchor()
    return {"plan": f"{a['main_product']} 技术方案 v1",
            "sla": f"{a['service_level']} 服务等级，RTO 35 分钟",
            "items": [a["circuit_name"], f"{a['bandwidth_mbps']}M", "云主机 4C8G", "QoS 策略"],
            "customer": a["cust_name"], "region": a["region"]}


def precheck(db: MockDb, ctx: dict) -> dict:
    """资源预评估：查目标订单端口快照。无快照视为"无法评估"，不能当成通过。"""
    rows = db.q("SELECT port_name, vlan, available_t1, available_now, note"
                "  FROM mock_resource_snapshot WHERE order_id = %s ORDER BY snapshot_id",
                [MAIN_ORDER])
    if not rows:
        return {"ok": False, "resList": {}, "lackRes": ["无资源快照，无法预评估"]}
    lack = [r["port_name"] for r in rows if r["available_now"] == 0]
    return {"ok": not lack, "resList": rows[0], "lackRes": lack}


def order(db: MockDb, ctx: dict) -> dict:
    o = db.one("SELECT order_id, current_node, stuck, escalate_to, product_desc"
               "  FROM mock_order WHERE order_id = %s", [MAIN_ORDER])
    return {"orderId": o["order_id"], "node": o["current_node"], "stuck": bool(o["stuck"]),
            "escalate_to": o["escalate_to"], "product": o["product_desc"]}


def stuck(db: MockDb, ctx: dict) -> dict:
    rows = db.q("SELECT s.port_name, s.available_t1, s.available_now, s.note,"
                "       o.escalate_to, o.stuck_reason"
                "  FROM mock_order o JOIN mock_resource_snapshot s ON s.order_id = o.order_id"
                " WHERE o.order_id = %s", [MAIN_ORDER])
    dirty = [r for r in rows if r["available_t1"] == 0 and r["available_now"] > 0]
    return {"resolved": not dirty,
            "reason": rows[0]["stuck_reason"],
            "detail": (f"{rows[0]['note']}：T+1 快照 available_t1=0，刷新后 "
                       f"available_now={dirty[0]['available_now']}（端口 {dirty[0]['port_name']}）")
                      if dirty else "快照与实时一致，无脏数据",
            "escalate_to": rows[0]["escalate_to"],
            "actions_taken": ["资源快照刷新", "同环设备复用校验", "临时端口预占"]}


def faultloc(db: MockDb, ctx: dict) -> dict:
    dev = db.one("SELECT device_code, device_name, qos_configured_mbps, qos_actual_mbps"
                 "  FROM mock_device WHERE qos_configured_mbps <> qos_actual_mbps")
    alm = db.one("SELECT alarm_id, metric_name, metric_value, unit, severity"
                 "  FROM mock_alarm WHERE device_code = %s AND severity = 'P1'"
                 " ORDER BY first_time DESC LIMIT 1", [dev["device_code"]])
    return {"cause": f"QoS 策略配置 {dev['qos_configured_mbps']}M 与实测 "
                     f"{dev['qos_actual_mbps']}M 不匹配",
            "device": dev["device_code"], "device_name": dev["device_name"],
            "severity": alm["severity"],
            "evidence": [f"{alm['metric_name']} {alm['metric_value']}{alm['unit']}",
                         "队列 5 丢弃计数增长"],
            "alarm_id": alm["alarm_id"]}


def change(db: MockDb, ctx: dict) -> dict:
    rows = db.q("SELECT change_id, effect_on_alarm, change_scope, change_object"
                "  FROM mock_change WHERE effect_on_alarm IN ('根因','加剧')"
                " ORDER BY plan_time")
    return {"hit": len(rows) > 0,
            "changes": [{"id": r["change_id"], "effect": r["effect_on_alarm"],
                         "scope": f"{r['change_scope']}（{r['change_object']}）"} for r in rows]}


def hidden(db: MockDb, ctx: dict) -> dict:
    scanned = db.one("SELECT COUNT(*) n FROM mock_device"
                     " WHERE role = '政企接入' AND status = '在网'")["n"]
    batch = db.one("SELECT optics_batch_no, COUNT(*) n FROM mock_device"
                   " WHERE status = '在网' GROUP BY optics_batch_no"
                   " ORDER BY n DESC, optics_batch_no LIMIT 1")
    return {"scanned": scanned,
            "risks": [{"item": f"同批次光模块 {batch['optics_batch_no']} 在网数",
                       "count": batch["n"], "level": "高"}],
            "based_on": ctx.get("source", {}).get("cause", "")}


def care(db: MockDb, ctx: dict) -> dict:
    p = db.one("SELECT risk_level, churn_level, suggest, n_alarm_90d, n_ticket_90d, max_loss_pct"
               "  FROM mock_care_profile WHERE cust_code = %s AND stat_date = %s",
               [MAIN_CUST, DEMO_DATE])
    return {"riskLevel": p["risk_level"], "churn": p["churn_level"], "suggest": p["suggest"],
            "inputs": {"近90天告警": p["n_alarm_90d"], "近90天工单": p["n_ticket_90d"],
                       "最大丢包率%": float(p["max_loss_pct"])}}


def summary(db: MockDb, ctx: dict) -> dict:
    rows = db.q("SELECT kb_title FROM mock_knowledge_writeback"
                " WHERE published_state = '已发布' ORDER BY writeback_time")
    return {"closed": True, "writeback": [r["kb_title"] for r in rows],
            "kb_published": len(rows)}


CAPS = {"zj.govcs.proposal": proposal, "zj.govcs.precheck": precheck, "zj.govcs.order": order,
        "zj.govcs.stuck": stuck, "zj.govcs.faultloc": faultloc, "zj.govcs.change": change,
        "zj.govcs.hidden": hidden, "zj.govcs.care": care, "zj.govcs.summary": summary}
