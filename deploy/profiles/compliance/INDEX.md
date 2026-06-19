# profiles/compliance 索引

> 行业合规规则库插槽。每个 YAML 文件 = 一个合规框架的检查项集。
> 真规则由领域专家提供;本目录仅含**空载示例**,V1.2.0 起步。

## 已提供示例(空载)

| 文件 | 框架 | 适用行业 |
| ------ | ------ | --------- |
| `soc2.yaml` | SOC 2 Type II | SaaS / 云服务 |
| `pci-dss.yaml` | PCI-DSS v4.0 | 支付 / 卡片处理 |
| `hipaa.yaml` | HIPAA Security Rule | 医疗 / 健康 |
| `iec-62304.yaml` | IEC 62304(医疗软件生命周期) | 医疗器械软件 |
| `iec-61508.yaml` | IEC 61508(工控功能安全) | 工业控制 |
| `iso-26262.yaml` | ISO 26262(车规功能安全 ASIL) | 汽车 / ADAS |
| `do-178c.yaml` | DO-178C(航空机载软件) | 航空 |
| `gdpr.yaml` | GDPR(欧盟数据保护) | 跨境数据 |
| `pipl.yaml` | PIPL(中国个人信息保护) | 中国境内 |
| `ccpa.yaml` | CCPA(加州消费者隐私) | 美国加州 |

## 规则文件 schema

```yaml
framework: <name>
version: <date>
applicable_industries: [list]
checks:

  - id: <unique-id>
    title: <human-readable>
    severity: P0/P1/P2/P3
    rule: <自然语言 + 可机器化条件>
    evidence_required: [list of evidence types]
    references: [URLs / 标准条款]

```text

## 接入方式

L4 级被测项( 深度准则 L4)必须通过 `mcp-compliance-checker.check_compliance(profile, run_id)` 验证。
真规则文件由领域专家+test-lead 双签签字后入库( 五条原则 + AgentChat 协议)。
