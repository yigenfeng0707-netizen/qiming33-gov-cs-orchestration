-- ============================================================
-- 启明杯 AI 挑战赛 · 赛道三 赛题 3-3《政企客户一站式服务编排》
-- 脱敏 mock 业务库（供主办方技术老师统一建库导入）
--
-- 目标库：MySQL 8.0（实测服务端 8.0.45）  字符集：utf8mb4
-- 数据来源：全部为选手自编 mock，不含任何真实客户/工号/IP/手机号/邮箱
-- 导入顺序：01_schema.sql → 02_data.sql → 03_verify.sql
-- 投稿账号：<主办方接口人邮箱>
-- ============================================================

CREATE DATABASE IF NOT EXISTS qiming33_mock
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE qiming33_mock;

SET NAMES utf8mb4;

-- ---------- 1. 政企客户主档 ----------
CREATE TABLE mock_customer (
  cust_code      VARCHAR(32)  NOT NULL COMMENT '客户编码（MOCK 前缀，非真实编码）',
  cust_name      VARCHAR(64)  NOT NULL COMMENT '客户名称（示例客户A/B…，全部虚构）',
  region         VARCHAR(16)  NOT NULL COMMENT '属地',
  industry       VARCHAR(32)  NOT NULL COMMENT '行业',
  service_level  VARCHAR(16)  NOT NULL COMMENT '服务等级',
  contract_no    VARCHAR(32)  NOT NULL COMMENT '协议编号（虚构）',
  main_product   VARCHAR(128) NOT NULL COMMENT '主要在用产品',
  create_time    DATETIME     NOT NULL,
  PRIMARY KEY (cust_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='政企客户主档（mock）';

-- ---------- 2. 专线电路实例 ----------
CREATE TABLE mock_circuit (
  circuit_id      VARCHAR(32)  NOT NULL,
  cust_code       VARCHAR(32)  NOT NULL,
  circuit_name    VARCHAR(128) NOT NULL,
  bandwidth_mbps  INT          NOT NULL,
  a_end_device    VARCHAR(32)  NOT NULL,
  z_end_device    VARCHAR(32)  NOT NULL,
  qos_profile     VARCHAR(64)  NOT NULL,
  status          VARCHAR(16)  NOT NULL,
  open_date       DATE         NOT NULL,
  PRIMARY KEY (circuit_id),
  KEY idx_circuit_cust (cust_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专线电路实例（mock）';

-- ---------- 3. 设备与光模块批次（隐患排查的数据底座）----------
CREATE TABLE mock_device (
  device_code         VARCHAR(32) NOT NULL,
  device_name         VARCHAR(64) NOT NULL,
  region              VARCHAR(16) NOT NULL,
  role                VARCHAR(32) NOT NULL COMMENT '设备角色：政企接入/汇聚/核心',
  model               VARCHAR(64) NOT NULL,
  optics_batch_no     VARCHAR(32) NOT NULL COMMENT '光模块批次号（同批次扫描键）',
  qos_configured_mbps INT         NOT NULL COMMENT 'QoS 模板配置带宽',
  qos_actual_mbps     INT         NOT NULL COMMENT '实测可用带宽（与上行不等即策略不匹配）',
  room                VARCHAR(32) NOT NULL COMMENT '机房（虚构命名）',
  status              VARCHAR(16) NOT NULL,
  PRIMARY KEY (device_code),
  KEY idx_device_batch (optics_batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='网元设备台账（mock，政企接入 19 台，其中 7 台光模块同批次）';

-- ---------- 4. 开通工单（售中卡单场景）----------
CREATE TABLE mock_order (
  order_id      VARCHAR(32)  NOT NULL,
  cust_code     VARCHAR(32)  NOT NULL,
  circuit_id    VARCHAR(32)  NOT NULL,
  product_desc  VARCHAR(128) NOT NULL,
  current_node  VARCHAR(64)  NOT NULL COMMENT '当前环节',
  stuck         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1=卡单',
  stuck_reason  VARCHAR(64)      NULL,
  escalate_to   VARCHAR(64)      NULL COMMENT '升级去向',
  accept_time   DATETIME     NOT NULL,
  expect_finish DATETIME     NOT NULL,
  PRIMARY KEY (order_id),
  KEY idx_order_cust (cust_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='开通/服务工单（mock）';

-- ---------- 5. 资源快照（卡单根因：T+1 快照与实时不一致）----------
CREATE TABLE mock_resource_snapshot (
  snapshot_id    INT AUTO_INCREMENT,
  order_id       VARCHAR(32) NOT NULL,
  port_name      VARCHAR(32) NOT NULL,
  available_t1   INT         NOT NULL COMMENT 'T+1 快照可用端口数（脏数据）',
  available_now  INT         NOT NULL COMMENT '刷新后实时可用端口数',
  vlan           INT         NOT NULL,
  snapshot_date  DATE        NOT NULL,
  note           VARCHAR(128) NOT NULL,
  PRIMARY KEY (snapshot_id),
  KEY idx_snap_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资源可用数快照（mock，演示卡单根因）';

-- ---------- 6. 告警（售后故障场景证据链）----------
CREATE TABLE mock_alarm (
  alarm_id     VARCHAR(32) NOT NULL,
  circuit_id   VARCHAR(32) NOT NULL,
  device_code  VARCHAR(32) NOT NULL,
  alarm_type   VARCHAR(32) NOT NULL,
  metric_name  VARCHAR(32) NOT NULL,
  metric_value DECIMAL(8,2) NOT NULL,
  unit         VARCHAR(8)  NOT NULL,
  severity     VARCHAR(8)  NOT NULL COMMENT 'P1/P2/P3',
  first_time   DATETIME    NOT NULL,
  ongoing      TINYINT(1)  NOT NULL DEFAULT 1,
  PRIMARY KEY (alarm_id),
  KEY idx_alarm_circuit (circuit_id),
  KEY idx_alarm_device (device_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='网络告警（mock）';

-- ---------- 7. 变更工单（与故障定位并行的第二路输入）----------
CREATE TABLE mock_change (
  change_id        VARCHAR(32) NOT NULL,
  change_scope     VARCHAR(64) NOT NULL COMMENT '变更内容',
  change_object    VARCHAR(64) NOT NULL COMMENT '变更对象（设备/批次）',
  effect_on_alarm  VARCHAR(16) NOT NULL COMMENT '根因/加剧/无关',
  plan_time        DATETIME    NOT NULL,
  executor_team    VARCHAR(32) NOT NULL,
  status           VARCHAR(16) NOT NULL,
  PRIMARY KEY (change_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='网络变更工单（mock，用于变更排查支路）';

-- ---------- 8. 历史工单（主动服务画像输入）----------
CREATE TABLE mock_ticket (
  ticket_id     VARCHAR(32)  NOT NULL,
  cust_code     VARCHAR(32)  NOT NULL,
  ticket_type   VARCHAR(32)  NOT NULL,
  title         VARCHAR(128) NOT NULL,
  create_time   DATETIME     NOT NULL,
  close_time    DATETIME         NULL,
  handle_minutes INT             NULL COMMENT '处理时长（分钟）',
  is_proactive  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1=主动发现而非客户报障',
  PRIMARY KEY (ticket_id),
  KEY idx_ticket_cust (cust_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='历史服务工单（mock）';

-- ---------- 9. 主动关怀画像（care 能力输出，可由第6/8表复算）----------
CREATE TABLE mock_care_profile (
  cust_code      VARCHAR(32)  NOT NULL,
  stat_date      DATE         NOT NULL,
  n_alarm_90d    INT          NOT NULL,
  n_ticket_90d   INT          NOT NULL,
  max_loss_pct   DECIMAL(6,2) NOT NULL,
  risk_level     VARCHAR(8)   NOT NULL COMMENT '高/中高/中/低',
  churn_level    VARCHAR(8)   NOT NULL COMMENT '高/中/低',
  suggest        VARCHAR(128) NOT NULL,
  PRIMARY KEY (cust_code, stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户健康画像（mock，供每日巡检定时任务读取）';

-- ---------- 10. 知识回写台账（闭环最后一环）----------
CREATE TABLE mock_knowledge_writeback (
  kb_title        VARCHAR(128) NOT NULL COMMENT '须与知识管理平台已发布标题一致',
  source_case     VARCHAR(64)  NOT NULL COMMENT '来源场景',
  writeback_time  DATETIME     NOT NULL,
  published_state VARCHAR(16)  NOT NULL COMMENT '已发布/待审核',
  PRIMARY KEY (kb_title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='演示产出的知识回写台账（mock）';
