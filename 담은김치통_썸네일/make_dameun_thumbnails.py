# -*- coding: utf-8 -*-
"""
이지앤프리 담은 블랙 김치통 — 용량/구성별 폴더링 + 없는 썸네일 자동 제작

사용법 (Windows, Python 3 + Pillow 필요: pip install pillow)
    python make_dameun_thumbnails.py
    python make_dameun_thumbnails.py --root "D:\\코워크\\_누끼원본_추출"

동작
 1) ROOT\\담은_김치통\\ 아래에 상품별 폴더(썸네일/상세페이지 하위폴더 포함)를 만든다.
 2) ROOT\\담은_김치통\\_단품누끼\\ 에 있는 단품 누끼 PNG(투명배경)를 찾아
    썸네일 폴더가 비어있는 상품만 1000x1000 썸네일을 합성해서 저장한다.
    (이미 썸네일이 들어있는 상품은 건드리지 않음)
 3) 결과를 ROOT\\담은_김치통\\_작업현황.csv 로 남긴다.

단품 누끼 파일명 규칙 (확장자 png/webp/jpg 가능)
    원핸들_1.4L.png  원핸들_2L.png  원핸들_4.3L.png  원핸들_4.7L.png
    원핸들_6L.png    원핸들_7.3L.png
    투핸들_8L.png    투핸들_13L.png  투핸들_17L.png
  - 세트(1~3호)에 들어가는 8L/13L은 원핸들 파일이 없으면 투핸들 파일로 대체한다.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BRAND = "이지앤프리 담은 블랙"
CANVAS = 1000
IMG_EXT = (".png", ".webp", ".jpg", ".jpeg")

# (그룹폴더, 상품폴더, 정식 상품명, 배지, 구성[(손잡이, 용량L, 수량)])
PRODUCTS = [
    ("01_원핸들_세트", "3호_4종5P_1.4Lx2+2L+7.3L+13L",
     "이지앤프리 담은 블랙 원핸들 김치통 3호 4종 5P 세트 1.4L 2P + 2L 1P + 7.3L 1P + 13L 1P",
     "3호 세트 4종 5P", [("원핸들", 13, 1), ("원핸들", 7.3, 1), ("원핸들", 2, 1), ("원핸들", 1.4, 2)]),
    ("01_원핸들_세트", "2호_3종4P_1.4Lx2+4.7L+8L",
     "이지앤프리 담은 블랙 원핸들 김치통 2호 3종 4P 세트 1.4L 2P + 4.7L 1P + 8L 1P",
     "2호 세트 3종 4P", [("원핸들", 8, 1), ("원핸들", 4.7, 1), ("원핸들", 1.4, 2)]),
    ("01_원핸들_세트", "1호_3종4P_1.4Lx2+2L+7.3L",
     "이지앤프리 담은 블랙 원핸들 김치통 1호 3종 4P 세트 1.4L 2P + 2L 1P + 7.3L 1P",
     "1호 세트 3종 4P", [("원핸들", 7.3, 1), ("원핸들", 2, 1), ("원핸들", 1.4, 2)]),
    ("02_투핸들_1+1", "투핸들_17L_1+1", "이지앤프리 담은 블랙 투핸들 김치통 17L 1+1",
     "1+1", [("투핸들", 17, 2)]),
    ("02_투핸들_1+1", "투핸들_13L_1+1", "이지앤프리 담은 블랙 투핸들 김치통 13L 1+1",
     "1+1", [("투핸들", 13, 2)]),
    ("02_투핸들_1+1", "투핸들_8L_1+1", "이지앤프리 담은 블랙 투핸들 김치통 8L 1+1",
     "1+1", [("투핸들", 8, 2)]),
    ("03_원핸들_1+1", "원핸들_7.3L_1+1", "이지앤프리 담은 블랙 원핸들 김치통 7.3L 1+1",
     "1+1", [("원핸들", 7.3, 2)]),
    ("03_원핸들_1+1", "원핸들_6L_1+1", "이지앤프리 담은 블랙 원핸들 김치통 6L 1+1",
     "1+1", [("원핸들", 6, 2)]),
    ("03_원핸들_1+1", "원핸들_4.7L_1+1", "이지앤프리 담은 블랙 원핸들 김치통 4.7L 1+1",
     "1+1", [("원핸들", 4.7, 2)]),
    ("03_원핸들_1+1", "원핸들_4.3L_1+1", "이지앤프리 담은 블랙 원핸들 김치통 4.3L 1+1",
     "1+1", [("원핸들", 4.3, 2)]),
    ("03_원핸들_1+1", "원핸들_2L_1+1", "이지앤프리 담은 블랙 원핸들 김치통 2L 1+1",
     "1+1", [("원핸들", 2, 2)]),
    ("03_원핸들_1+1", "원핸들_1.4L_2P_1+1", "이지앤프리 담은 블랙 원핸들 김치통 1.4L 2P 1+1",
     "2P 1+1", [("원핸들", 1.4, 4)]),
    ("04_투핸들_단품", "투핸들_17L_1P", "이지앤프리 담은 블랙 투핸들 김치통 17L 1P",
     "", [("투핸들", 17, 1)]),
]


def fmt_l(v):
    return f"{v:g}L"


def find_font(size):
    candidates = [
        r"C:\Windows\Fonts\malgunbd.ttf", r"C:\Windows\Fonts\malgun.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def find_source(src_dir, handle, liters):
    """단품 누끼 찾기. 같은 용량의 다른 손잡이 타입으로 대체 가능."""
    cap = re.escape(fmt_l(liters))
    files = [p for p in src_dir.iterdir() if p.suffix.lower() in IMG_EXT]
    for h in (handle, "투핸들" if handle == "원핸들" else "원핸들"):
        for p in files:
            name = p.stem.replace(" ", "")
            if h in name and re.search(rf"(?<![\d.]){cap}", name, re.I):
                return p, h != handle
    return None, False


def trim(img):
    img = img.convert("RGBA")
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def compose(items, badge):
    """items: [(PIL.Image, liters, qty)] 큰 용량 → 작은 용량 순."""
    canvas = Image.new("RGB", (CANVAS, CANVAS), "white")
    draw = ImageDraw.Draw(canvas)

    # 개별 제품 높이: 용량의 세제곱근에 비례 (실제 크기감 유지)
    max_l = max(l for _, l, _ in items)
    pieces = []
    for img, liters, qty in items:
        rel = (liters / max_l) ** (1 / 3)
        for _ in range(qty):
            pieces.append((img, rel, liters))

    area_top, area_bottom = 170, 850
    area_w, area_h = CANVAS - 100, area_bottom - area_top
    gap = 24

    # 1줄/2줄(큰 용량 뒷줄, 작은 용량 앞줄) 중 제품이 더 크게 보이는 배치 선택
    def layout(rows):
        # 기준 높이 1.0 일 때 각 줄의 폭/높이
        dims = [(sum(img.width * rel / img.height for img, rel, _ in r),
                 max(rel for _, rel, _ in r)) for r in rows]
        total_h = sum(h for _, h in dims)
        unit = min(
            (area_h - gap * (len(rows) - 1)) / total_h,
            *[(area_w - gap * (len(r) - 1)) / w for r, (w, _) in zip(rows, dims)],
        )
        return unit, dims

    options = [[pieces]]
    if len(pieces) >= 3:
        k = (len(pieces) + 1) // 2
        options.append([pieces[:k], pieces[k:]])
    rows = max(options, key=lambda o: layout(o)[0])
    unit, dims = layout(rows)

    block_h = sum(h * unit for _, h in dims) + gap * (len(rows) - 1)
    y = area_top + (area_h - block_h) / 2
    for r, (w, rh) in zip(rows, dims):
        row_w = w * unit + gap * (len(r) - 1)
        x = (CANVAS - row_w) / 2
        bottom = y + rh * unit
        for img, rel, _ in r:
            h = int(rel * unit)
            pw = int(img.width * h / img.height)
            resized = img.resize((max(pw, 1), max(h, 1)), Image.LANCZOS)
            canvas.paste(resized, (int(x), int(bottom - h)), resized)
            x += pw + gap
        y = bottom + gap

    # 배지
    if badge:
        f = find_font(56)
        tw = draw.textlength(badge, font=f)
        draw.rounded_rectangle((50, 50, 50 + tw + 60, 50 + 90), radius=45, fill="#111111")
        draw.text((80, 65), badge, font=f, fill="white")

    # 하단 구성 표기
    caps = " + ".join(
        fmt_l(l) + (f" {q}P" if q > 1 and "1+1" not in badge else "")
        for _, l, q in items
    )
    f2 = find_font(44)
    tw = draw.textlength(caps, font=f2)
    draw.text(((CANVAS - tw) / 2, 880), caps, font=f2, fill="#222222")
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\코워크\_누끼원본_추출")
    ap.add_argument("--force", action="store_true", help="기존 썸네일이 있어도 _제작 썸네일 새로 생성")
    args = ap.parse_args()

    base = Path(args.root) / "담은_김치통"
    src_dir = base / "_단품누끼"
    src_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for group, folder, full_name, badge, comp in PRODUCTS:
        pdir = base / group / folder
        thumb_dir, detail_dir = pdir / "썸네일", pdir / "상세페이지"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        detail_dir.mkdir(parents=True, exist_ok=True)
        (pdir / "상품명.txt").write_text(full_name + "\n", encoding="utf-8")

        existing = [p for p in thumb_dir.iterdir() if p.suffix.lower() in IMG_EXT]
        has_detail = any(detail_dir.iterdir())
        status, note = "", []

        if existing and not args.force:
            status = f"기존 썸네일 {len(existing)}개"
        else:
            items, missing = [], []
            for handle, liters, qty in comp:
                src, substituted = find_source(src_dir, handle, liters)
                if not src:
                    missing.append(f"{handle}_{fmt_l(liters)}")
                    continue
                if substituted:
                    note.append(f"{fmt_l(liters)} 다른 손잡이 누끼로 대체")
                items.append((trim(Image.open(src)), liters, qty))
            if missing:
                status = "제작불가 - 단품누끼 없음: " + ", ".join(missing)
            else:
                out = thumb_dir / f"{folder}_썸네일_제작.jpg"
                compose(items, badge).save(out, quality=95)
                status = "썸네일 제작완료"

        rows.append([group, folder, full_name, status,
                     "있음" if has_detail else "없음(수집 필요)", "; ".join(note)])
        print(f"[{status}] {group}/{folder}")

    with open(base / "_작업현황.csv", "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["그룹", "폴더", "상품명", "썸네일", "상세페이지", "비고"])
        w.writerows(rows)
    print(f"\n완료: {base / '_작업현황.csv'}")


if __name__ == "__main__":
    sys.exit(main())
