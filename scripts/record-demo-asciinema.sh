#!/usr/bin/env bash
# 自动录 asciicast(用于 GitHub README / 技术圈传播)
#
# 安装:
#   pip install asciinema
#   或 brew install asciinema
#
# 用法:
#   bash scripts/record-demo-asciinema.sh                          # 默认输出 docs/assets/demo.cast
#   bash scripts/record-demo-asciinema.sh docs/assets/my.cast      # 自定义输出
#
# 渲染 GIF:
#   docker run --rm -v $PWD:/data asciinema/asciicast2gif demo.cast demo.gif
#   或用 https://asciinema.org 上传后嵌入
#
# 渲染 SVG(可嵌 GitHub README,无需 GIF):
#   npm install -g svg-term-cli
#   svg-term --in docs/assets/demo.cast --out docs/assets/demo.svg --window true

set -e

OUT="${1:-docs/assets/demo.cast}"
mkdir -p "$(dirname "$OUT")"

# 删旧 cast,asciinema 不允许追加
rm -f "$OUT"

echo "录制开始 → $OUT"
echo "命令序列在 scripts/_demo-commands.sh"
echo "按 Ctrl+D 在录完后退出"
sleep 1

asciinema rec "$OUT" \
  --title "Test-Agent V1.14 · 30s demo · 真 AgentRunner + stub LLM" \
  --command "bash scripts/_demo-commands.sh" \
  --idle-time-limit 1.5 \
  --rows 28 \
  --cols 100

echo ""
echo "✓ 录制完成 → $OUT"
echo ""
echo "下一步:"
echo "  · 上传 asciinema.org:asciinema upload $OUT"
echo "  · 渲染 GIF:docker run --rm -v \$PWD:/data asciinema/asciicast2gif $(basename $OUT) demo.gif"
echo "  · 渲染 SVG:svg-term --in $OUT --out ${OUT%.cast}.svg --window true"
