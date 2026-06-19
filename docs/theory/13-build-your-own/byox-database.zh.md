---
id: byox-database
category: 13-build-your-own
level: 高级
name_zh: 从零写一个数据库(Build Your Own Database)
name_en: Build Your Own Database
one_liner_zh: 从 B+Tree 到 SQL 3000 行;懂事务/索引/并发竟态根因
one_liner_en: B+Tree → SQL in 3000 lines; understand transactions/indexes/race roots
authority:

  - "build-your-own.org/database/(Go,B+ tree → SQL)"
  - "cstack/db_tutorial(C,经典)"
  - "AOSA 500L: DBDB / dagoba"
confidence: medium
last_reviewed: 2026-05-12
reviewer: agent-curator
estimated_time_hours: 30
when_to_use: 性能测试 / SQL 注入 / 事务隔离 / N+1 查询 / 死锁 根因分析
common_pitfall:

  - tutorial 简化省略 WAL → 不能学 ACID
  - 忽略并发 → 不能学锁/MVCC
example: |
  Go 经典:build-your-own.org/database/ 从 B+ tree → kv store → SQL parser → query exec
related_to: [byox-network-stack, byox-web-server]
reading_zh: ["阿里测试学院《MySQL 锁与隔离级别》"]
reading_en: ["https://build-your-own.org/database/"]
---

# 从零写一个数据库

## 对测试工作有什么用?

-**性能测试**:理解 query plan / 索引选择 / IO 模型 → 设计真实负载
-**SQL 注入**:理解 parser → 知道哪里能注入
-**事务测试**:理解隔离级别 → 设计并发竞态用例
-**死锁**:理解锁排队 / 死锁检测 → 复现+修

## 推荐路径

1.**入门**Go `build-your-own.org/database/`(30h,B+ tree → SQL)
2.**C 经典**`cstack/db_tutorial`(40h,SQLite 风格)
3.**图数据库**AOSA 500L Dagoba(10h,简化版理解索引)

## 不要做

- 不真做完整生产库(几年工程)
- 仅理解**核心机制**(B+ tree / WAL / MVCC),够用了
