"""Sync the backend display dictionary from the single frontend source."""
import json
from pathlib import Path


def main():
    """Extract the JSON-compatible catalog without executing TypeScript."""
    source = Path("frontend/src/i18n/zh-TW.ts").read_text(encoding="utf-8-sig")
    start = source.index("{", source.index("export const zhTW"))
    end = source.index("\n};", start) + 2
    catalog = json.loads(source[start:end])
    Path("backend/elusim/zh_tw.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    main()
