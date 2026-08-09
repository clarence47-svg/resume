import httpx


def main() -> None:
    base_url = "http://127.0.0.1:8080"
    for path in ("/health", "/info", "/career/settings", "/jobs", "/tracking/dashboard"):
        response = httpx.get(f"{base_url}{path}", timeout=30)
        response.raise_for_status()
        print(path, response.status_code)


if __name__ == "__main__":
    main()
