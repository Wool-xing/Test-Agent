---
name: automotive-hil-loop-test
description: HIL/SIL/MIL/PIL 环路在路 Skill。真 ECU + 仿真外设(传感器/执行器);ASIL C/D 必经;故障注入 + 极端工况。
tools: Read, Write, Bash, Grep, Glob
requires_layer: [base, system]
SKILL_IMPL_STATUS: rollout
---

# automotive-hil-loop-test

## 4 类环路

| 缩写 | 含义 | 何时 |
|------|------|------|
| **MIL** | Model-in-the-Loop | 算法早期(Simulink/Matlab)|
| **SIL** | Software-in-the-Loop | 编译后软件 + 主机仿真 |
| **PIL** | Processor-in-the-Loop | 真 ECU + 仿真环境 |
| **HIL** | Hardware-in-the-Loop | **真 ECU + 真 I/O**(模拟外设)|

**ASIL C / D 必经 HIL**(主宪章 §21 L4 极深);ASIL A/B 可 PIL 替代。

## HIL 平台

- 商业:dSPACE / NI VeriStand / ETAS LABCAR / Vector vTESTstudio
- 开源:Linaro AGL Test Suite / 自研 RT-Linux 板

## 必测维度

| 维度 | 内容 |
|------|------|
| 传感器仿真 | 摄像头 / 雷达 / 激光 / IMU / GNSS / 轮速 |
| 执行器仿真 | 制动 / 转向 / 油门 / 灯光 / 空调 |
| 总线注入 | CAN/LIN/FlexRay/Ethernet 模拟其他 ECU |
| 故障注入 | 短路 / 断路 / 过压 / 高温 / 信号丢失 |
| 极端工况 | 高低温 / 振动 / EMC |
| 实时性 | 周期 ≤ 1ms 抖动 |

## 录波

- 格式:**MDF 4.x** / MF4(AUTOSAR 标准)
- 工具:Vector CANape / ASAM ODS
- 必含 seed + 算法版本 + ECU 固件 hash + 仿真版本(主宪章 §21 可复现性)

## 输出

- HIL 测试矩阵
- 录波 MDF4 → `mcp-evidence-vault`
- 故障注入恢复时间统计
