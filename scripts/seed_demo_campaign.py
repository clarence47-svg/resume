import httpx


def main() -> None:
    base_url = "http://127.0.0.1:8080"
    profiles = httpx.get(f"{base_url}/profiles", timeout=30).json()
    completed = [item for item in profiles if item["status"] in {"completed", "partial_success"}]
    if not completed:
        raise SystemExit("请先创建一个已完成画像。")
    response = httpx.post(
        f"{base_url}/campaigns",
        json={
            "profile_task_id": completed[0]["id"],
            "title": "示例求职活动",
            "search_keywords": ["Python 开发", "AI 应用开发"],
            "target_cities": ["上海", "杭州"],
            "source_platforms": ["manual", "official"],
        },
        timeout=30,
    )
    response.raise_for_status()
    print(response.json()["campaign"]["id"])


if __name__ == "__main__":
    main()
