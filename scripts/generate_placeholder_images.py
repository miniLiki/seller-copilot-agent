from __future__ import annotations

from pathlib import Path


PLACEHOLDERS = {
    "sku_001_main.jpg": "placeholder image for SKU_001\n",
    "sku_002_main.jpg": "placeholder image for SKU_002\n",
}


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    image_dir = project_root / "data" / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in PLACEHOLDERS.items():
        (image_dir / filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()

