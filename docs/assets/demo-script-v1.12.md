# 30 秒 demo · 录制脚本(V1.12 配置自动组装)

> 目标:让观众在 30 秒内看到"从 0 到测试报告"完整链路 · 用于推特 / 微信视频号 / 掘金 / Hacker News
> 录制工具:[Terminalizer](https://terminalizer.com) / [asciinema](https://asciinema.org) / OBS 屏幕录制
> 配置:`docs/assets/terminalizer-config.yml`(已有)

---

## 分镜表(精确到秒)

| 时间 | 屏幕 | 旁白(可选) |
| ------ | ------ | ------------- |
| 0-3s | 黑屏 → 项目 logo + `Test-Agent · AI Testing Agent · 5 秒上手` | "AI 测试,5 秒上手" |
| 3-6s | 终端:`tagent init --preset 国内-web` 命令打出来 | "一行命令选预设" |
| 6-10s | 屏幕显示生成 3 文件 `✓ 配置生成完毕` + 路径 | "立刻产 .env + tagent.yml + 启动指南" |
| 10-14s | `cat workspace/STARTUP.md` 滚动显示推荐 skill + 出错对照表 | "新手 80% 卡点已自助" |
| 14-18s | `tagent doctor --agents` 显示 `agents=16/16 skills=32/≥25 OK` | "16 专家 32 技能全就绪" |
| 18-25s | `tagent demo` 一键跑 e2e + 显示产出文件树:Excel + xmind + opml + markmap + Word 报告 | "用例 + 思维导图 + 报告全闭环" |
| 25-30s | 屏幕停留产物截图,角标 `github.com/Wool-xing/Test-Agent ⭐` | "GitHub 搜 Test-Agent" |

---

## 终端命令清单(逐条粘贴可跑)

> 录制前先 `cd ~/demo-recording`(干净目录)+ 清空 `.env`、`workspace/`。

```bash
# Step 1 · 装(已假设 pip install -e . 完成,实际录制略过)
# pip install -e .   # 0.5s 一闪而过

# Step 2 · 一键初始化(主秀)

tagent init --preset 国内-web --out . --overwrite

# Step 3 · 看启动指南

cat STARTUP.md | head -30

# Step 4 · 健康检查(秒过)

tagent doctor --agents

# Step 5 · 跑 demo(V1.13 加 · 全 stub LLM 0 成本)

tagent demo

# Step 6 · 看产物(树形)

ls -la workspace/测试用例/ workspace/测试报告/{项目名}/

```text

---

## Terminalizer 录制流程

```bash

# 1. 装(macOS / Linux / Windows-WSL)

npm install -g terminalizer

# 2. 录制(用 docs/assets/terminalizer-config.yml 配置)

terminalizer record demo --config docs/assets/terminalizer-config.yml

# 3. 跑上面 Step 2-6 命令(节奏:每条等输出完再敲下条)

# 4. 渲染成 gif

terminalizer render demo --output docs/assets/demo.gif

# 5. 或导出 mp4(更小)

terminalizer render demo --output docs/assets/demo.mp4 --quality 80

```text

---

## OBS 屏幕录制(若用真窗口而非纯终端)

1.**场景**:终端 + 浏览器并排
2.**左屏**(终端):跑 Step 2-6
3.**右屏**(浏览器):
   - 6-14s 切到 GitHub Repo 页(显示 star 计数)
   - 18-25s 打开生成的 `.xmind` 文件(XMind 客户端)或 `.md` 文件(markmap.js 网页渲染)

4.**录制设置**:1080p / 30fps / H.264 / 码率 6000kbps
5.**后期**:加 0.5s 淡入淡出 + 底栏字幕(`项目网址 + ⭐ Star`)

---

## 渠道适配(同一份素材 3 平台)

| 平台 | 时长 | 格式 | 文案 |
| ------ | ------ | ------ | ------ |
| Twitter / X | 30 秒 | mp4 | "5 sec AI testing setup with `tagent init`. 16 experts, 32 skills, 8640 config combinations. github.com/Wool-xing/Test-Agent" |
| 微信视频号 / 抖音 | 30-60 秒 | mp4 1080×1920 竖屏 | "AI 测试 5 秒上手 · 用例 + 思维导图 + Bug 单 + 报告一键产出 · GitHub 搜 Test-Agent" |
| 掘金 / V2EX / 少数派 | gif | terminalizer | 配文章:介绍 V1.12 配置自动组装 + 矩阵 8640 组合 + 5 preset |
| Hacker News | 静态截图 + 链接 | png + url | 标题:"Test-Agent: AI testing framework with `tagent init` to scaffold 8640 configurations" |

---

## 录制前 checklist

- [ ] 干净的 demo 目录 `~/demo-recording`,清空过的 workspace/
- [ ] `TAGENT_LLM_PROVIDER=stub` 设好(防真 LLM 调用拖慢节奏 + 烧 $)
- [ ] 终端字号 16pt+(手机观众也看得清)
- [ ] 终端颜色主题 dracula / one-dark(对比度高)
- [ ] 录前彩排 3 次,确保每条命令 < 3s 完成
- [ ] 视频发布前过一遍 grep 检查:`三端` / 真 API key / 公司名 — 0 命中才能发

---

## 后续 V1.13 扩(若 demo 火)

| 触发条件 | 加什么 |
| ---------- | -------- |
| 30 秒太赶 | 录 60 秒长版(加用户改 `.env` + 真 LLM 跑 web 测试场景) |
| 用户问"能跑 mobile / api 吗" | 录 4 个 60 秒变体,每个 preset 一个 |
| 公众号 / 视频号要 5 分钟教程 | 录 5 分钟完整 walkthrough(`tagent init` + `tagent run` + 改 `.env` + 修 bug + 跑回归) |

---

## 相关

- 项目宪章 一键部署 · 配置自动组装 canon · 多格式 I/O
- Terminalizer 配置:[`terminalizer-config.yml`](terminalizer-config.yml)
- 录制原 recipe:[`demo.recipe.md`](demo.recipe.md)(V1.7 起占位)
