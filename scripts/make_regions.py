# -*- coding: utf-8 -*-
"""시군구 대표 좌표(일출·일몰 계산용) 생성 — 한국관광공사 TourAPI 목록(우아메뉴·우아숙소 수집본)의 좌표 중앙값.
사용: python scripts/make_regions.py  → data/regions.json ([[시도, 시군구, 경도, 위도, 표본수], ...])
수집본이 없으면(레포 단독 실행) 기존 data/regions.json 을 그대로 쓰므로 한 번 만들어 커밋해 둔다."""
import gzip, json, re, statistics, sys, collections
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SRC = [ROOT.parent / "wooamenu" / "data" / "list.json.gz", ROOT.parent / "wooasukso" / "data" / "list.json.gz"]
SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
         "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
         "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주", "전남광주통합특별시": "전남광주", "전북특별자치시": "전북", "강원": "강원", "경북": "경북", "충북": "충북", "충남": "충남", "경남": "경남", "전북": "전북", "전남": "전남광주", "광주": "전남광주"}
pts = collections.defaultdict(list)
for p in SRC:
    for r in json.loads(gzip.open(p, "rt", encoding="utf-8").read()):
        t = (r.get("a") or "").split()
        if len(t) < 2 or t[0] not in SHORT:
            continue
        s = SHORT[t[0]]
        g = "세종시" if s == "세종" else t[1]
        if not re.search(r"(시|군|구)$", g):
            continue
        try:
            x, y = float(r["x"]), float(r["y"])
        except Exception:
            continue
        if 124 < x < 132 and 33 < y < 39.5:
            pts[(s, g)].append((x, y))
out = []
for (s, g), L in sorted(pts.items()):
    if len(L) < 3:
        continue
    out.append([s, g, round(statistics.median(a for a, _ in L), 4), round(statistics.median(b for _, b in L), 4), len(L)])
(ROOT / "data" / "regions.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("시군구", len(out), "표본<10:", [(a, b, n) for a, b, _, _, n in out if n < 10][:15])
print(collections.Counter(a for a, *_ in out))
