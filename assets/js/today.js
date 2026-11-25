/* 우아일출 — 오늘(KST) 일출·일몰 표시. window.SUN = {"YYYY-MM-DD":[일출,일몰,남중,박명시작,박명종료(분)]} (시군구 페이지) / window.SUNHOME = {"서울 종로구":{...}} (홈) */
(function () {
  function p2(n) { return (n < 10 ? '0' : '') + n; }
  function hm(m) { return p2(Math.floor(m / 60) % 24) + ':' + p2(m % 60); }
  function dur(a, b) { var m = b - a; return Math.floor(m / 60) + '시간 ' + p2(m % 60) + '분'; }
  var k = new Date(Date.now() + (new Date().getTimezoneOffset() + 540) * 60000);
  function key(d) { return d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()); }
  var W = ['일', '월', '화', '수', '목', '금', '토'];
  var data = window.SUN, name = '';
  if (!data && window.SUNHOME) { name = Object.keys(window.SUNHOME)[0]; data = window.SUNHOME[name]; }
  if (!data) return;
  var t = key(k), v = data[t];
  if (!v) { var ks = Object.keys(data).sort(); t = t < ks[0] ? ks[0] : ks[ks.length - 1]; v = data[t]; }
  function set(id, s) { var e = document.getElementById(id); if (e) e.textContent = s; }
  set('t-rise', hm(v[0])); set('t-set', hm(v[1])); set('t-len', dur(v[0], v[1])); set('t-noon', hm(v[2]));
  if (name) set('t-name', name + ' 오늘 일출');
  set('t-date', t.replace(/^(\d+)-(\d+)-(\d+)$/, function (_, y, m, d) { return y + '년 ' + +m + '월 ' + +d + '일(' + W[new Date(+y, +m - 1, +d).getDay()] + ') 기준 · 박명 ' + hm(v[3]) + '~' + hm(v[4]); }));
  var wk = document.getElementById('week');
  if (wk) {
    var base = new Date(k.getFullYear(), k.getMonth(), k.getDate());
    for (var i = 0; i < 7; i++) {
      var d = new Date(base.getTime() + i * 86400000), x = data[key(d)];
      if (!x) continue;
      var tr = wk.insertRow(-1);
      tr.innerHTML = '<th>' + (d.getMonth() + 1) + '월 ' + d.getDate() + '일(' + W[d.getDay()] + ')</th><td>' + hm(x[0]) + '</td><td>' + hm(x[1]) + '</td><td>' + dur(x[0], x[1]) + '</td>';
    }
  }
})();
