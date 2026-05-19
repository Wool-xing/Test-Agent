---
name: automotive-can-bus-test
description: 车载总线测试 Skill。CAN / CAN-FD / LIN / FlexRay / Automotive Ethernet(SOME/IP)协议一致性 + 故障注入 + DoIP/UDS 诊断。
tools: Read, Write, Bash, Grep, Glob
requires_layer: [base, system]
SKILL_IMPL_STATUS: production
---

# automotive-can-bus-test

## 协议矩阵

| 协议 | 工具(开源) | 工具(商业) |
|------|------------|------------|
| CAN / CAN-FD | python-can / SocketCAN / cantools(DBC) | Vector CANoe / PEAK PCAN |
| LIN | python-lin / Saleae | Vector LIN |
| FlexRay | (少开源) | Vector / Synopsys |
| Automotive Ethernet + SOME/IP | vsomeip / commonAPI / Wireshark | Vector vTESTstudio |
| DoIP / UDS | OpenDXM / udsoncan | CANoe + CANape |

## 必测维度

- **协议一致性**:CAN 2.0B / CAN-FD / SOME/IP 标准
- **DBC 解析**:每信号在 frame 内位置 + 符号 + 偏移
- **时序约束**:周期帧 / 事件帧 / 响应帧 timing
- **故障注入**:总线断 / 错误帧 / 总线 off / 节点掉电
- **诊断 UDS**:0x10/0x11/0x22/0x27/0x31/0x34/0x36/0x37 服务
- **安全 SecOC**(AUTOSAR):MAC 校验 / freshness 防重放

## 输出

- DBC 校验报告
- 帧时序统计
- 故障注入恢复时间
- 诊断 DTC 验证
