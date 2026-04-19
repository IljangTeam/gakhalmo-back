"""
법정동코드 전체자료.txt → regions.json 변환 스크립트.

실행:
    uv run python -m app.domain.regions.seeds.build_regions
"""

from __future__ import annotations

import json
from pathlib import Path

SEEDS_DIR = Path(__file__).parent
SOURCE_FILE = SEEDS_DIR / "legal_dong_codes.txt"
OUTPUT_FILE = SEEDS_DIR / "regions.json"

SEJONG_SIDO = "세종특별자치시"
SEJONG_DISPLAY = "세종시"


def _level(code: str) -> int:
    """법정동코드 10자리 계층 판정.

    1: 시/도          XX00000000
    2: 시/군/구       XXYYY00000 (일반구 포함, 자릿수 동일)
    3: 읍/면/동/가/로 XXYYYZZZ00
    4: 리             XXYYYZZZWW
    """
    if code[2:] == "00000000":
        return 1
    if code[5:] == "00000":
        return 2
    if code[8:] == "00":
        return 3
    return 4


def build() -> list[dict[str, str | None]]:
    name_by_code: dict[str, str] = {}
    with SOURCE_FILE.open(encoding="utf-8") as f:
        next(f)  # header
        for raw in f:
            parts = raw.rstrip("\r\n").split("\t")
            if len(parts) < 3:
                continue
            code, full_name, status = parts[0], parts[1], parts[2]
            if status != "존재":
                continue
            name_by_code[code] = full_name

    regions: list[dict[str, str | None]] = []

    for code, full_name in name_by_code.items():
        lvl = _level(code)
        if lvl not in (3, 4):
            continue

        tokens = full_name.split()
        sido = tokens[0]
        is_sejong = sido == SEJONG_SIDO

        if lvl == 3:
            # L3: 마지막 토큰이 본인 단위, 중간 토큰이 sigungu
            unit = tokens[-1]
            middle = tokens[1:-1]
            if is_sejong:
                # "세종특별자치시 반곡동" → sigungu NULL, name="세종시 반곡동"
                sigungu: str | None = None
                name = f"{SEJONG_DISPLAY} {unit}"
            else:
                sigungu = " ".join(middle) if middle else None
                parent_unit = middle[-1] if middle else sido
                name = f"{parent_unit} {unit}"
        else:
            # L4 리: 마지막 2토큰(읍/면 + 리)이 name, 그 앞은 sigungu
            if len(tokens) < 3:
                # 방어: 발생하지 않아야 함
                continue
            unit_pair = f"{tokens[-2]} {tokens[-1]}"
            middle = tokens[1:-2]
            if is_sejong:
                sigungu = None
            else:
                sigungu = " ".join(middle) if middle else None
            name = unit_pair

        regions.append(
            {
                "sido": sido,
                "sigungu": sigungu,
                "name": name,
                "full_name": full_name,
            }
        )

    regions.sort(key=lambda r: r["full_name"])

    OUTPUT_FILE.write_text(
        json.dumps(regions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(regions)} regions → {OUTPUT_FILE}")
    return regions


if __name__ == "__main__":
    build()
