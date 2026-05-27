# examples/ 索引(V1.42.0)

> 端到端可跑示例 · 让新人 5 分钟内看到 Test-Agent 实际工作。

## 速查表

| 子目录 | 用途 | 跑法 |
|--------|------|------|
| `web-demo/` | Playwright + pytest 网页测试最小例(saucedemo.com) | `cd web-demo && pip install -r requirements.txt && pytest` |

## 新手 5 分钟

1. `cd examples/web-demo`
2. `pip install -r requirements.txt`(playwright + pytest + 依赖)
3. `playwright install chromium`(首次)
4. `pytest`(看 3 个用例跑过)
5. 翻 `tests/` 看用例怎么写,翻 `pages/` 看 Page Object 模式

## 高级用法

- 想加新 demo(API / 移动 / 桌面 / IoT 等):新建子目录,写 `README.md` 说明启动方式
- demo 不应含真实凭据 / 真实客户数据 → 一律占位 `<YOUR_*>` 或 `.env.example`

## 私有边界(V1.10 起强制)

- **禁止**:真实客户 PRD 样本入 `examples/`
- **占位**:用 `_template_*` 前缀(如 `_template_login_prd.md`)
- **隔离**:含敏感场景的 demo 放私有仓

## 相关

- 上一级:[`../README.md`](../README.md)
- 主宪章 §0(开源约束)+ §29(精髓库隔离)+ §34(精髓库防误入,V1.10)
