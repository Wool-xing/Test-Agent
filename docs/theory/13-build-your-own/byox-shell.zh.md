---
id: byox-shell
category: 13-build-your-own
level: 中级
name_zh: 从零写 Shell(Build Your Own Shell)
name_en: Build Your Own Shell
one_liner_zh: 用 C 写 mini shell;懂 fork/exec/pipe/signal
one_liner_en: Mini shell in C; understand fork/exec/pipe/signal
authority:
  - "APUE《UNIX 环境高级编程》Stevens 经典"
  - "tutorial: Stephen Brennan's shell tutorial(C)"
confidence: medium
last_reviewed: 2026-05-12
reviewer: agent-curator
estimated_time_hours: 10
when_to_use: subprocess 测试 / 信号处理 / pipe 输出捕获 / 后台进程测试
common_pitfall: ["不实现 signal handler → SIGCHLD 僵尸进程", "省略 stdin/stdout 重定向 → pipe 不能"]
example: |
  C 100 行 mini shell:cmd parsing + fork+execvp + waitpid + 简单 pipe
related_to: [byox-programming-language]
reading_en: ["https://brennan.io/2015/01/16/write-a-shell-in-c/"]
---

# 对测试工作

- **subprocess 测试**:`runtime/orchestrator/adapters/scripts.py` 用 subprocess 包 49 utils;懂 shell = 懂边界
- **信号**:测试中 SIGTERM/SIGINT 优雅退出
- **pipe**:测试命令链(`cmd1 | cmd2`)各自 stderr 独立
- **后台 / nohup**:测试持久化进程 / Daemon
- **环境变量**:测试 .env 注入 / PATH 安全
