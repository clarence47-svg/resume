import json
import os
import sys
import urllib.error
import urllib.request


def main() -> None:
    base_url = os.getenv("CHROME_CDP_URL", "http://127.0.0.1:9222").rstrip("/")
    try:
        with urllib.request.urlopen(f"{base_url}/json/version", timeout=5) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"Chrome CDP 未连接：{exc}", file=sys.stderr)
        print("请运行：sh scripts/start_boss_chrome.sh", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Chrome CDP 已连接：{payload.get('Browser', 'unknown')}")
    print(payload.get("webSocketDebuggerUrl", ""))


if __name__ == "__main__":
    main()
