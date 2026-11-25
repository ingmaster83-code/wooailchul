# 우아일출 (wooailchul)

시군구별 일출·일몰·낮 길이·남중·박명 시각 사이트(천문 계산 PyEphem, API 키 불필요). https://wooailchul.wooahouse.com

- `scripts/make_regions.py` — 시군구 대표 좌표(우아메뉴·우아숙소 TourAPI 목록 좌표 중앙값, 표본 3개 이상) → `data/regions.json`(229개). 수집본이 없으면 기존 파일 사용.
- `scripts/build_site.py` — 시군구 페이지(오늘 JS 표시)+월별 시간표 14개월, 해맞이·해넘이 순위, 날짜별 366일 전국 표. 태양 중심 -0°34′ 일출·일몰, -6° 시민박명, 분 반올림. 서울 검증: 1/1 07:47·17:24, 하지 05:11·19:57, 동지 07:43·17:17(한국천문연구원 값과 일치).
- Actions: push·매월 2일 KST 00:10 재빌드(월별 표가 앞으로 14개월로 굴러감). 네이버 토큰은 `scripts/common.py` `NAVER_TOKEN`.
- 전북·전남광주 등 행정구역 개편은 `make_regions.py` SHORT 매핑을 확인(2026-07 전남광주통합특별시).
