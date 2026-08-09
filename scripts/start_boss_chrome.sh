#!/bin/sh
set -eu

CHROME_BIN="${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
CDP_PORT="${CHROME_CDP_PORT:-9222}"
PROFILE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/resume-agent-boss.XXXXXX")"

cleanup() {
  rm -rf "$PROFILE_DIR"
}
trap cleanup EXIT INT TERM

if [ ! -x "$CHROME_BIN" ]; then
  echo "未找到 Google Chrome：$CHROME_BIN" >&2
  exit 1
fi

echo "正在启动独立的 BOSS Chrome 会话。"
echo "请在打开的窗口中登录 BOSS 直聘；关闭窗口后临时浏览器资料会被删除。"

"$CHROME_BIN" \
  --remote-debugging-port="$CDP_PORT" \
  --remote-allow-origins='*' \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  https://www.zhipin.com/
