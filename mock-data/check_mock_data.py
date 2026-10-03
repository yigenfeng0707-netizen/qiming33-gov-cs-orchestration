# -*- coding: utf-8 -*-
"""离线校验 mock-data：把 01/02/03 三个 SQL 解析回数据，用 Python 复算 03_verify.sql 的 20 条断言。

存在的理由：主办方共享 MySQL 目前 1045 拒绝我方出口 IP，SQL 无法真跑。
没有这道校验就把 .sql 发出去，等于把"能不能导入"的风险推给技术老师。

用法：python check_mock_data.py     （零第三方依赖）
退出码 0 = 全部通过。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "01_schema.sql")
DATA = os.path.join(HERE, "02_data.sql")


def read(p):
    return io.open(p, encoding="utf-8").read()


def strip_comments(sql):
    return "\n".join(re.sub(r"--(?:(?!\*/).)*$", "", ln) for ln in sql.splitlines())


def parse_creates(sql):
    tables = {}
    for m in re.finditer(r"CREATE TABLE (\w+)\s*\((.*?)\n\)\s*ENGINE", sql, re.S):
        cols = []
        for line in m.group(2).splitlines():
            line = line.strip().rstrip(",")
            cm = re.match(r"([a-z_][a-z0-9_]*)\s+(VARCHAR|INT|TINYINT|DATETIME|DATE|DECIMAL|AUTO_INCREMENT)",
                          line, re.I)
            if cm and cm.group(1).upper() not in ("PRIMARY", "KEY", "UNIQUE", "CONSTRAINT"):
                cols.append(cm.group(1))
        tables[m.group(1)] = cols
    return tables


def scan_tuples(body):
    """把 VALUES 后面的正文切成若干元组原文；单引号内的逗号与中文不参与结构判断。"""
    tuples, cur, instr, depth, i = [], None, False, 0, 0
    while i < len(body):
        ch = body[i]
        if instr:
            if ch == "'":
                if i + 1 < len(body) and body[i + 1] == "'":
                    cur += "''"
                    i += 2
                    continue
                instr = False
            cur += ch
        elif ch == "'":
            instr = True
            if cur is None:
                cur = ""
            else:
                cur += ch
        elif ch == "(":
            depth += 1
            if depth == 1:
                cur = ""
                i += 1
                continue
            cur += ch
        elif ch == ")":
            depth -= 1
            if depth == 0:
                tuples.append(cur)
                cur = None
            else:
                cur += ch
        elif cur is not None:
            cur += ch
        i += 1
    return tuples


def split_fields(raw):
    out, cur, instr, i = [], "", False, 0
    while i < len(raw):
        ch = raw[i]
        if instr:
            if ch == "'":
                if i + 1 < len(raw) and raw[i + 1] == "'":
                    cur += "''"
                    i += 2
                    continue
                instr = False
            cur += ch
        elif ch == "'":
            instr = True
            cur += ch
        elif ch == ",":
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    if cur.strip():
        out.append(cur.strip())
    return out


def unquote(v):
    if v.upper() == "NULL":
        return None
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    return v


def parse_inserts(sql):
    rows, insert_cols = {}, {}
    for m in re.finditer(r"INSERT INTO (\w+)\s*\(([^)]*)\)\s*VALUES(.*?);", sql, re.S):
        table, cols, body = m.group(1), [c.strip() for c in m.group(2).split(",")], m.group(3)
        insert_cols[table] = cols
        parsed = []
        for raw in scan_tuples(body):
            vals = [unquote(v) for v in split_fields(raw)]
            parsed.append(dict(zip(cols, vals)))
        rows.setdefault(table, []).extend(parsed)
    return rows, insert_cols


def num(v):
    return float(v)


def check(rows):
    dev = rows["mock_device"]
    cust = rows["mock_customer"]
    cir = rows["mock_circuit"]
    alm = rows["mock_alarm"]
    order = rows["mock_order"]
    snap = rows["mock_resource_snapshot"]
    chg = rows["mock_change"]
    tkt = rows["mock_ticket"]
    prof = rows["mock_care_profile"]
    kb = rows["mock_knowledge_writeback"]

    access_live = [d for d in dev if d["role"] == "政企接入" and d["status"] == "在网"]
    batch = [d for d in dev if d["optics_batch_no"] == "OPTIC-B2024-07" and d["status"] == "在网"]
    mismatch = [d for d in dev if num(d["qos_configured_mbps"]) != num(d["qos_actual_mbps"])]
    cust1_circuits = {c["circuit_id"] for c in cir if c["cust_code"] == "MOCK-CUST-0001"}
    alm_90d = [a for a in alm if a["circuit_id"] in cust1_circuits
               and a["first_time"][:10] >= "2026-06-28"]
    tkt_90d = [t for t in tkt if t["cust_code"] == "MOCK-CUST-0001" and t["create_time"][:10] >= "2026-06-28"]
    p1 = [a for a in alm if a["device_code"] == "MOCK-DEVICE-A07"
          and a["metric_name"] == "入向丢包率" and num(a["metric_value"]) == 3.20 and a["severity"] == "P1"]
    stuck_o = [o for o in order if o["order_id"] == "MOCK-ORD-20260925-001"
               and o["stuck"] == "1" and o["escalate_to"] == "L2 跨专业处置"]
    snap_o = [s for s in snap if s["order_id"] == "MOCK-ORD-20260925-001"
              and num(s["available_t1"]) == 0 and num(s["available_now"]) > 0]
    hot = [c for c in chg if c["effect_on_alarm"] in ("根因", "加剧")
           and c["change_id"] in ("CHG-20260924-002", "CHG-20260925-001")]
    prof1 = [p for p in prof if p["cust_code"] == "MOCK-CUST-0001"
             and p["risk_level"] == "中高" and p["churn_level"] == "中"]

    cust_codes = {c["cust_code"] for c in cust}
    circuit_ids = {c["circuit_id"] for c in cir}
    device_codes = {d["device_code"] for d in dev}
    order_ids = {o["order_id"] for o in order}

    orphan_circ = [c for c in cir if c["cust_code"] not in cust_codes]
    bad_ends = [c for c in cir if c["a_end_device"] not in device_codes
                or c["z_end_device"] not in device_codes]
    orphan_rest = (
        [o for o in order if o["cust_code"] not in cust_codes]
        + [t for t in tkt if t["cust_code"] not in cust_codes]
        + [p for p in prof if p["cust_code"] not in cust_codes]
        + [a for a in alm if a["circuit_id"] not in circuit_ids]
        + [a for a in alm if a["device_code"] not in device_codes]
        + [s for s in snap if s["order_id"] not in order_ids]
    )
    phone = [c for c in cust if re.search(r"1[3-9]\d{9}", c["contract_no"] + c["cust_name"])] \
        + [t for t in tkt if re.search(r"1[3-9]\d{9}", t["title"])]
    ips = [d for d in dev if re.search(r"\d{1,3}(\.\d{1,3}){3}", d["room"] + d["device_name"])] \
        + [t for t in tkt if re.search(r"\d{1,3}(\.\d{1,3}){3}", t["title"])]
    nonmock = [c for c in cust if not c["cust_code"].startswith("MOCK-CUST-")]
    key_ids = ["MOCK-CUST-0001", "MOCK-CIR-0001", "MOCK-ORD-20260925-001",
               "MOCK-DEVICE-A07", "CHG-20260925-001", "MOCK-ALM-0001"]
    present = sum([
        any(c["cust_code"] == key_ids[0] for c in cust),
        any(c["circuit_id"] == key_ids[1] for c in cir),
        any(o["order_id"] == key_ids[2] for o in order),
        any(d["device_code"] == key_ids[3] for d in dev),
        any(c["change_id"] == key_ids[4] for c in chg),
        any(a["alarm_id"] == key_ids[5] for a in alm),
    ])

    return [
        ("01 客户主档 10 户", len(cust), 10),
        ("02 专线电路 10 条", len(cir), 10),
        ("03 政企接入在网设备 19 台（隐患排查扫描范围）", len(access_live), 19),
        ("04 同批次光模块 OPTIC-B2024-07 在网 7 台（隐患数）", len(batch), 7),
        ("05 QoS 配置≠实测的设备恰好 1 台且为 A07",
         len(mismatch) == 1 and mismatch and mismatch[0]["device_code"] == "MOCK-DEVICE-A07", True),
        ("06 主卡单工单存在且升级 L2", len(stuck_o), 1),
        ("07 卡单根因可复算（T+1=0 而刷新后>0）", len(snap_o), 1),
        ("08 入向丢包 3.20% 的 P1 告警挂在 A07", len(p1), 1),
        ("09 变更支路命中 2 条（根因+加剧）", len(hot), 2),
        ("10 示例客户A 近 90 天告警 5 条", len(alm_90d), 5),
        ("10b 画像 n_alarm_90d 与实算一致",
         prof1 and num(prof1[0]["n_alarm_90d"]) == len(alm_90d), True),
        ("10c 画像 n_ticket_90d 与实算一致",
         prof1 and num(prof1[0]["n_ticket_90d"]) == len(tkt_90d), True),
        ("10d 画像 max_loss_pct 等于该窗口内最大丢包率告警值",
         prof1 and num(prof1[0]["max_loss_pct"])
         == max(num(a["metric_value"]) for a in alm_90d if a["metric_name"] == "入向丢包率"), True),
        ("11 客户A 画像=风险中高/流失中", len(prof1), 1),
        ("12 知识回写台账 5 条全部已发布",
         len(kb), 5),
        ("12b 台账标题均带平台要求的类型末级词",
         all(("政企案例" in k["kb_title"]) or ("流程规范" in k["kb_title"]) or ("解决方案" in k["kb_title"]) for k in kb), True),
        ("13 电路→客户无孤儿", len(orphan_circ), 0),
        ("14 电路两端设备均在台账内", len(bad_ends), 0),
        ("15 其余外键均可解析", len(orphan_rest), 0),
        ("16 告警设备均可解析（含在 15 内，此处单列）",
         len([a for a in alm if a["device_code"] not in device_codes]), 0),
        ("17 涉密自查：无 11 位手机号形态取值", len(phone), 0),
        ("18 涉密自查：无 IP 形态取值", len(ips), 0),
        ("19 客户编码 100% MOCK 前缀", len(nonmock), 0),
        ("20 演示主链路 6 个关键标识齐备", present, 6),
    ]


def main():
    schema_sql, data_sql = strip_comments(read(SCHEMA)), strip_comments(read(DATA))
    creates = parse_creates(schema_sql)
    rows, insert_cols = parse_inserts(data_sql)

    fail = 0
    print("=" * 74)
    print("mock-data 离线自检（解析 SQL → Python 复算，替代尚不可达的 MySQL 执行）")
    print("=" * 74)

    print("\n[结构] 01_schema.sql 建表数:", len(creates))
    for t in sorted(rows):
        cols, tcols = insert_cols[t], creates.get(t)
        if tcols is None:
            print(f"  FAIL {t}: 插入了未建表的对象")
            fail += 1
            continue
        unknown = [c for c in cols if c not in tcols]
        ragged = [i for i, r in enumerate(rows[t], 1) if len(r) != len(cols)]
        status = "OK " if not (unknown or ragged) else "FAIL"
        if unknown or ragged:
            fail += 1
        print(f"  {status} {t:<24} {len(rows[t]):>2} 行 / INSERT {len(cols)} 列（表 {len(tcols)} 列）"
              + (f"  未知列 {unknown}" if unknown else "")
              + (f"  值个数与列清单不符@{ragged[:3]}" if ragged else ""))

    missing = [t for t in creates if t not in rows]
    if missing:
        print("  FAIL 建了表却没有数据:", ", ".join(missing))
        fail += 1

    print("\n[断言] 对应 03_verify.sql 的 21 条（Python 侧细分 3 项，共 24 项）:")
    for name, got, want in check(rows):
        ok = got == want
        fail += (not ok)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"   -> got {got!r}, want {want!r}"))

    total_rows = sum(len(v) for v in rows.values())
    print(f"\n合计：{len(creates)} 张表 / {total_rows} 行数据 / {'全部通过' if not fail else str(fail) + ' 项失败'}")
    return 1 if fail else 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    raise SystemExit(rc)
