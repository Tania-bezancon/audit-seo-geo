document.addEventListener('click', function (e) {
  var b = e.target.closest && e.target.closest('button.copy');
  if (!b) return;
  var pre = b.parentNode.querySelector('pre');
  if (!pre) return;
  var text = pre.textContent, label = b.textContent;
  function done() { b.textContent = b.getAttribute('data-done'); setTimeout(function () { b.textContent = label; }, 1500); }
  function fallback() {
    var r = document.createRange(); r.selectNodeContents(pre);
    var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
    try { document.execCommand('copy'); done(); } catch (err) {}
    s.removeAllRanges();
  }
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback);
  else fallback();
});

(function () {
  var box = document.getElementById('progress');
  var data = document.getElementById('audit-grid');
  if (!box || !data) return;
  var grid = JSON.parse(data.textContent);
  var inputs = [].slice.call(document.querySelectorAll('input.done'));
  var codes = inputs.map(function (i) { return i.getAttribute('data-code'); }).filter(function (c, n, a) { return a.indexOf(c) === n; });
  function key(code) { return 'audit-seo-geo:' + grid.id + ':' + code; }
  function read(code) { try { return localStorage.getItem(key(code)) === '1'; } catch (e) { return false; } }
  function write(code, on) { try { if (on) localStorage.setItem(key(code), '1'); else localStorage.removeItem(key(code)); } catch (e) {} }
  function all(code) { return inputs.filter(function (i) { return i.getAttribute('data-code') === code; }); }
  function fmt(x) { var s = x.toFixed(1); return grid.lang === 'fr' ? s.replace('.', ',') : s; }
  function round1(x) { return Math.round((x + 1e-9) * 10) / 10; }
  // the same calculation as grid_scores in common.py: a criterion counts as fixed once all its tasks are ticked
  function score(done) {
    var rows = {}, code, c;
    for (code in grid.rows) rows[code] = grid.rows[code];
    var byCrit = {};
    codes.forEach(function (t) { c = all(t)[0].getAttribute('data-crit'); if (c) (byCrit[c] = byCrit[c] || []).push(t); });
    for (c in byCrit) if (rows[c] !== null && rows[c] !== undefined && byCrit[c].every(function (t) { return done[t]; })) rows[c] = 2;
    var cats = [];
    'ABCDEF'.split('').forEach(function (L) {
      var v = []; for (code in rows) if (code[0] === L && rows[code] !== null) v.push(rows[code]);
      if (v.length) cats.push(round1(v.reduce(function (a, b) { return a + b; }, 0) / (2 * v.length) * 10));
    });
    return round1(cats.reduce(function (a, b) { return a + b; }, 0) / cats.length);
  }
  function refresh() {
    var done = {}, n = 0;
    codes.forEach(function (c) {
      done[c] = all(c)[0].checked;
      if (done[c]) n++;
      all(c).forEach(function (i) { var t = i.closest('.task'); if (t) t.classList.toggle('is-done', done[c]); });
      var f = document.querySelector('a.first[href="#t-' + c + '"]');
      if (f) f.classList.toggle('is-done', done[c]);
    });
    box.querySelector('.p-count').textContent = box.getAttribute('data-count').replace('{n}', n).replace('{total}', codes.length);
    box.querySelector('.p-bar i').style.width = (codes.length ? Math.round(n / codes.length * 100) : 0) + '%';
    var est = box.querySelector('.p-est'), s = score(done);
    est.textContent = n ? box.getAttribute('data-est').replace('{s}', fmt(s)) : '';
    box.classList.toggle('all-done', n === codes.length && n > 0);
  }
  inputs.forEach(function (i) {
    var c = i.getAttribute('data-code');
    if (i.getAttribute('data-verified') === '1') { i.checked = true; i.disabled = true; }
    else if (read(c)) i.checked = true;
    i.addEventListener('change', function () {
      write(c, i.checked);
      all(c).forEach(function (o) { o.checked = i.checked; });
      refresh();
    });
  });
  refresh();
})();
