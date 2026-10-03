-- ============================================================
-- 03_verify.sql —— 启明杯 3-3 mock 库自检（导入后执行，全 PASS 即数据可用（当前 21 条））
--
-- 设计原则：方案演示里报出的每一个数字（19 台在网 / 7 台同批次 / 丢包 3.20% /
-- 两条变更 T+1 快照）都必须能从本库 SELECT 复算出来。
-- 若某行 FAIL，说明导入的数据与路演口径不一致，请回传差异给我们。
-- ============================================================
USE qiming33_mock;
SET NAMES utf8mb4;

SELECT '01 客户主档 10 户' AS check_item,
       CASE WHEN COUNT(*) = 10 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END AS result
  FROM mock_customer
UNION ALL SELECT '02 专线电路 10 条',
       CASE WHEN COUNT(*) = 10 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_circuit
UNION ALL SELECT '03 政企接入设备在网 19 台（隐患排查扫描范围）',
       CASE WHEN COUNT(*) = 19 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_device WHERE role = '政企接入' AND status = '在网'
UNION ALL SELECT '04 同批次光模块 OPTIC-B2024-07 在网 7 台（隐患数）',
       CASE WHEN COUNT(*) = 7 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_device WHERE optics_batch_no = 'OPTIC-B2024-07' AND status = '在网'
UNION ALL SELECT '05 QoS 策略与实测带宽不匹配的设备恰为 MOCK-DEVICE-A07（故障根因）',
       CASE WHEN COUNT(*) = 1 AND MAX(device_code) = 'MOCK-DEVICE-A07' THEN 'PASS'
            ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_device WHERE qos_configured_mbps <> qos_actual_mbps
UNION ALL SELECT '06 主卡单工单存在且需升级 L2',
       CASE WHEN COUNT(*) = 1 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_order
 WHERE order_id = 'MOCK-ORD-20260925-001' AND stuck = 1 AND escalate_to = 'L2 跨专业处置'
UNION ALL SELECT '07 卡单根因可复算：T+1 快照=0 而刷新后>0',
       CASE WHEN COUNT(*) = 1 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_resource_snapshot
 WHERE order_id = 'MOCK-ORD-20260925-001' AND available_t1 = 0 AND available_now > 0
UNION ALL SELECT '08 入向丢包率 3.20% 的 P1 告警挂在 MOCK-DEVICE-A07',
       CASE WHEN COUNT(*) = 1 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_alarm
 WHERE device_code = 'MOCK-DEVICE-A07' AND metric_name = '入向丢包率'
   AND metric_value = 3.20 AND severity = 'P1'
UNION ALL SELECT '09 变更排查支路命中 2 条（1 根因 + 1 加剧）',
       CASE WHEN COUNT(*) = 2 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_change
 WHERE effect_on_alarm IN ('根因', '加剧')
   AND change_id IN ('CHG-20260924-002', 'CHG-20260925-001')
UNION ALL SELECT '10 示例客户A 近 90 天告警 5 条（主动服务画像输入）',
       CASE WHEN COUNT(*) = 5 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_alarm a JOIN mock_circuit c ON a.circuit_id = c.circuit_id
 WHERE c.cust_code = 'MOCK-CUST-0001'
   AND a.first_time >= DATE_SUB('2026-09-26', INTERVAL 90 DAY)
UNION ALL SELECT '11 示例客户A 画像=风险中高/流失中（care 输出）',
       CASE WHEN COUNT(*) = 1 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_care_profile
 WHERE cust_code = 'MOCK-CUST-0001' AND risk_level = '中高' AND churn_level = '中'
UNION ALL SELECT '12 知识回写台账 5 条全部"已发布"',
       CASE WHEN COUNT(*) = 5 AND SUM(published_state = '已发布') = 5 THEN 'PASS' ELSE 'FAIL' END
  FROM mock_knowledge_writeback
UNION ALL SELECT '13 引用完整性：电路→客户无孤儿',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_circuit c LEFT JOIN mock_customer k ON c.cust_code = k.cust_code WHERE k.cust_code IS NULL
UNION ALL SELECT '14 引用完整性：电路两端设备均存在于台账',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_circuit c
  LEFT JOIN mock_device d1 ON c.a_end_device = d1.device_code
  LEFT JOIN mock_device d2 ON c.z_end_device = d2.device_code
 WHERE d1.device_code IS NULL OR d2.device_code IS NULL
UNION ALL SELECT '15 引用完整性：工单/告警/快照/画像/历史单的客户键均可解析',
       CASE WHEN (SELECT COUNT(*) FROM mock_order o LEFT JOIN mock_customer k ON o.cust_code=k.cust_code WHERE k.cust_code IS NULL)
              + (SELECT COUNT(*) FROM mock_ticket t LEFT JOIN mock_customer k ON t.cust_code=k.cust_code WHERE k.cust_code IS NULL)
              + (SELECT COUNT(*) FROM mock_care_profile p LEFT JOIN mock_customer k ON p.cust_code=k.cust_code WHERE k.cust_code IS NULL)
              + (SELECT COUNT(*) FROM mock_alarm a LEFT JOIN mock_circuit c ON a.circuit_id=c.circuit_id WHERE c.circuit_id IS NULL)
              + (SELECT COUNT(*) FROM mock_resource_snapshot s LEFT JOIN mock_order o ON s.order_id=o.order_id WHERE o.order_id IS NULL)
                = 0 THEN 'PASS' ELSE 'FAIL' END
  FROM DUAL
UNION ALL SELECT '16 告警指标均可解析到设备台账',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE CONCAT('FAIL: ', COUNT(*)) END
  FROM mock_alarm a LEFT JOIN mock_device d ON a.device_code = d.device_code WHERE d.device_code IS NULL
UNION ALL SELECT '17 涉密字段自查：无任何 11 位手机号形态取值',
       CASE WHEN (SELECT COUNT(*) FROM mock_customer WHERE contract_no REGEXP '^1[3-9][0-9]{9}$')
              + (SELECT COUNT(*) FROM mock_device WHERE room REGEXP '^1[3-9][0-9]{9}$')
              + (SELECT COUNT(*) FROM mock_ticket WHERE title REGEXP '1[3-9][0-9]{9}') = 0
            THEN 'PASS' ELSE 'FAIL' END
  FROM DUAL
UNION ALL SELECT '18 涉密字段自查：真实 IP 形态取值 0 条',
       CASE WHEN (SELECT COUNT(*) FROM mock_device WHERE room REGEXP '([0-9]{1,3}\\.){3}[0-9]{1,3}')
              + (SELECT COUNT(*) FROM mock_ticket WHERE title REGEXP '([0-9]{1,3}\\.){3}[0-9]{1,3}') = 0
            THEN 'PASS' ELSE 'FAIL' END
  FROM DUAL
UNION ALL SELECT '19 全部客户编码均为 MOCK 前缀（可一眼判定脱敏）',
       CASE WHEN SUM(cust_code NOT LIKE 'MOCK-CUST-%') = 0 THEN 'PASS' ELSE 'FAIL' END
  FROM mock_customer
UNION ALL SELECT '20 演示主链路 6 个关键标识齐备',
       CASE WHEN (SELECT COUNT(*) FROM mock_customer WHERE cust_code='MOCK-CUST-0001')
              + (SELECT COUNT(*) FROM mock_circuit WHERE circuit_id='MOCK-CIR-0001')
              + (SELECT COUNT(*) FROM mock_order WHERE order_id='MOCK-ORD-20260925-001')
              + (SELECT COUNT(*) FROM mock_device WHERE device_code='MOCK-DEVICE-A07')
              + (SELECT COUNT(*) FROM mock_change WHERE change_id='CHG-20260925-001')
              + (SELECT COUNT(*) FROM mock_alarm WHERE alarm_id='MOCK-ALM-0001') = 6
            THEN 'PASS' ELSE 'FAIL' END
  FROM DUAL
UNION ALL SELECT '21 画像三值可由明细复算（告警数/工单数/最大丢包率）',
       CASE WHEN p.n_alarm_90d = x.n_alm AND p.n_ticket_90d = y.n_tkt AND p.max_loss_pct = z.mx
            THEN 'PASS' ELSE CONCAT('FAIL: ', p.n_alarm_90d, '/', x.n_alm, ' ',
                                    p.n_ticket_90d, '/', y.n_tkt, ' ',
                                    p.max_loss_pct, '/', z.mx) END
  FROM mock_care_profile p
  JOIN (SELECT c.cust_code, COUNT(*) n_alm
          FROM mock_alarm a JOIN mock_circuit c ON a.circuit_id=c.circuit_id
         WHERE a.first_time >= DATE_SUB('2026-09-26', INTERVAL 90 DAY)
         GROUP BY c.cust_code) x ON x.cust_code = p.cust_code
  JOIN (SELECT cust_code, COUNT(*) n_tkt FROM mock_ticket
         WHERE create_time >= DATE_SUB('2026-09-26', INTERVAL 90 DAY)
         GROUP BY cust_code) y ON y.cust_code = p.cust_code
  JOIN (SELECT c.cust_code, MAX(a.metric_value) mx
          FROM mock_alarm a JOIN mock_circuit c ON a.circuit_id=c.circuit_id
         WHERE a.metric_name = '入向丢包率'
         GROUP BY c.cust_code) z ON z.cust_code = p.cust_code
 WHERE p.stat_date = '2026-09-25' AND p.cust_code = 'MOCK-CUST-0001';

-- ---------- 路演现场可直接敲的三条业务查询（非自检）----------
-- ① 售后·隐患排查扫描范围（对应 zj.govcs.hidden 输出 19 / 7）
--    SELECT COUNT(*) AS scanned FROM mock_device WHERE role='政企接入' AND status='在网';
--    SELECT COUNT(*) AS same_batch FROM mock_device WHERE optics_batch_no='OPTIC-B2024-07';
-- ② 售中·卡单是否可自动解（对应 zj.govcs.stuck 输出 resolved=false）
--    SELECT o.order_id, s.port_name, s.available_t1, s.available_now, o.escalate_to
--      FROM mock_order o JOIN mock_resource_snapshot s ON s.order_id=o.order_id
--     WHERE o.order_id='MOCK-ORD-20260925-001';
-- ③ 主动服务·每日 09:00 巡检该看谁
--    SELECT p.cust_code, k.cust_name, p.risk_level, p.churn_level, p.suggest
--      FROM mock_care_profile p JOIN mock_customer k ON k.cust_code=p.cust_code
--     WHERE p.risk_level IN ('高','中高') ORDER BY p.n_alarm_90d DESC;
