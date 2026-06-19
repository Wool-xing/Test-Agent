---
name: automotive-adas-scenario
description: ADAS 场景库测试 Skill。仿真(VTD/CarMaker/CARLA)+ 封闭场地;ODD 边界 + 极端场景;SOTIF(ISO 21448)合规。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# automotive-adas-scenario

## 场景库矩阵

| 类别 | 子场景 |
|------|--------|
| **AEB** | 静止车 / 静止行人 / 横穿自行车 / 夜间逆光 / 雨雪雾 |
| **ACC** | 减速跟车 / 切入切出 / 弯道 / 隧道 |
| **LKA / LCC** | 标线模糊 / 急弯 / 合流 / 隧道入口 / 雪地 |
| **APA / RPA** | 垂直 / 平行 / 斜列 / 障碍误检 / 极窄车位 |
| **AVP** | 信号丢失 / 多层车库 / 人车混流 |
| **HWA / NOA** | 强插 / 鬼探头 / 临时管制 / 大车遮挡 |

## ODD(Operational Design Domain)边界

每场景必含:**ODD-in**(正常)+ **ODD-edge**(边界)+ **ODD-out**(越界,系统必须降级)

## 工具栈

- 仿真:CARLA(开源)/ VTD / CarMaker / Esmini
- 场景文件:OpenSCENARIO 2.0 / Cognata
- 重放:MDF/MF4 录波回放
- 真车:小范围封闭场地;`tagent.yml automotive.public_road_test_authorized` 必显式才允许公开道路

## SOTIF(ISO 21448)关注

- 已知不安全(已知风险)→ 测试覆盖
- 未知不安全(场景库未覆盖)→ 用 fuzz / 极端值生成

## 输出

- 场景结果矩阵(过/挂/未跑 + 触发条件)
- 录波 MDF/MF4
- SOTIF 残余风险报告
