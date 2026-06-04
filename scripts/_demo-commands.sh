#!/usr/bin/env bash
# _demo-commands.sh · 30 秒 demo 实际命令序列(被 record-demo-* 调)
# 不直接跑 · 通过 asciinema / OBS 录脚本调

set -e

CYAN='\033[36m'
GREEN='\033[32m'
DIM='\033[2m'
RESET='\033[0m'

prompt() {
  echo -en "${CYAN}\$${RESET} "
  for ((i=0; i<${#1}; i++)); do
    echo -n "${1:$i:1}"
    sleep 0.04  # 模拟手打节奏
  done
  echo
  sleep 0.5
}

step() {
  echo -e "\n${DIM}── $1 ──${RESET}\n"
  sleep 0.8
}

# 清干净(录制前)
rm -rf workspace/_demo workspace/测试报告/{项目名}/*.json workspace/测试用例/_smoke_out workspace/_init_smoke 2>/dev/null || true

# Step 1 · init
step "Step 1/4 · 一键初始化(stub LLM,0 API key)"
prompt "tagent init --preset minimal --out workspace/_demo --overwrite"
PYTHONUTF8=1 TAGENT_LLM_PROVIDER=stub TAGENT_LLM_PROVIDER_FALLBACK=stub python -m runtime.cli.main init --preset minimal --out workspace/_demo --overwrite 2>&1 | tail -6
sleep 2

# Step 2 · 看启动指南
step "Step 2/4 · 启动指南"
prompt "cat workspace/_demo/STARTUP.md | head -20"
head -20 workspace/_demo/STARTUP.md
sleep 3

# Step 3 · doctor
step "Step 3/4 · L1 自检"
prompt "tagent doctor --agents"
PYTHONUTF8=1 python -m runtime.cli.main doctor --agents 2>&1 | tail -10
sleep 2

# Step 4 · demo 一键 e2e
step "Step 4/4 · tagent demo(完整 16 agent DAG · 真 AgentRunner · stub LLM)"
prompt "tagent demo"
PYTHONUTF8=1 python -m runtime.cli.main demo 2>&1 | tail -25
sleep 3

# Outro · 看产物
step "产物清单"
prompt "ls workspace/测试报告/{项目名}/*.json"
ls workspace/测试报告/{项目名}/*.json 2>/dev/null
sleep 2

prompt "cat workspace/测试报告/{项目名}/decisions/final_verdict_*.json | head -10"
cat workspace/测试报告/{项目名}/decisions/final_verdict_*.json 2>/dev/null | head -12
sleep 4

# CTA
echo -e "\n${GREEN}⭐ Star on GitHub:${RESET} github.com/Wool-xing/Test-Agent\n"
sleep 2
