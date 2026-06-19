#!/usr/bin/env bash
# pre-tag hook · 卡 `git tag v1.x` 命令,没跑过 L3 selftest 拒绝
#
# 安装:
#   ln -sf $(pwd)/scripts/git-pre-tag.sh .git/hooks/pre-tag
#   chmod +x .git/hooks/pre-tag
#
# 跳过(紧急):
#   TAGENT_SKIP_PRETAG=1 git tag v1.x  # 自负其责,日志会留痕

set -e

if [ "${TAGENT_SKIP_PRETAG:-0}" = "1" ]; then
  echo "[pre-tag] SKIPPED via TAGENT_SKIP_PRETAG=1(紧急通道)"
  echo "[pre-tag] 跳过原因必须记录到 discussions/selftest_skipped_$(date +%Y%m%d).log"
  exit 0
fi

VERSION_FILE="VERSION"
VERSION=$(cat "$VERSION_FILE" 2>/dev/null || echo "unknown")
LOG_DIR="discussions"
TODAY=$(date +%Y%m%d)
LOG_PATTERN="${LOG_DIR}/selftest_${VERSION}_*.log"

# 检查 7 天内有 L3 自检日志
if ! ls $LOG_PATTERN 1>/dev/null 2>&1; then
  echo "❌ pre-tag rejected: 未发现 selftest_${VERSION}_*.log"
  echo "处置:在打 tag 前执行 L3 自检"
  echo "  tagent doctor --agents --probe 2>&1 | tee ${LOG_DIR}/selftest_${VERSION}_${TODAY}_probe.log"
  echo "  tagent selftest --e2e          2>&1 | tee ${LOG_DIR}/selftest_${VERSION}_${TODAY}_e2e.log"
  echo "(紧急情况:TAGENT_SKIP_PRETAG=1 git tag v1.x)"
  exit 1
fi

LATEST_LOG=$(ls -t $LOG_PATTERN | head -1)
AGE_SEC=$(( $(date +%s) - $(stat -c %Y "$LATEST_LOG" 2>/dev/null || stat -f %m "$LATEST_LOG") ))
MAX_AGE_SEC=$((7 * 24 * 3600))

if [ "$AGE_SEC" -gt "$MAX_AGE_SEC" ]; then
  echo "❌ pre-tag rejected: selftest log too old ($((AGE_SEC / 86400)) 天前)"
  echo "处置:重跑 tagent selftest --e2e"
  exit 1
fi

echo "✅ pre-tag passed: L3 selftest log fresh ($((AGE_SEC / 3600)) 小时前)"
exit 0
