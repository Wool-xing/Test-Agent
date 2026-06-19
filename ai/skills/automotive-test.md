---
name: automotive-test
description: 车载主编排 Skill。整车 ECU + ADAS + IVI + V2X 测试流程编排。ISO 26262 ASIL + SOTIF + UN R155/R156 合规驱动。HIL/SIL/MIL/PIL 环路在路。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# automotive-test

## 触发

```text
/automotive-test [target] [--ecu <name>] [--asil A|B|C|D] [--scenarios <list>]
```

## 流程

| 阶段 | 调用 |
| ------ | ------ |
| 1 HARA + ASIL 分解 | `requirements-analyst` + `automotive-tester` |
| 2 静态(MISRA + Polyspace + Coverity) | 工具桥 |
| 3 单元 + MC/DC(ASIL C/D) | `pytest` + 覆盖率工具 |
| 4 集成 + SIL/PIL | `automotive-tester` |
| 5 HIL(真 ECU + 仿真) | `/automotive-hil-loop-test` |
| 6 总线 CAN/LIN/FlexRay/Eth | `/automotive-can-bus-test` |
| 7 ADAS 场景 | `/automotive-adas-scenario` |
| 8 OTA 升级 | `/automotive-ota-update-test` |
| 9 合规审计 | `compliance/engine.py` + 行业规则库（ISO 26262/SOTIF/R155/R156 Phase 2） |
| 10 报告 + Bug 单 | `report-generator` |

## 铁律

- L4 极深:ADAS/底盘/转向必 HIL + 形式化验证
- safe-by-default:`automotive.fleet_test_authorized: true` + `automotive.test_lab: <id>` 才允许真车数据
- 不可逆禁止:OTA 必含回退;真车 kill-switch 必有
- 行业适配:接入车载行业必《领域档案》+ 主机厂签字

## 输出

- 测试计划(ISO 26262 V&V 格式)
- HIL 录波(MDF/MF4)
- 场景库结果矩阵
- 合规审计包(SOTIF / R155 / R156 / ASPICE)
