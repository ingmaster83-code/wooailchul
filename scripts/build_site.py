# -*- coding: utf-8 -*-
"""우아일출 정적 사이트 생성기 — 시군구별 일출·일몰·낮 길이·남중·박명 시각(천문 계산, ephem, API 키 불필요).
입력: data/regions.json (시도, 시군구, 경도, 위도, 표본수) — scripts/make_regions.py 로 생성
출력: _site/ (시군구 페이지 + 월별 시간표 14개월, 해맞이·해넘이 순위, 날짜별(366일) 전국 표, 안내, 검색 인덱스, sitemap)
계산: 태양 중심이 지평선 아래 0°34′(대기굴절+시반경)일 때 일출·일몰, 시민박명은 -6°, 분 단위 반올림(한국천문연구원 표기와 같은 방식). 고도는 0m로 가정.
"""
import collections, datetime as dt, json, os, shutil, sys

import ephem

from common import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
DATA = ROOT / "data"
TODAY = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date()
REF_YEAR = TODAY.year if TODAY.month <= 6 else TODAY.year + 1      # 날짜별·주요 날짜 표의 기준 연도(연도마다 1~2분 이내 차이)
NY = TODAY.year + 1                                                # 다음 새해(해맞이) 연도
WD = "월화수목금토일"
ORDER = ["서울", "부산", "대구", "인천", "전남광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "경북", "경남", "제주"]
REP = {"서울": "종로구", "부산": "부산진구", "대구": "중구", "인천": "남동구", "전남광주": "동구", "대전": "서구", "울산": "남구", "세종": "세종시", "경기": "수원시", "강원": "춘천시",
       "충북": "청주시", "충남": "천안시", "전북": "전주시", "경북": "포항시", "경남": "창원시", "제주": "제주시"}
_cache = {}
_SUN = ephem.Sun()


def mm(d):
    """ephem.Date → KST 분(0~1440+)"""
    k = d.datetime() + dt.timedelta(hours=9)
    return k.hour * 60 + k.minute + (1 if k.second >= 30 else 0)


def hm(m):
    return "%02d:%02d" % ((m // 60) % 24, m % 60)


def sun(r, d):
    """(일출, 일몰, 남중, 박명시작, 박명종료) 분 단위"""
    key = (r["i"], d)
    v = _cache.get(key)
    if v is None:
        o = ephem.Observer()
        o.lon, o.lat, o.elevation, o.pressure = str(r["x"]), str(r["y"]), 0, 0
        o.date = ephem.Date(dt.datetime(d.year, d.month, d.day) - dt.timedelta(hours=9))
        o.horizon = "-0:34"
        rise, sett, tr = o.next_rising(_SUN), o.next_setting(_SUN), o.next_transit(_SUN)
        o.horizon = "-6"
        o.date = ephem.Date(dt.datetime(d.year, d.month, d.day) - dt.timedelta(hours=9))
        cb, ce = o.next_rising(_SUN), o.next_setting(_SUN)
        v = (mm(rise), mm(sett), mm(tr), mm(cb), mm(ce))
        _cache[key] = v
    return v


def dur(a, b):
    m = b - a
    return "%d시간 %02d분" % (m // 60, m % 60)


def dd(m):
    return ("+%d분" % m) if m > 0 else (("%d분" % m) if m < 0 else "0분")


def load():
    rows = json.loads((DATA / "regions.json").read_text(encoding="utf-8"))
    rs = [dict(s=s, g=g, x=x, y=y, n=n) for s, g, x, y, n in rows]
    rs.sort(key=lambda r: (ORDER.index(r["s"]) if r["s"] in ORDER else 99, r["g"]))
    for i, r in enumerate(rs):
        r["i"] = i
    return rs


def month_list():
    out, y, m = [], TODAY.year, TODAY.month
    for _ in range(14):
        out.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def days_of(y, m):
    d = dt.date(y, m, 1)
    while d.month == m:
        yield d
        d += dt.timedelta(days=1)


def rlink(r):
    return '<a href="/region/%s/%s/">%s %s</a>' % (q(r["s"]), q(r["g"]), esc(r["s"]), esc(r["g"]))


def day_table(r, ds):
    rows, prev = [], None
    for d in ds:
        a, b, t, cb, ce = sun(r, d)
        L = b - a
        rows.append("<tr><th>%d월 %d일(%s)</th><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            d.month, d.day, WD[d.weekday()], hm(a), hm(b), dur(a, b), hm(t), hm(cb), hm(ce)))
    return '<div class="tbl-wrap"><table class="tbl"><tr><th>날짜</th><th>일출</th><th>일몰</th><th>낮 길이</th><th>남중</th><th>박명 시작</th><th>박명 종료</th></tr>%s</table></div>' % "".join(rows)


def key_days(r):
    items = [("새해 첫날", dt.date(REF_YEAR, 1, 1)), ("춘분 무렵(3/20)", dt.date(REF_YEAR, 3, 20)), ("하지 무렵(6/21)", dt.date(REF_YEAR, 6, 21)), ("추분 무렵(9/23)", dt.date(REF_YEAR, 9, 23)), ("동지 무렵(12/22)", dt.date(REF_YEAR, 12, 22)), ("해넘이(12/31)", dt.date(REF_YEAR, 12, 31))]
    rows = []
    for n, d in items:
        a, b, t, cb, ce = sun(r, d)
        rows.append("<tr><th>%s</th><td>%s</td><td>%s</td><td>%s</td></tr>" % (n, hm(a), hm(b), dur(a, b)))
    return '<div class="tbl-wrap"><table class="tbl"><tr><th>구분</th><th>일출</th><th>일몰</th><th>낮 길이</th></tr>%s</table></div>' % "".join(rows)


def year_facts(r):
    ds = [dt.date(REF_YEAR, 1, 1) + dt.timedelta(days=i) for i in range(366 if REF_YEAR % 4 == 0 else 365)]
    S = [(sun(r, d), d) for d in ds]
    ear = min(S, key=lambda v: (v[0][0], v[1])); lat = max(S, key=lambda v: (v[0][0], -v[1].toordinal()))
    esu = min(S, key=lambda v: (v[0][1], v[1])); lsu = max(S, key=lambda v: (v[0][1], -v[1].toordinal()))
    lon = max(S, key=lambda v: (v[0][1] - v[0][0], -abs((v[1] - dt.date(REF_YEAR, 6, 21)).days))); sho = min(S, key=lambda v: (v[0][1] - v[0][0], abs((v[1] - dt.date(REF_YEAR, 12, 22)).days)))
    f = lambda d: "%d월 %d일" % (d.month, d.day)
    return dict(ear=(f(ear[1]), hm(ear[0][0])), lat=(f(lat[1]), hm(lat[0][0])), esu=(f(esu[1]), hm(esu[0][1])), lsu=(f(lsu[1]), hm(lsu[0][1])),
                lon=(f(lon[1]), dur(lon[0][0], lon[0][1])), sho=(f(sho[1]), dur(sho[0][0], sho[0][1])))


def page_region(r, by_s, months):
    s, g = r["s"], r["g"]
    place = "%s %s" % (s, g)
    fy = year_facts(r)
    cur = list(days_of(TODAY.year, TODAY.month))
    data = {}
    for y, m in months:
        for d in days_of(y, m):
            a, b, t, cb, ce = sun(r, d)
            data["%04d-%02d-%02d" % (y, m, d.day)] = [a, b, t, cb, ce]
    new = sun(r, dt.date(NY, 1, 1))
    body = ['<div class="page-head"><h1>%s 일출·일몰 시간</h1><p>오늘·이번 주·월별 일출, 일몰, 낮 길이, 박명 시각</p></div>' % esc(place),
            '<div class="hero"><div class="today-box" id="today" data-rg="%s"><div><small>오늘 일출</small><b id="t-rise">-</b></div><div><small>오늘 일몰</small><b id="t-set">-</b></div><div><small>낮 길이</small><b id="t-len">-</b></div><div><small>남중 시각</small><b id="t-noon">-</b></div></div>'
            '<p id="t-date" style="margin-top:10px"></p></div>' % esc(place),
            ad(),
            '<h2 class="group-title">앞으로 7일</h2><div class="tbl-wrap"><table class="tbl" id="week"><tr><th>날짜</th><th>일출</th><th>일몰</th><th>낮 길이</th></tr></table></div>',
            '<script>window.SUN=%s;</script><script src="/assets/js/today.js"></script>' % json.dumps(data, separators=(",", ":")),
            '<h2 class="group-title">%d월 일출·일몰 시간표</h2>' % TODAY.month, day_table(r, cur),
            '<h2 class="group-title">월별 시간표</h2><div class="chips">%s</div>' % "".join('<a class="chip" href="/region/%s/%s/%04d-%02d/">%d년 %d월</a>' % (q(s), q(g), y, m, y, m) for y, m in months),
            '<h2 class="group-title">주요 날짜 일출·일몰</h2>', key_days(r),
            '<h2 class="group-title">1년 요약</h2><ul class="lead"><li>일출이 가장 빠른 날은 <b>%s</b>(%s), 가장 늦은 날은 <b>%s</b>(%s)입니다.</li><li>일몰이 가장 빠른 날은 <b>%s</b>(%s), 가장 늦은 날은 <b>%s</b>(%s)입니다.</li><li>낮이 가장 긴 날은 <b>%s</b>(%s), 가장 짧은 날은 <b>%s</b>(%s)입니다.</li></ul>' % (
                fy["ear"][0], fy["ear"][1], fy["lat"][0], fy["lat"][1], fy["esu"][0], fy["esu"][1], fy["lsu"][0], fy["lsu"][1], fy["lon"][0], fy["lon"][1], fy["sho"][0], fy["sho"][1]),
            '<h2 class="group-title">같은 지역의 다른 시군구</h2><div class="chips">%s</div>' % "".join(
                '<a class="chip" href="/region/%s/%s/">%s</a>' % (q(s), q(o["g"]), esc(o["g"])) for o in by_s[s] if o is not r)]
    body.append('<div class="note-box">%s 대표 좌표(동경 %.2f°, 북위 %.2f°) 기준 계산값입니다. 같은 시군구 안에서도 위치·지형·고도에 따라 1~2분 차이가 날 수 있습니다.</div>' % (esc(place), r["x"], r["y"]))
    faq = [("%s의 새해 첫 일출은 몇 시인가요?" % place, "%d년 1월 1일 %s 일출은 %s, 일몰은 %s입니다. 전망 좋은 곳은 일출 30분 전에 도착하는 것을 권합니다." % (NY, place, hm(new[0]), hm(new[1]))),
           ("%s에서 낮이 가장 긴 날은 언제인가요?" % place, "하지 무렵인 %s이며 낮 길이는 %s입니다. 가장 짧은 날은 %s로 %s입니다." % (fy["lon"][0], fy["lon"][1], fy["sho"][0], fy["sho"][1])),
           ("일출 시각은 어떤 기준인가요?", "태양 중심이 지평선 아래 0°34′에 있을 때를 일출·일몰로 하며(대기굴절과 태양 반지름 반영), 분 단위로 반올림했습니다. 박명은 태양 중심이 지평선 아래 6°일 때(시민박명)입니다."),
           ("일출 시각이 해마다 달라지나요?", "같은 날짜의 일출·일몰은 연도에 따라 1~2분 이내로만 달라집니다. 월별 표는 해당 연월 기준으로 계산했습니다.")]
    crumbs = [("홈", "/"), (s, "/region/%s/" % s), (g, "/region/%s/%s/" % (s, g))]
    title = "%s 일출 일몰 시간 - 오늘·월별 시간표" % place
    desc = "%s의 오늘 일출·일몰 시각과 월별 시간표. 새해 첫 일출 %s, 낮 길이·남중·박명 시각을 한눈에 확인하세요." % (place, hm(new[0]))
    write("/region/%s/%s/" % (s, g), layout("/region/%s/%s/" % (s, g), title, desc, "\n".join(body), faq, crumbs, coupang=True), "0.9")
    for y, m in months:
        ds = list(days_of(y, m))
        i = months.index((y, m))
        nav = ""
        if i > 0:
            nav += '<a class="chip" href="/region/%s/%s/%04d-%02d/">‹ %d월</a> ' % (q(s), q(g), months[i - 1][0], months[i - 1][1], months[i - 1][1])
        if i < len(months) - 1:
            nav += '<a class="chip" href="/region/%s/%s/%04d-%02d/">%d월 ›</a>' % (q(s), q(g), months[i + 1][0], months[i + 1][1], months[i + 1][1])
        a1, b1, *_ = sun(r, ds[0]); a2, b2, *_ = sun(r, ds[-1])
        lead = "%s의 %d년 %d월 일출은 %s에서 %s까지, 일몰은 %s에서 %s까지 변합니다. 월 초 낮 길이는 %s, 월말은 %s입니다." % (place, y, m, hm(a1), hm(a2), hm(b1), hm(b2), dur(a1, b1), dur(a2, b2))
        mb = ['<div class="page-head"><h1>%s %d년 %d월 일출·일몰 시간표</h1><p>일출, 일몰, 낮 길이, 남중, 박명</p></div>' % (esc(place), y, m), '<p class="lead">%s</p>' % esc(lead), ad(), day_table(r, ds),
              '<div class="chips">%s<a class="chip" href="/region/%s/%s/">%s 오늘 일출</a></div>' % (nav, q(s), q(g), esc(place))]
        p = "/region/%s/%s/%04d-%02d/" % (s, g, y, m)
        write(p, layout(p, "%s %d년 %d월 일출 일몰 시간표" % (place, y, m), "%s의 %d년 %d월 날짜별 일출·일몰 시각, 낮 길이, 남중, 박명 시간표입니다." % (place, y, m), "\n".join(mb),
                        [("%s %d월 일출은 몇 시인가요?" % (place, m), "%d월 1일 일출 %s, 월말 일출 %s입니다. 일몰은 %s에서 %s까지입니다." % (m, hm(a1), hm(a2), hm(b1), hm(b2)))],
                        [("홈", "/"), (s, "/region/%s/" % s), (g, "/region/%s/%s/" % (s, g)), ("%d년 %d월" % (y, m), p)], coupang=True), "0.5")


def rank_table(rs, d, which):
    rows = []
    for r in rs:
        a, b, t, cb, ce = sun(r, d)
        rows.append((a if which == "rise" else b, r, a, b))
    rows.sort(key=lambda v: (v[0], v[1]["i"]))
    out = "".join("<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (i + 1, rlink(r), hm(a), hm(b)) for i, (_, r, a, b) in enumerate(rows))
    return rows, '<div class="tbl-wrap"><table class="tbl"><tr><th>순위</th><th>시군구</th><th>일출</th><th>일몰</th></tr>%s</table></div>' % out


def page_rank(kind, rs, by_s):
    if kind == "haedoji":
        d, which, name, verb = dt.date(NY, 1, 1), "rise", "해맞이", "새해 첫 일출"
    else:
        d, which, name, verb = dt.date(NY - 1, 12, 31), "set", "해넘이", "한 해 마지막 일몰"
    rows, tbl = rank_table(rs, d, which)
    first, last = rows[0], rows[-1]
    key = hm(first[0]), hm(last[0])
    lead = "%d년 %d월 %d일 %s이 가장 빠른 곳은 %s %s(%s)이고, 가장 늦은 곳은 %s %s(%s)입니다. 서울 종로구는 %s입니다." % (
        d.year, d.month, d.day, verb, first[1]["s"], first[1]["g"], key[0], last[1]["s"], last[1]["g"], key[1],
        hm(sun([r for r in rs if r["s"] == "서울"][0], d)[0 if which == "rise" else 1]))
    path = "/%s/%d/" % (kind, NY)
    body = ['<div class="page-head"><h1>%d년 %s 시각 — 전국 시군구 순위</h1><p>%d년 %d월 %d일 기준</p></div>' % (NY, name, d.year, d.month, d.day), '<p class="lead">%s</p>' % esc(lead), ad(),
            '<h2 class="group-title">시도별 보기</h2><div class="chips">%s</div>' % "".join('<a class="chip" href="%s%s/">%s</a>' % (path, q(s), esc(s)) for s in ORDER if s in by_s), tbl,
            '<div class="note-box">%s 시각은 시군구 대표 좌표 기준 계산값입니다. 해안·산 위 등 전망 지점마다 1~2분 차이가 나며, 날씨와 구름은 반영하지 않았습니다.</div>' % name]
    faq = [("%d년 %s이 가장 빠른 지역은 어디인가요?" % (NY, verb), "수록한 시군구 중에서는 %s %s(%s)입니다. 동쪽에 있을수록 빨리 뜹니다." % (first[1]["s"], first[1]["g"], key[0])),
           ("서울의 %s 시각은 몇 시인가요?" % verb, "서울 종로구 기준 %s입니다." % hm(sun([r for r in rs if r["s"] == "서울"][0], d)[0 if which == "rise" else 1]))]
    write(path, layout(path, "%d년 %s 시각 - 전국 시군구 순위" % (NY, name), "%d년 %s(%s) 시각을 전국 시군구별로 비교했습니다. 가장 빠른 곳과 늦은 곳을 확인하세요." % (NY, name, verb), "\n".join(body), faq,
                       [("홈", "/"), (name, path)], coupang=True), "0.9")
    for s in ORDER:
        if s not in by_s:
            continue
        sub = [r for r in rs if r["s"] == s]
        _, t2 = rank_table(sub, d, which)
        sp = "%s%s/" % (path, s)
        write(sp, layout(sp, "%s %d년 %s 시각" % (s, NY, name), "%s 시군구별 %d년 %s(%s) 시각 순위입니다." % (s, NY, name, verb),
                         '<div class="page-head"><h1>%s %d년 %s 시각</h1><p>%d년 %d월 %d일 기준</p></div>' % (esc(s), NY, name, d.year, d.month, d.day) + ad() + t2 + '<p><a class="chip" href="%s">전국 순위 보기</a></p>' % path, None,
                         [("홈", "/"), (name, path), (s, sp)], coupang=True), "0.6")
    return path


def page_dates(rs):
    base = dt.date(2027, 1, 1)
    cards = []
    for i in range(365):
        d = base + dt.timedelta(days=i)
        pass
    allds = [dt.date(2028, 1, 1) + dt.timedelta(days=i) for i in range(366)]
    mp = collections.OrderedDict()
    for d in allds:
        mp.setdefault(d.month, []).append(d)
    for d in allds:
        # 2027(평년) 기준으로 계산하되 2/29만 윤년(2028)
        dd_ = d if (d.month == 2 and d.day == 29) else dt.date(2027, d.month, d.day)
        rows = []
        for r in rs:
            a, b, t, cb, ce = sun(r, dd_)
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (rlink(r), hm(a), hm(b), dur(a, b)))
        seoul = [r for r in rs if r["s"] == "서울"][0]
        a, b, *_ = sun(seoul, dd_)
        e = sorted(rs, key=lambda r: (sun(r, dd_)[0], r["i"]))
        p = "/date/%02d-%02d/" % (d.month, d.day)
        lead = "%d월 %d일 서울 종로구의 일출은 %s, 일몰은 %s이며 낮 길이는 %s입니다. 수록 시군구 중 일출이 가장 빠른 곳은 %s %s(%s)입니다." % (d.month, d.day, hm(a), hm(b), dur(a, b), e[0]["s"], e[0]["g"], hm(sun(e[0], dd_)[0]))
        body = ['<div class="page-head"><h1>%d월 %d일 일출·일몰 시간 — 전국 시군구</h1><p>연도에 관계없이 같은 날짜의 대표 시각(1~2분 이내 차이)</p></div>' % (d.month, d.day), '<p class="lead">%s</p>' % esc(lead), ad(),
                '<div class="tbl-wrap"><table class="tbl"><tr><th>시군구</th><th>일출</th><th>일몰</th><th>낮 길이</th></tr>%s</table></div>' % "".join(rows)]
        write(p, layout(p, "%d월 %d일 일출 일몰 시간 - 전국 시군구" % (d.month, d.day), "%d월 %d일 전국 시군구별 일출·일몰 시각과 낮 길이. 서울은 일출 %s, 일몰 %s입니다." % (d.month, d.day, hm(a), hm(b)), "\n".join(body),
                         [("%d월 %d일 서울 일출은 몇 시인가요?" % (d.month, d.day), "서울 종로구 기준 일출 %s, 일몰 %s입니다." % (hm(a), hm(b)))], [("홈", "/"), ("날짜별", "/date/"), ("%d월 %d일" % (d.month, d.day), p)], coupang=True), "0.5")
    chips = "".join('<h2 class="group-title">%d월</h2><div class="chips">%s</div>' % (m, "".join('<a class="chip" href="/date/%02d-%02d/">%d일</a>' % (d.month, d.day, d.day) for d in L)) for m, L in mp.items())
    write("/date/", layout("/date/", "날짜별 일출 일몰 시간", "1월 1일부터 12월 31일까지 날짜별 전국 일출·일몰 시각을 확인하세요.", '<div class="page-head"><h1>날짜별 일출·일몰 시간</h1></div>' + ad() + chips, None, [("홈", "/"), ("날짜별", "/date/")]), "0.8")


def build():
    rs = load()
    months = month_list()
    by_s = collections.defaultdict(list)
    for r in rs:
        by_s[r["s"]].append(r)
    print("시군구", len(rs), "달", months[0], "~", months[-1], "기준연도", REF_YEAR, "새해", NY)
    OUT.mkdir(parents=True, exist_ok=True)
    for ch in OUT.iterdir():
        shutil.rmtree(ch) if ch.is_dir() else ch.unlink()
    for r in rs:
        page_region(r, by_s, months)
    # 시도 허브
    for s in ORDER:
        if s not in by_s:
            continue
        L = by_s[s]
        rows = []
        for r in L:
            a, b, *_ = sun(r, dt.date(NY, 1, 1))
            c, d_, *_ = sun(r, dt.date(REF_YEAR, 6, 21))
            e, f, *_ = sun(r, dt.date(REF_YEAR, 12, 22))
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (rlink(r), hm(a), "%s~%s" % (hm(c), hm(d_)), "%s~%s" % (hm(e), hm(f))))
        body = ['<div class="page-head"><h1>%s 일출·일몰 시간</h1><p>시군구별 새해 첫 일출·하지·동지 시각</p></div>' % esc(s), '<p class="lead">%s의 %d개 시군구 일출·일몰 시각입니다. 시군구를 누르면 오늘과 월별 시간표를 볼 수 있습니다.</p>' % (esc(s), len(L)), ad(),
                '<div class="tbl-wrap"><table class="tbl"><tr><th>시군구</th><th>%d/1/1 일출</th><th>하지 일출~일몰</th><th>동지 일출~일몰</th></tr>%s</table></div>' % (NY, "".join(rows)),
                '<p><a class="chip" href="/haedoji/%d/%s/">%s 해맞이 순위</a></p>' % (NY, q(s), esc(s))]
        write("/region/%s/" % s, layout("/region/%s/" % s, "%s 일출 일몰 시간 - 시군구별" % s, "%s %d개 시군구의 일출·일몰 시각, 새해 첫 일출, 하지·동지 시각을 비교하세요." % (s, len(L)), "\n".join(body), None, [("홈", "/"), ("지역별", "/region/"), (s, "/region/%s/" % s)], coupang=True), "0.8")
    cards = "".join('<a class="card" href="/region/%s/"><b>%s</b><span>%d곳</span></a>' % (q(s), esc(s), len(by_s[s])) for s in ORDER if s in by_s)
    write("/region/", layout("/region/", "지역별 일출 일몰 시간", "시도·시군구별 일출·일몰 시각을 확인하세요.", '<div class="page-head"><h1>지역별 일출·일몰 시간</h1></div>' + ad() + '<div class="card-grid">%s</div>' % cards, None, [("홈", "/"), ("지역별", "/region/")]), "0.8")
    hp = page_rank("haedoji", rs, by_s)
    np_ = page_rank("haenomi", rs, by_s)
    write("/haedoji/", layout("/haedoji/", "해맞이·해넘이 시각", "새해 첫 일출(해맞이)과 한 해 마지막 일몰(해넘이) 시각을 전국 시군구별로 확인하세요.",
                              '<div class="page-head"><h1>해맞이·해넘이 시각</h1></div>' + ad() + '<div class="card-grid"><a class="card" href="%s"><b>%d년 해맞이</b><span>새해 첫 일출 순위</span></a><a class="card" href="%s"><b>%d년 해넘이</b><span>마지막 일몰 순위</span></a></div>' % (hp, NY, np_, NY - 1),
                              None, [("홈", "/"), ("해맞이", "/haedoji/")]), "0.8")
    page_dates(rs)
    # 홈
    reps = [r for s in ORDER for r in by_s.get(s, []) if REP.get(s) == r["g"]]
    cur = {}
    for r in reps:
        for d in (TODAY + dt.timedelta(days=i) for i in range(3)):
            a, b, t, cb, ce = sun(r, d)
            cur.setdefault("%s %s" % (r["s"], r["g"]), {})[d.isoformat()] = [a, b, t, cb, ce]
    seoul = [r for r in rs if r["s"] == "서울"][0]
    ny = sun(seoul, dt.date(NY, 1, 1))
    body = ['<div class="hero"><h1>오늘 우리 동네 일출·일몰 시간</h1><p>전국 %d개 시군구의 일출, 일몰, 낮 길이, 박명 시각을 날짜별로 확인하세요</p>'
            '<div class="today-box" id="today" data-home="1"><div><small id="t-name">서울 종로구 오늘 일출</small><b id="t-rise">-</b></div><div><small>오늘 일몰</small><b id="t-set">-</b></div><div><small>낮 길이</small><b id="t-len">-</b></div><div><small>%d 새해 첫 일출(서울)</small><b>%s</b></div></div></div>' % (len(rs), NY, hm(ny[0])),
            '<div class="search-box"><input id="q" type="search" placeholder="시군구 검색 (예: 강릉시, 해운대, 제주시)" autocomplete="off"><div id="sr" class="sr-list"></div></div>',
            '<div class="chips" id="reps">%s</div>' % "".join('<a class="chip" href="/region/%s/%s/">%s</a>' % (q(r["s"]), q(r["g"]), esc(r["s"] if r["s"] != r["g"] else r["g"])) for r in reps),
            '<script>window.SUNHOME=%s;</script><script src="/assets/js/today.js"></script>' % json.dumps(cur, ensure_ascii=False, separators=(",", ":")), ad(),
            '<h2 class="group-title">해맞이·해넘이</h2><div class="card-grid"><a class="card" href="%s"><b>%d년 해맞이 순위</b><span>새해 첫 일출이 가장 빠른 곳</span></a><a class="card" href="%s"><b>%d년 해넘이 순위</b><span>마지막 일몰 시각</span></a></div>' % (hp, NY, np_, NY - 1),
            '<h2 class="group-title">지역별</h2><div class="card-grid">%s</div>' % cards, '<script src="/assets/js/search.js"></script>']
    faq = [("일출·일몰 시각은 어떻게 계산했나요?", "태양의 위치를 천문 계산으로 구해 태양 중심이 지평선 아래 0°34′일 때를 일출·일몰로 했습니다. 시군구 대표 좌표 기준이며 고도는 0m로 가정했습니다."),
           ("한국천문연구원 값과 같은가요?", "같은 기준(대기굴절·태양 반지름 반영)이라 보통 1분 이내로 일치합니다. 공식 값이 필요하면 한국천문연구원 천문우주지식정보를 확인하세요."),
           ("날씨가 흐려도 일출 시각이 같나요?", "시각은 같지만 구름이 있으면 해가 보이지 않을 수 있습니다. 해맞이는 지역 기상예보를 함께 확인하세요.")]
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "우아일출", "url": BASE + "/", "potentialAction": {"@type": "SearchAction", "target": BASE + "/?q={q}", "query-input": "required name=q"}}]
    write("/", layout("/", "오늘 일출 일몰 시간 - 전국 %d개 시군구 | 우아일출" % len(rs), "오늘 우리 동네 일출·일몰 시간과 낮 길이, 월별 시간표, 새해 해맞이 시각을 전국 %d개 시군구별로 확인하세요." % len(rs), "\n".join(body), faq, None, "website", ld), "1.0")
    idx = [[r["g"], "/region/%s/%s/" % (r["s"], r["g"]), r["s"], "", ""] for r in rs]
    (OUT / "search_index.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pages_static()
    finish()


def pages_static():
    body = ['<div class="page-head"><h1>일출·일몰 시간 보는 방법</h1></div>', ad(),
            '<h2 class="group-title">용어</h2><ul class="lead"><li><b>일출·일몰</b> — 태양 윗부분이 아니라 중심을 기준으로, 대기굴절과 태양 반지름을 반영해 태양 중심이 지평선 아래 0°34′일 때입니다.</li><li><b>남중</b> — 태양이 정남쪽에 와 고도가 가장 높은 시각입니다.</li><li><b>박명</b> — 해 뜨기 전·해 진 뒤 하늘이 어슴푸레 밝은 시간. 이 사이트는 태양 중심이 지평선 아래 6°인 시민박명을 씁니다.</li><li><b>낮 길이</b> — 일출부터 일몰까지의 시간입니다.</li></ul>',
            '<h2 class="group-title">해맞이 팁</h2><ul class="lead"><li>일출 30~40분 전에 전망 지점에 도착하면 붉게 물드는 하늘까지 볼 수 있습니다.</li><li>동해안 일출 명소는 같은 날에도 서쪽 지역보다 일출이 빠릅니다. <a href="/haedoji/%d/">해맞이 순위</a>를 참고하세요.</li><li>구름·안개는 시각과 별개이니 당일 기상예보를 확인하세요.</li></ul>' % NY]
    write("/guide/", layout("/guide/", "일출·일몰 시간 보는 방법", "일출·일몰·남중·박명의 의미와 해맞이 준비 요령을 정리했습니다.", "\n".join(body), None, [("홈", "/"), ("이용 안내", "/guide/")]), "0.4")
    body = ['<div class="page-head"><h1>계산 방법</h1></div>', '<p class="lead">우아일출의 시각은 천문 계산 라이브러리(PyEphem)로 시군구 대표 좌표에서 태양의 위치를 구해 만든 <b>참고값</b>입니다. 대표 좌표는 한국관광공사 TourAPI에 등록된 해당 시군구 장소들의 좌표 중앙값이며, 고도는 0m로 가정합니다. 분 단위 이하는 반올림합니다. 같은 시군구 안에서도 위치·고도에 따라 1~2분 차이가 날 수 있고, 공식 값은 한국천문연구원 천문우주지식정보에서 확인할 수 있습니다. 월별 표는 매달 1일 갱신해 앞으로 14개월을 제공합니다.</p>']
    write("/about/", layout("/about/", "계산 방법", "우아일출의 일출·일몰 계산 방법과 한계를 설명합니다.", "\n".join(body), None, [("홈", "/"), ("계산 방법", "/about/")]), "0.3")
    body = ['<div class="page-head"><h1>개인정보처리방침</h1></div>', '<p class="lead">우아일출은 회원가입·로그인 없이 이용하며 개인정보를 수집하지 않습니다. 사이트 개선을 위해 Google Analytics를 사용하고, 광고 게재를 위해 Google AdSense와 쿠팡 파트너스를 사용하며 이 과정에서 쿠키가 사용될 수 있습니다.</p>']
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아일출 개인정보처리방침", "\n".join(body), None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)


def finish():
    shutil.copytree(ROOT / "assets", OUT / "assets")
    for nf in ROOT.glob("naver*.html"):
        shutil.copy(nf, OUT / nf.name)
    today = TODAY.isoformat()
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), today, pr) for p, pr in WRITTEN)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooailchul.wooahouse.com\n", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1></div><div class="chips"><a class="chip" href="/">홈으로</a><a class="chip" href="/region/">지역별</a><a class="chip" href="/haedoji/">해맞이</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("페이지", len(WRITTEN), "(sitemap)")


if __name__ == "__main__":
    build()
