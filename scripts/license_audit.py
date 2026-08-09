from pathlib import Path


def main() -> None:
    required = [Path("LICENSE"), Path("THIRD_PARTY_NOTICES.md"), Path("pyproject.toml")]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"缺少许可证文件：{', '.join(missing)}")
    print("许可证文件检查通过。")


if __name__ == "__main__":
    main()
