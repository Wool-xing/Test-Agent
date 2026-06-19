# tutor 索引(教学层)

## 文件清单

| 文件 | 用途 |
| ------ | ------ |
| `theory_kb.py` | 扫 `docs/theory/**/*.md` frontmatter,构建内存目录;反幻觉 L1 引用约束 |
| `verbosity.py` | 模式枚举:`exec`(默认,1 句 ≤30 字 why)/ `learn`(全套教学) |
| `i18n.py` | 语言切换 zh / en / zh-en;UI 与 KB 文本均切 |
| `explainer.py` | 工具调用前后包装"why+theory_ref+alternatives";自检 L2 |
| `feedback.py` | 用户回报"标记错误"落 `workspace/learning/feedback/`(L3) |

## 模式 2 档(Q3-B 决定)

| 模式 | 输出 |
| ------ | ------ |
| **exec**(老手 / CI / 默认) | 每节点仅 `one_liner_zh`(≤30 字);可 `--silent` 完全静默 |
| **learn**(新手 / 评审 / 教学) | 全套:why + theory_ref(KB 卡 id)+ alternatives + reading + L3 反馈按钮 |

## 反幻觉 3 层

| 层 | 实现 |
| ---- | ------ |
| L1 引用约束 | `theory_kb.is_known_id(id)` 检查;非 KB → 输出"该领域未收录" |
| L2 自检 | `explainer.verify_refs` 二次问 LLM "引用的章节真存在?" |
| L3 用户回报 | `feedback.flag_error(card_id, run_id, note)` |

## 双语(zh / en / zh-en)

`i18n.translate(text, lang)` + KB 卡片本身双语 `*.zh.md` / `*.en.md` 预译。
