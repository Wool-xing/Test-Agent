# Demo Gif 录制配方

> 目标:30 秒 GIF · ≤ 2MB · 嵌入 README

## 推荐工具(选 1)

### A · terminalizer(最简单,跨平台)

```bash
npm install -g terminalizer
terminalizer config            # 一次性,生成 ~/.terminalizer
terminalizer record demo       # 开始录,Ctrl+D 停
terminalizer render demo -o docs/assets/demo.gif --quality 60
```

### B · asciinema + svg-term-cli(更轻量,SVG 嵌入更小)

```bash
# 录
asciinema rec docs/assets/demo.cast

# 转 SVG(SVG 不是 GIF,但 GitHub README 也能渲染)
npm install -g svg-term-cli
cat docs/assets/demo.cast | svg-term --out docs/assets/demo.svg --window
```

### C · OBS + ffmpeg(最通用,体积大)

录屏 mp4 → `ffmpeg -i demo.mp4 -vf "fps=10,scale=800:-1" docs/assets/demo.gif`

## 30 秒脚本(按此演)

```
[0s]   tagent --version
       v1.8.0

[3s]   tagent run "测试 https://playwright.dev 首页+导航 → 验证标题+CTA 按钮" --mode learn --lang zh
       
[6s]   Step 1/8: requirements-analyst
         ↳ 原因: 任何测试必先理解被测物;Web 系统先解析需求
         ↳ 理论: ISTQB Foundation §1.4 七原则·测试早介入

[10s]  Step 2/8: testcase-designer
         ↳ 原因: 等价类划分 + 边界值;输入字段:URL/Header/Action
         ↳ 理论: equivalence-partitioning(KB) / boundary-value-analysis

[14s]  Step 3/8: automation-engineer
         ↳ 原因: Web 优先用 Playwright;跨浏览器+稳定
         ↳ 替代: Selenium(慢)/ Cypress(同域限制)
         ↳ 阅读: https://playwright.dev

[18s]  Step 7/8: report-generator
         ↳ 生成 Allure 报告 → workspace/测试报告/{项目名}/

[22s]  done: 8/8 ok · 报告 → http://localhost:5050
       
[25s]  打开 Allure 报告页面快闪一下

[30s]  end
```

## 风险

| 问题 | 防御 |
|------|------|
| Gif > 2MB 渲染慢 | 800x400 / fps=10 / 60% 质量 |
| 真跑 30 秒不到 | 用 stub provider + 预录会话回放 |
| 文字看不清 | 字号 14+ / 暗色背景 / 高对比 |
| 敏感数据 | 录前 unset env / 清屏 / 用 demo.example.com |

## 嵌入 README

```html
<img src="docs/assets/demo.gif" alt="demo">
```

或 SVG(终端动画体积更小):
```html
<img src="docs/assets/demo.svg" alt="demo">
```

## Checkpoint

- [ ] 录制完成
- [ ] 文件 < 2MB
- [ ] README 引用更新
- [ ] commit + push
