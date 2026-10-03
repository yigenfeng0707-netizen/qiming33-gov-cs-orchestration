"""对主办方已导入的真实库执行 03_verify.sql，逐条打印 21 项结果。

数据层复用 prototype/mock_db.py（同一份凭据解析 + 只读约束），本文件自身不写任何语句。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "prototype"))
from mock_db import MockDb  # noqa: E402

HERE = Path(__file__).resolve().parent


def main() -> int:
    sql = re.sub(r"^\s*--.*$", "", (HERE / "03_verify.sql").read_text(encoding="utf-8"), flags=re.M)
    stmt = " ".join(next(s for s in sql.split(";") if s.strip().upper().startswith("SELECT")).split())

    db = MockDb.connect()
    meta = db.q("SELECT VERSION() ver, CURRENT_USER() usr, DATABASE() db,"
                " (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()) ntab")[0]
    checks = db.q(stmt)
    db.close()

    print("=" * 78)
    print("真实库自检：03_verify.sql（主办方 09-27 导入的 qiming33_mock）")
    print(f"  VERSION={meta['ver']}  CURRENT_USER={meta['usr']}  "
          f"DATABASE={meta['db']}  表数={meta['ntab']}")
    print("=" * 78)
    bad = 0
    for c in checks:
        name, result = c["check_item"], c["result"]
        if not result.startswith("PASS"):
            bad += 1
        print(f"  {'OK  ' if result == 'PASS' else 'FAIL'}  {result:<12} {name}")
    print(f"\n共 {len(checks)} 条，非 PASS {bad} 条")
    return 1 if bad or len(checks) != 21 else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
