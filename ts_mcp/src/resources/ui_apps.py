"""
MCP Apps UI 资源模块

注册 ui:// 协议资源，为工具返回提供交互式 HTML 可视化：
- ui://tushare/market-dashboard: 市场概况仪表板（ECharts）
- ui://tushare/macro-panel: 宏观经济指标面板
- ui://tushare/data-table: 通用可交互数据表格

参考：MCP Apps 规范 (SEP-1865)
协议版本：2025-06-18
"""

import logging
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# HTML 模板
# ─────────────────────────────────────────────────────────

MARKET_DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>市场概况</title>
<style>
:root {
  --color-background-primary: light-dark(#ffffff, #1a1a1a);
  --color-text-primary: light-dark(#171717, #e5e5e5);
  --color-text-secondary: light-dark(#6b7280, #9ca3af);
  --color-border-primary: light-dark(#e5e5e5, #333333);
  --font-sans: system-ui, -apple-system, "PingFang SC", "Noto Sans SC", sans-serif;
  --font-mono: "SF Mono", "JetBrains Mono", monospace;
  --border-radius-md: 8px;
  --color-up: #ef4444;
  --color-down: #22c55e;
  --color-flat: #9ca3af;
}
* { margin: 0; box-sizing: border-box; }
body {
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  background: var(--color-background-primary);
  padding: 16px; line-height: 1.5;
}
.header { margin-bottom: 16px; }
.header h2 { font-size: 16px; font-weight: 600; }
.header .sub { font-size: 12px; color: var(--color-text-secondary); margin-top: 2px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 16px; }
.card { border: 1px solid var(--color-border-primary); border-radius: var(--border-radius-md); padding: 14px 12px; }
.stat-value { font-size: 22px; font-weight: 600; font-family: var(--font-mono); letter-spacing: -0.02em; }
.stat-label { font-size: 11px; color: var(--color-text-secondary); margin-top: 4px; }
.up { color: var(--color-up); }
.down { color: var(--color-down); }
.flat { color: var(--color-flat); }
#chart { width: 100%; height: 280px; margin-top: 8px; }
.loading { text-align: center; padding: 48px 0; color: var(--color-text-secondary); font-size: 13px; }
</style>
</head>
<body>
<div id="app" class="loading">等待数据…</div>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<script>
(function(){
  var toolInput = null, toolResult = null;

  window.addEventListener('message', function(e) {
    var msg = e.data;
    if (!msg || !msg.jsonrpc) return;
    switch (msg.method) {
      case 'ui/notifications/tool-input':
        toolInput = msg.params && msg.params.arguments; break;
      case 'ui/notifications/tool-result':
        toolResult = msg.params;
        render(toolResult.structuredContent || parseContent(toolResult.content));
        break;
      case 'ui/notifications/host-context-changed':
        if (msg.params && msg.params.styles && msg.params.styles.variables)
          applyTheme(msg.params.styles.variables);
        break;
    }
    if (msg.id !== undefined && msg.method === 'ui/initialize') {
      window.parent.postMessage({ jsonrpc:'2.0', id: msg.id, result: {
        protocolVersion: '2025-06-18',
        appCapabilities: { availableDisplayModes: ['inline','fullscreen'] }
      }}, '*');
      window.parent.postMessage({ jsonrpc:'2.0', method:'ui/notifications/initialized', params:{} }, '*');
    }
  });

  function parseContent(content) {
    if (!content) return null;
    var arr = Array.isArray(content) ? content : [content];
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].type === 'text') try { return JSON.parse(arr[i].text); } catch(e) {}
    }
    return null;
  }

  function applyTheme(vars) {
    var r = document.documentElement;
    for (var k in vars) if (vars[k]) r.style.setProperty('--' + k, vars[k]);
  }

  function fmt(n) {
    if (n == null) return '-';
    if (Math.abs(n) >= 10000) return (n/10000).toFixed(1) + '万亿';
    if (Math.abs(n) >= 1) return n.toFixed(1);
    return n.toFixed(2);
  }

  function render(raw) {
    if (!raw) return;
    var data = raw.data || raw;
    var app = document.getElementById('app');
    app.classList.remove('loading');
    var ad = data.advance_decline || {};
    var ls = data.limit_stats || {};
    var am = data.amount_stats || {};
    var vs = data.valuation_stats || {};
    var ps = data.pct_chg_stats || {};
    var mkt = data.market === 'all' ? 'A股' : data.market;

    var meanCls = ps.mean > 0 ? 'up' : ps.mean < 0 ? 'down' : '';
    var meanVal = ps.mean != null ? (ps.mean > 0 ? '+' : '') + ps.mean.toFixed(2) + '%' : '-';

    app.innerHTML =
      '<div class="header">' +
        '<h2>' + mkt + '市场概况</h2>' +
        '<div class="sub">' + (data.trade_date || '-') + ' · 共 ' + (data.total_stocks || '-') + ' 只</div>' +
      '</div>' +
      '<div class="grid">' +
        '<div class="card"><div class="stat-value ' + meanCls + '">' + meanVal + '</div><div class="stat-label">平均涨幅</div></div>' +
        '<div class="card"><div class="stat-value up">' + (ad.advance || '-') + '</div><div class="stat-label">上涨 (' + (ad.advance_ratio || 0) + '%)</div></div>' +
        '<div class="card"><div class="stat-value down">' + (ad.decline || '-') + '</div><div class="stat-label">下跌 (' + (ad.decline_ratio || 0) + '%)</div></div>' +
        '<div class="card"><div class="stat-value up">' + (ls.limit_up || 0) + '</div><div class="stat-label">涨停</div></div>' +
        '<div class="card"><div class="stat-value down">' + (ls.limit_down || 0) + '</div><div class="stat-label">跌停</div></div>' +
        '<div class="card"><div class="stat-value">' + fmt(am.total) + '亿</div><div class="stat-label">总成交额</div></div>' +
        '<div class="card"><div class="stat-value">' + (vs.pe_median != null ? vs.pe_median.toFixed(1) : '-') + '</div><div class="stat-label">PE 中位数</div></div>' +
        '<div class="card"><div class="stat-value">' + (vs.pb_median != null ? vs.pb_median.toFixed(2) : '-') + '</div><div class="stat-label">PB 中位数</div></div>' +
      '</div>' +
      '<div id="chart"></div>';
    renderCharts(data);
    notifySize();
  }

  function renderCharts(data) {
    var el = document.getElementById('chart');
    if (!el || !window.echarts) return;
    var c = echarts.init(el);
    var ad = data.advance_decline || {};
    c.setOption({
      tooltip: { trigger:'item', formatter:'{b}: {c} ({d}%)' },
      legend: { bottom: 0, textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie', radius: ['38%','68%'], center: ['50%','45%'],
        padAngle: 2, itemStyle: { borderRadius: 4 },
        label: { formatter:'{b}\\n{c}只', fontSize: 11 },
        data: [
          { value: ad.advance || 0, name:'上涨', itemStyle:{ color:'#ef4444' } },
          { value: ad.flat || 0,    name:'平盘', itemStyle:{ color:'#d1d5db' } },
          { value: ad.decline || 0, name:'下跌', itemStyle:{ color:'#22c55e' } }
        ]
      }]
    });
    window.addEventListener('resize', function() { c.resize(); });
  }

  function notifySize() {
    var h = document.documentElement.scrollHeight;
    window.parent.postMessage({ jsonrpc:'2.0', method:'ui/notifications/size-changed', params:{ height: h } }, '*');
  }
})();
</script>
</body>
</html>"""


MACRO_PANEL_HTML = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>宏观经济面板</title>
<style>
:root {
  --color-background-primary: light-dark(#ffffff, #1a1a1a);
  --color-text-primary: light-dark(#171717, #e5e5e5);
  --color-text-secondary: light-dark(#6b7280, #9ca3af);
  --color-border-primary: light-dark(#e5e5e5, #333333);
  --font-sans: system-ui, -apple-system, "PingFang SC", sans-serif;
  --font-mono: "SF Mono", "JetBrains Mono", monospace;
  --border-radius-md: 8px;
}
* { margin: 0; box-sizing: border-box; }
body { font-family: var(--font-sans); color: var(--color-text-primary); background: var(--color-background-primary); padding: 16px; }
.header { margin-bottom: 16px; }
.header h2 { font-size: 16px; font-weight: 600; }
.header .sub { font-size: 12px; color: var(--color-text-secondary); margin-top: 2px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.card { border: 1px solid var(--color-border-primary); border-radius: var(--border-radius-md); padding: 14px 12px; }
.card-title { font-size: 11px; color: var(--color-text-secondary); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.04em; }
.card-value { font-size: 20px; font-weight: 600; font-family: var(--font-mono); }
.card-detail { font-size: 11px; color: var(--color-text-secondary); margin-top: 4px; }
.card-tag { display: inline-block; font-size: 10px; padding: 1px 6px; border-radius: 4px; margin-top: 6px; font-weight: 500; }
.tag-green { background: #dcfce7; color: #166534; }
.tag-red { background: #fee2e2; color: #991b1b; }
.tag-yellow { background: #fef3c7; color: #92400e; }
.tag-gray { background: #f3f4f6; color: #4b5563; }
.analysis { margin-top: 16px; padding: 12px; border: 1px solid var(--color-border-primary); border-radius: var(--border-radius-md); }
.analysis h3 { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.analysis-item { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 4px; }
.loading { text-align: center; padding: 48px 0; color: var(--color-text-secondary); font-size: 13px; }
</style>
</head>
<body>
<div id="app" class="loading">等待数据…</div>
<script>
(function(){
  window.addEventListener('message', function(e) {
    var msg = e.data;
    if (!msg || !msg.jsonrpc) return;
    if (msg.method === 'ui/notifications/tool-result') {
      var raw = msg.params;
      render(raw.structuredContent || parseContent(raw.content));
    }
    if (msg.method === 'ui/notifications/host-context-changed' && msg.params && msg.params.styles && msg.params.styles.variables) {
      var vars = msg.params.styles.variables;
      for (var k in vars) if (vars[k]) document.documentElement.style.setProperty('--'+k, vars[k]);
    }
    if (msg.id !== undefined && msg.method === 'ui/initialize') {
      window.parent.postMessage({ jsonrpc:'2.0', id:msg.id, result:{ protocolVersion:'2025-06-18', appCapabilities:{ availableDisplayModes:['inline','fullscreen'] } } }, '*');
      window.parent.postMessage({ jsonrpc:'2.0', method:'ui/notifications/initialized', params:{} }, '*');
    }
  });

  function parseContent(c) {
    if (!c) return null;
    var arr = Array.isArray(c) ? c : [c];
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].type === 'text') try { return JSON.parse(arr[i].text); } catch(e) {}
    }
    return null;
  }

  function makeCard(title, value, period, tagClass, tagText, extra) {
    return '<div class="card">' +
      '<div class="card-title">' + title + '</div>' +
      '<div class="card-value">' + value + '</div>' +
      '<div class="card-detail">' + period + (extra ? ' &middot; ' + extra : '') + '</div>' +
      '<span class="card-tag ' + tagClass + '">' + tagText + '</span>' +
    '</div>';
  }

  function render(raw) {
    if (!raw) return;
    var data = raw.data || raw;
    var analysis = raw.analysis || {};
    var app = document.getElementById('app');
    app.classList.remove('loading');
    var cards = '';

    if (data.gdp) {
      var g = data.gdp;
      var gTag = g.gdp_yoy >= 5 ? 'tag-green' : g.gdp_yoy >= 3 ? 'tag-yellow' : 'tag-red';
      var gLabel = g.gdp_yoy >= 5 ? '高增长' : g.gdp_yoy >= 3 ? '中增长' : '低增长';
      cards += makeCard('GDP', g.gdp_yoy != null ? g.gdp_yoy + '%' : '-', g.quarter || '', gTag, gLabel, '');
    }
    if (data.cpi) {
      var c = data.cpi;
      var cTag = c.yoy >= 3 ? 'tag-red' : c.yoy >= 0 ? 'tag-green' : 'tag-yellow';
      var cLabel = c.yoy >= 3 ? '通胀压力' : c.yoy >= 0 ? '温和' : '通缩风险';
      cards += makeCard('CPI', c.yoy != null ? c.yoy + '%' : '-', c.month || '', cTag, cLabel, c.mom != null ? '环比 ' + c.mom + '%' : '');
    }
    if (data.ppi) {
      var p = data.ppi;
      var pTag = p.yoy >= 0 ? 'tag-green' : 'tag-yellow';
      cards += makeCard('PPI', p.yoy != null ? p.yoy + '%' : '-', p.month || '', pTag, p.yoy >= 0 ? '扩张' : '收缩', '');
    }
    if (data.pmi) {
      var m = data.pmi;
      var val = m.manufacturing_pmi || m.value;
      var mTag = val >= 50 ? 'tag-green' : 'tag-red';
      cards += makeCard('制造业 PMI', val != null ? val.toFixed(1) : '-', m.month || m.MONTH || '', mTag, val >= 50 ? '扩张' : '收缩', '');
    }
    if (data.money) {
      var mo = data.money;
      var moTag = mo.m2_yoy >= 10 ? 'tag-green' : mo.m2_yoy >= 8 ? 'tag-yellow' : 'tag-gray';
      cards += makeCard('M2 同比', mo.m2_yoy != null ? mo.m2_yoy + '%' : '-', mo.month || '', moTag, mo.m2_yoy >= 10 ? '宽松' : mo.m2_yoy >= 8 ? '适度' : '中性', '');
    }
    if (data.lpr) {
      var l = data.lpr;
      cards += makeCard('LPR 1Y/5Y', (l.lpr_1y || '-') + ' / ' + (l.lpr_5y || '-'), l.date || '', 'tag-gray', '基准利率', '');
    }

    var analysisHtml = '';
    var keys = Object.keys(analysis);
    if (keys.length > 0) {
      var items = '';
      for (var i = 0; i < keys.length; i++) items += '<div class="analysis-item">&middot; ' + analysis[keys[i]] + '</div>';
      analysisHtml = '<div class="analysis"><h3>综合判断</h3>' + items + '</div>';
    }

    app.innerHTML =
      '<div class="header"><h2>宏观经济面板</h2><div class="sub">数据来源：Tushare Pro</div></div>' +
      '<div class="grid">' + cards + '</div>' +
      analysisHtml;
    window.parent.postMessage({ jsonrpc:'2.0', method:'ui/notifications/size-changed', params:{ height: document.documentElement.scrollHeight } }, '*');
  }
})();
</script>
</body>
</html>"""


DATA_TABLE_HTML = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>数据表格</title>
<style>
:root {
  --color-background-primary: light-dark(#ffffff, #1a1a1a);
  --color-text-primary: light-dark(#171717, #e5e5e5);
  --color-text-secondary: light-dark(#6b7280, #9ca3af);
  --color-border-primary: light-dark(#e5e5e5, #333333);
  --color-row-hover: light-dark(#f9fafb, #222222);
  --font-sans: system-ui, -apple-system, "PingFang SC", sans-serif;
  --font-mono: "SF Mono", "JetBrains Mono", monospace;
}
* { margin: 0; box-sizing: border-box; }
body { font-family: var(--font-sans); color: var(--color-text-primary); background: var(--color-background-primary); padding: 16px; }
.header { margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }
.header h2 { font-size: 15px; font-weight: 600; }
.header .count { font-size: 12px; color: var(--color-text-secondary); }
.search { width: 100%; padding: 6px 10px; border: 1px solid var(--color-border-primary); border-radius: 6px; background: transparent; color: var(--color-text-primary); font-size: 12px; margin-bottom: 10px; outline: none; }
.search:focus { border-color: #3b82f6; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--color-border-primary); font-weight: 600; font-size: 11px; color: var(--color-text-secondary); cursor: pointer; user-select: none; white-space: nowrap; }
th:hover { color: var(--color-text-primary); }
th .arrow { font-size: 10px; margin-left: 2px; }
td { padding: 7px 10px; border-bottom: 1px solid var(--color-border-primary); font-family: var(--font-mono); font-size: 12px; white-space: nowrap; }
tr:hover td { background: var(--color-row-hover); }
.up { color: #ef4444; }
.down { color: #22c55e; }
.right { text-align: right; }
.loading { text-align: center; padding: 48px 0; color: var(--color-text-secondary); font-size: 13px; }
.export-btn { font-size: 11px; padding: 4px 10px; border: 1px solid var(--color-border-primary); border-radius: 5px; background: transparent; color: var(--color-text-primary); cursor: pointer; }
.export-btn:hover { background: var(--color-row-hover); }
</style>
</head>
<body>
<div id="app" class="loading">等待数据…</div>
<script>
(function(){
  var tableData = [], sortCol = null, sortAsc = true, filterText = '';
  var LABELS = { ts_code:'代码', name:'名称', pct_chg:'涨跌幅%', close:'收盘', open:'开盘', high:'最高', low:'最低', pre_close:'昨收', volume:'成交量', amount:'成交额', trade_date:'日期', change:'涨跌额', industry:'行业', turnover_rate:'换手率%', start_price:'起始价', end_price:'终止价', data_points:'数据点' };

  window.addEventListener('message', function(e) {
    var msg = e.data;
    if (!msg || !msg.jsonrpc) return;
    if (msg.method === 'ui/notifications/tool-result') {
      var raw = msg.params;
      render(raw.structuredContent || parseContent(raw.content));
    }
    if (msg.method === 'ui/notifications/host-context-changed' && msg.params && msg.params.styles && msg.params.styles.variables) {
      var vars = msg.params.styles.variables;
      for (var k in vars) if (vars[k]) document.documentElement.style.setProperty('--'+k, vars[k]);
    }
    if (msg.id !== undefined && msg.method === 'ui/initialize') {
      window.parent.postMessage({ jsonrpc:'2.0', id:msg.id, result:{ protocolVersion:'2025-06-18', appCapabilities:{ availableDisplayModes:['inline','fullscreen'] } } }, '*');
      window.parent.postMessage({ jsonrpc:'2.0', method:'ui/notifications/initialized', params:{} }, '*');
    }
  });

  function parseContent(c) {
    if (!c) return null;
    var arr = Array.isArray(c) ? c : [c];
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].type === 'text') try { return JSON.parse(arr[i].text); } catch(e) {}
    }
    return null;
  }

  function render(raw) {
    if (!raw) return;
    var d = raw.data || raw;
    if (Array.isArray(d)) tableData = d;
    else if (d.results) tableData = d.results;
    else if (d.items) tableData = d.items;
    else if (d.top_gainers) tableData = d.top_gainers.concat(d.top_losers || []);
    else if (Array.isArray(d.data)) tableData = d.data;
    else tableData = [d];

    if (!tableData.length) {
      document.getElementById('app').innerHTML = '<div class="loading">无数据</div>';
      return;
    }
    document.getElementById('app').classList.remove('loading');
    renderTable();
  }

  function renderTable() {
    var app = document.getElementById('app');
    var cols = [];
    var first = tableData[0];
    for (var k in first) if (first.hasOwnProperty(k) && k !== 'error') cols.push(k);

    var rows = tableData;
    if (filterText) {
      var q = filterText.toLowerCase();
      rows = rows.filter(function(r) {
        for (var i = 0; i < cols.length; i++) {
          if (String(r[cols[i]] || '').toLowerCase().indexOf(q) >= 0) return true;
        }
        return false;
      });
    }
    if (sortCol) {
      rows = rows.slice().sort(function(a, b) {
        var va = a[sortCol], vb = b[sortCol];
        if (typeof va === 'number' && typeof vb === 'number') return sortAsc ? va - vb : vb - va;
        return sortAsc ? String(va||'').localeCompare(String(vb||'')) : String(vb||'').localeCompare(String(va||''));
      });
    }

    var numCols = {};
    for (var i = 0; i < cols.length; i++) {
      if (typeof tableData[0][cols[i]] === 'number') numCols[cols[i]] = true;
    }

    var ths = '';
    for (var i = 0; i < cols.length; i++) {
      var c = cols[i];
      var arrow = sortCol === c ? (sortAsc ? '&#8593;' : '&#8595;') : '';
      ths += '<th class="' + (numCols[c] ? 'right' : '') + '" data-col="' + c + '">' + (LABELS[c] || c) + '<span class="arrow">' + arrow + '</span></th>';
    }

    var trs = '';
    for (var r = 0; r < rows.length; r++) {
      var tds = '';
      for (var ci = 0; ci < cols.length; ci++) {
        var c = cols[ci];
        var v = rows[r][c];
        var cls = numCols[c] ? 'right' : '';
        if ((c === 'pct_chg' || c === 'change') && typeof v === 'number') {
          cls += v > 0 ? ' up' : v < 0 ? ' down' : '';
          v = (v > 0 ? '+' : '') + v.toFixed(2);
        } else if (typeof v === 'number') {
          v = Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2);
        }
        tds += '<td class="' + cls + '">' + (v != null ? v : '-') + '</td>';
      }
      trs += '<tr>' + tds + '</tr>';
    }

    app.innerHTML =
      '<div class="header"><h2>数据明细</h2><div><span class="count">' + rows.length + ' 条</span> <button class="export-btn" id="exportBtn">导出 CSV</button></div></div>' +
      '<input class="search" placeholder="搜索…" value="' + filterText + '" id="searchInput">' +
      '<table><thead><tr>' + ths + '</tr></thead><tbody>' + trs + '</tbody></table>';

    document.getElementById('searchInput').addEventListener('input', function(e) {
      filterText = e.target.value;
      renderTable();
    });
    document.getElementById('exportBtn').addEventListener('click', exportCSV);

    var headers = app.querySelectorAll('th');
    for (var h = 0; h < headers.length; h++) {
      headers[h].addEventListener('click', function() {
        var col = this.getAttribute('data-col');
        if (sortCol === col) sortAsc = !sortAsc;
        else { sortCol = col; sortAsc = true; }
        renderTable();
      });
    }

    window.parent.postMessage({ jsonrpc:'2.0', method:'ui/notifications/size-changed', params:{ height: document.documentElement.scrollHeight } }, '*');
  }

  function exportCSV() {
    if (!tableData.length) return;
    var cols = Object.keys(tableData[0]);
    var lines = [cols.join(',')];
    for (var i = 0; i < tableData.length; i++) {
      var row = [];
      for (var j = 0; j < cols.length; j++) row.push(JSON.stringify(tableData[i][cols[j]] != null ? tableData[i][cols[j]] : ''));
      lines.push(row.join(','));
    }
    var blob = new Blob(['\\uFEFF' + lines.join('\\n')], { type:'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'data_' + new Date().toISOString().slice(0,10) + '.csv';
    a.click();
  }
})();
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────
# 资源注册
# ─────────────────────────────────────────────────────────

def register_ui_app_resources(mcp: FastMCP):
    """注册 MCP Apps ui:// 交互式 HTML 资源"""

    @mcp.resource(
        "ui://tushare/market-dashboard",
        name="市场概况仪表板",
        description="A股市场整体涨跌、成交、涨停跌停统计的交互式仪表板（ECharts）",
        mime_type="text/html",
        meta={
            "ui": {
                "profile": "mcp-app",
                "csp": {
                    "connectDomains": [],
                    "resourceDomains": ["https://cdn.jsdelivr.net"]
                },
                "prefersBorder": True
            }
        }
    )
    def market_dashboard_resource() -> str:
        return MARKET_DASHBOARD_HTML

    @mcp.resource(
        "ui://tushare/macro-panel",
        name="宏观经济面板",
        description="GDP、CPI、PMI、M2、LPR 等宏观指标的交互式面板",
        mime_type="text/html",
        meta={
            "ui": {
                "csp": {
                    "connectDomains": [],
                    "resourceDomains": []
                },
                "prefersBorder": True
            }
        }
    )
    def macro_panel_resource() -> str:
        return MACRO_PANEL_HTML

    @mcp.resource(
        "ui://tushare/data-table",
        name="数据表格",
        description="可排序、可筛选、可导出 CSV 的通用交互式数据表格",
        mime_type="text/html",
        meta={
            "ui": {
                "csp": {
                    "connectDomains": [],
                    "resourceDomains": []
                },
                "prefersBorder": True
            }
        }
    )
    def data_table_resource() -> str:
        return DATA_TABLE_HTML

    logger.info("✅ Registered 3 ui:// MCP App resources")
