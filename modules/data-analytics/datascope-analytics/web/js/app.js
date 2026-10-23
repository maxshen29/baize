/* =========================================================================
 * app.js — UI controller for DataScope Analytics
 * Drag-and-drop encoding, multi-dimensional filtering, view switching,
 * HTML views (pivot / data / stats) and export.
 * ========================================================================= */
(function () {
  "use strict";

  const ZONES = [
    { key: "x", label: "X 轴 / 行", hint: "维度或数值" },
    { key: "y", label: "Y 轴 / 值", hint: "数值或维度" },
    { key: "z", label: "Z 轴 (3D)", hint: "数值" },
    { key: "color", label: "颜色", hint: "分类" },
    { key: "size", label: "大小", hint: "数值" },
    { key: "filter", label: "筛选", hint: "点击选值" },
  ];

  const state = {
    rawRows: [],
    fields: [],
    enc: { x: null, y: null, z: null, color: null, size: null, filter: null },
    filterValues: {}, // field -> Set of allowed values
    chartType: "scatter",
    agg: "sum",
    colorTheme: "classic",
    topN: 0,
    binX: false,
    stack: false,
  };

  let chart = null;
  let currentView = "chart";

  /* ------------------------------ DOM refs ------------------------------ */
  const $ = (id) => document.getElementById(id);

  /* ------------------------------ Init ---------------------------------- */
  function init() {
    buildToolbar();
    buildFieldShelf();
    buildEncodingZones();
    buildChartTabs();
    buildOptions();
    $("chart").addEventListener("contextmenu", (e) => e.preventDefault());
    window.addEventListener("resize", () => chart && chart.resize());
    // initial sample
    loadSample("iris");
  }

  /* --------------------------- Data loading ----------------------------- */
  function loadCSVText(text, name) {
    const parsed = DS.parseCSV(text);
    if (!parsed.headers.length) {
      setStatus("解析失败：未识别到表头或数据。", true);
      return;
    }
    state.rawRows = parsed.rows;
    state.fields = DS.inferFields(parsed);
    state.enc = { x: null, y: null, z: null, color: null, size: null, filter: null };
    state.filterValues = {};
    suggestEncodings(state.chartType);
    buildFieldShelf();
    buildEncodingZones();
    setStatus(`已载入「${name || "数据"}」：${parsed.rows.length} 行 × ${parsed.headers.length} 列`);
    render();
  }

  function loadSample(key) {
    const s = DS.SAMPLES[key];
    if (s) loadCSVText(s.csv, s.label);
  }

  function filteredRows() {
    let rows = state.rawRows;
    const f = state.enc.filter;
    if (f && state.filterValues[f] && state.filterValues[f].size) {
      const allowed = state.filterValues[f];
      rows = rows.filter((r) => allowed.has(String(r[f] == null ? "" : r[f])));
    }
    return rows;
  }

  /* ----------------------- Auto-suggest encodings ----------------------- */
  function suggestEncodings(type) {
    const nums = state.fields.filter((f) => f.type === "number");
    const cats = state.fields.filter((f) => f.type !== "number");
    const dates = state.fields.filter((f) => f.type === "date");
    const dims = cats.concat(dates);
    const set = (k, v) => {
      if (!state.enc[k]) state.enc[k] = v;
    };
    if (type === "scatter3d") {
      set("x", nums[0] && nums[0].name);
      set("y", nums[1] && nums[1].name);
      set("z", nums[2] && nums[2].name);
      set("color", dims[0] && dims[0].name);
    } else if (type === "scatter" || type === "regression") {
      set("x", nums[0] && nums[0].name);
      set("y", nums[1] && nums[1].name);
      set("color", dims[0] && dims[0].name);
    } else if (type === "boxplot" || type === "violin") {
      set("x", dims[0] && dims[0].name);
      set("y", nums[0] && nums[0].name);
      set("color", dims[1] && dims[1].name);
    } else if (type === "histogram" || type === "density") {
      set("y", nums[0] && nums[0].name);
      set("color", dims[0] && dims[0].name);
    } else if (type === "pie" || type === "radar") {
      set("x", dims[0] && dims[0].name);
      set("y", nums[0] && nums[0].name);
      set("color", dims[1] && dims[1].name);
    } else if (type === "heatmap" || type === "sankey") {
      set("x", dims[0] && dims[0].name);
      set("y", dims[1] && dims[1].name);
      set("size", nums[0] && nums[0].name);
    } else if (type === "parallel") {
      set("x", nums[0] && nums[0].name);
      set("y", nums[1] && nums[1].name);
      set("z", nums[2] && nums[2].name);
      set("size", nums[3] && nums[3].name);
      set("color", dims[0] && dims[0].name);
    } else {
      // bar / line / area
      set("x", dims[0] && dims[0].name);
      set("y", nums[0] && nums[0].name);
      set("color", dims[1] && dims[1].name);
    }
  }

  /* ------------------------------ Toolbar ------------------------------- */
  function buildToolbar() {
    const tb = $("toolbar");
    tb.innerHTML = "";
    const mkBtn = (label, onClick, cls) => {
      const b = document.createElement("button");
      b.className = "tb-btn " + (cls || "");
      b.textContent = label;
      b.onclick = onClick;
      return b;
    };
    tb.appendChild(mkBtn("📁 上传 CSV", () => $("fileInput").click()));
    tb.appendChild(mkBtn("📋 粘贴数据", showPasteDialog));
    tb.appendChild(mkBtn("🎲 示例数据", (e) => showSampleMenu(e)));
    tb.appendChild(document.createTextNode(" "));
    tb.appendChild(mkBtn("🖼 导出图片", exportPNG));
    tb.appendChild(mkBtn("⬇ 导出筛选后 CSV", exportCSV));

    const file = $("fileInput");
    file.onchange = (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => loadCSVText(reader.result, f.name);
      reader.readAsText(f, "UTF-8");
    };

    // drag file onto window
    const drop = $("dropZone");
    drop.ondragover = (e) => {
      e.preventDefault();
      drop.classList.add("dragover");
    };
    drop.ondragleave = () => drop.classList.remove("dragover");
    drop.ondrop = (e) => {
      e.preventDefault();
      drop.classList.remove("dragover");
      const f = e.dataTransfer.files[0];
      if (f) {
        const reader = new FileReader();
        reader.onload = () => loadCSVText(reader.result, f.name);
        reader.readAsText(f, "UTF-8");
      }
    };
  }

  function showSampleMenu(ev) {
    const menu = document.createElement("div");
    menu.className = "popmenu";
    Object.keys(DS.SAMPLES).forEach((k) => {
      const item = document.createElement("div");
      item.className = "popmenu-item";
      item.textContent = DS.SAMPLES[k].label;
      item.onclick = () => {
        loadSample(k);
        if (menu.parentNode) document.body.removeChild(menu);
      };
      menu.appendChild(item);
    });
    positionMenu(menu, ev);
  }

  function showPasteDialog() {
    const overlay = document.createElement("div");
    overlay.className = "overlay";
    overlay.innerHTML = `
      <div class="dialog">
        <h3>粘贴 CSV 数据</h3>
        <p class="muted">首行作为表头；支持逗号或制表符分隔。</p>
        <textarea id="pasteArea" placeholder="col1,col2,col3&#10;1,2,3&#10;4,5,6"></textarea>
        <div class="dialog-actions">
          <button class="tb-btn" id="pasteCancel">取消</button>
          <button class="tb-btn primary" id="pasteOk">导入</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    $("pasteCancel").onclick = () => document.body.removeChild(overlay);
    $("pasteOk").onclick = () => {
      const t = $("pasteArea").value.trim();
      if (t) loadCSVText(t, "粘贴数据");
      document.body.removeChild(overlay);
    };
  }

  function positionMenu(menu, ev) {
    document.body.appendChild(menu);
    menu.style.left = ev.clientX + "px";
    menu.style.top = ev.clientY + "px";
    const close = (e) => {
      if (!menu.contains(e.target)) {
        if (menu.parentNode) document.body.removeChild(menu);
        document.removeEventListener("click", close);
      }
    };
    setTimeout(() => document.addEventListener("click", close), 0);
  }

  /* --------------------------- Field shelf ------------------------------ */
  function buildFieldShelf() {
    const shelf = $("fieldShelf");
    shelf.innerHTML = "";
    state.fields.forEach((f) => {
      const chip = document.createElement("div");
      chip.className = "field-chip " + f.type;
      chip.draggable = true;
      chip.dataset.field = f.name;
      chip.innerHTML = `
        <span class="dot ${f.type}"></span>
        <span class="fname" title="${f.name}">${f.name}</span>
        <span class="ftype">${f.type === "number" ? "数值" : f.type === "date" ? "日期" : "分类"}</span>`;
      chip.ondragstart = (e) => {
        e.dataTransfer.setData("text/plain", f.name);
        e.dataTransfer.effectAllowed = "copy";
      };
      chip.ondblclick = () => autoAssign(f.name);
      shelf.appendChild(chip);
    });
  }

  function autoAssign(field) {
    const zone = ZONES.find((z) => !state.enc[z.key]);
    if (zone) {
      assignZone(zone.key, field);
    } else {
      setStatus("所有编码区都已占用，先清空一个再拖入。", true);
    }
  }

  /* ------------------------- Encoding zones ----------------------------- */
  function buildEncodingZones() {
    const wrap = $("encodingZones");
    wrap.innerHTML = "";
    ZONES.forEach((z) => {
      const el = document.createElement("div");
      el.className = "zone";
      el.dataset.zone = z.key;
      const f = state.enc[z.key];
      const used = z.key !== "filter" && isFieldUsedElsewhere(z.key);
      el.innerHTML = `
        <div class="zone-label">${z.label}<span class="zone-hint">${z.hint}</span></div>
        <div class="zone-drop ${f ? "filled" : ""}">
          ${f ? chipHTML(f, z.key) : '<span class="placeholder">拖动字段到此</span>'}
        </div>`;
      el.ondragover = (e) => {
        e.preventDefault();
        el.classList.add("over");
      };
      el.ondragleave = () => el.classList.remove("over");
      el.ondrop = (e) => {
        e.preventDefault();
        el.classList.remove("over");
        const fname = e.dataTransfer.getData("text/plain");
        if (fname) assignZone(z.key, fname);
      };
      if (z.key === "filter" && f) {
        el.querySelector(".zone-drop").onclick = (ev) => {
          if (ev.target.closest(".x")) return; // let the remove handler take it
          openFilterPicker(f);
        };
      }
      wrap.appendChild(el);
    });
  }

  function isFieldUsedElsewhere(key) {
    return ZONES.some((z) => z.key !== key && state.enc[z.key] === state.enc[key] && state.enc[key]);
  }

  function chipHTML(field, zone) {
    const fd = state.fields.find((x) => x.name === field);
    const tag = fd ? fd.type : "";
    return `<span class="enc-chip ${tag}" data-field="${field}">
      ${field}
      <span class="x" data-zone="${zone}">×</span>
    </span>`;
  }

  function assignZone(zone, field) {
    state.enc[zone] = field;
    if (zone === "filter") {
      if (!state.filterValues[field]) state.filterValues[field] = new Set();
    }
    buildEncodingZones();
    buildFieldShelf();
    render();
  }

  function clearZone(zone) {
    state.enc[zone] = null;
    if (zone === "filter") state.filterValues = {};
    buildEncodingZones();
    render();
  }

  // delegated removal of enc chips
  document.addEventListener("click", (e) => {
    const x = e.target.closest(".enc-chip .x");
    if (x) {
      clearZone(x.dataset.zone);
    }
  });

  function openFilterPicker(field) {
    const vals = [...new Set(state.rawRows.map((r) => String(r[field] == null ? "" : r[field])))].sort();
    const cur = state.filterValues[field] || new Set();
    const overlay = document.createElement("div");
    overlay.className = "overlay";
    overlay.innerHTML = `
      <div class="dialog">
        <h3>筛选：${field}（${vals.length} 个取值）</h3>
        <div class="filter-list">
          ${vals
            .map(
              (v) =>
                `<label class="frow"><input type="checkbox" value="${v}" ${
                  cur.has(v) || cur.size === 0 ? "checked" : ""
                }/> ${v}</label>`
            )
            .join("")}
        </div>
        <div class="dialog-actions">
          <button class="tb-btn" id="fAll">全选</button>
          <button class="tb-btn" id="fNone">清空</button>
          <button class="tb-btn primary" id="fApply">应用</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector(".filter-list").onclick = (e) => e.stopPropagation();
    $("fAll").onclick = () => overlay.querySelectorAll("input").forEach((i) => (i.checked = true));
    $("fNone").onclick = () => overlay.querySelectorAll("input").forEach((i) => (i.checked = false));
    $("fApply").onclick = () => {
      const set = new Set();
      overlay.querySelectorAll("input:checked").forEach((i) => set.add(i.value));
      state.filterValues[field] = set;
      document.body.removeChild(overlay);
      buildEncodingZones();
      render();
    };
    overlay.onclick = (e) => {
      if (e.target === overlay) document.body.removeChild(overlay);
    };
  }

  /* ----------------------------- Chart tabs ----------------------------- */
  function buildChartTabs() {
    const tabs = $("chartTypeTabs");
    tabs.innerHTML = "";
    const cats = {};
    DSCharts.CHART_TYPES.forEach((t) => {
      (cats[t.cat] = cats[t.cat] || []).push(t);
    });
    Object.keys(cats).forEach((cat) => {
      const group = document.createElement("div");
      group.className = "chart-group";
      group.innerHTML = `<div class="group-label">${cat}</div>`;
      cats[cat].forEach((t) => {
        const b = document.createElement("button");
        b.className = "chart-tab" + (t.id === state.chartType ? " active" : "");
        b.textContent = t.name;
        b.dataset.type = t.id;
        b.onclick = () => selectChartType(t.id);
        group.appendChild(b);
      });
      tabs.appendChild(group);
    });
  }

  function selectChartType(type) {
    state.chartType = type;
    suggestEncodings(type);
    buildChartTabs();
    buildEncodingZones();
    render();
  }

  /* ------------------------------ Options ------------------------------- */
  function buildOptions() {
    const o = $("options");
    o.innerHTML = "";
    // aggregation
    o.appendChild(
      labeledSelect("聚合方式", "agg", [
        ["sum", "求和"], ["avg", "均值"], ["count", "计数"],
        ["max", "最大值"], ["min", "最小值"], ["median", "中位数"],
      ], state.agg, (v) => { state.agg = v; render(); })
    );
    // color theme
    o.appendChild(
      labeledSelect("配色", "theme", [
        ["classic", "经典"], ["academic", "学术"], ["vivid", "鲜明"],
      ], state.colorTheme, (v) => { state.colorTheme = v; render(); })
    );
    // topN
    o.appendChild(
      labeledSelect("Top N", "topn", [
        ["0", "全部"], ["5", "前 5"], ["10", "前 10"], ["15", "前 15"], ["20", "前 20"],
      ], String(state.topN), (v) => { state.topN = +v; render(); })
    );
    // binX checkbox
    o.appendChild(
      labeledCheck("X 轴分箱(数值)", state.binX, (v) => { state.binX = v; render(); })
    );
    // stack checkbox
    o.appendChild(
      labeledCheck("堆叠(颜色分组)", state.stack, (v) => { state.stack = v; render(); })
    );
  }

  function labeledSelect(label, id, opts, val, onChange) {
    const wrap = document.createElement("div");
    wrap.className = "opt-row";
    const sel = document.createElement("select");
    sel.id = id;
    opts.forEach(([v, t]) => {
      const op = document.createElement("option");
      op.value = v;
      op.textContent = t;
      if (String(v) === String(val)) op.selected = true;
      sel.appendChild(op);
    });
    sel.onchange = () => onChange(sel.value);
    wrap.innerHTML = `<label>${label}</label>`;
    wrap.appendChild(sel);
    return wrap;
  }
  function labeledCheck(label, val, onChange) {
    const wrap = document.createElement("div");
    wrap.className = "opt-row";
    const c = document.createElement("input");
    c.type = "checkbox";
    c.checked = val;
    c.onchange = () => onChange(c.checked);
    const lab = document.createElement("label");
    lab.textContent = label;
    lab.prepend(c);
    wrap.appendChild(lab);
    return wrap;
  }

  /* ------------------------------- Render ------------------------------- */
  function render() {
    if (!chart) chart = echarts.init($("chart"), null, { renderer: "canvas" });
    updateZoneHint();
    if (currentView !== "chart") {
      renderHTMLView();
      return;
    }
    const ctx = {
      rows: filteredRows(),
      fields: state.fields,
      enc: state.enc,
      chartType: state.chartType,
      agg: state.agg,
      colorTheme: state.colorTheme,
      topN: state.topN,
      binX: state.binX,
      stack: state.stack,
    };
    const option = DSCharts.build(ctx);
    if (option && option._warn) {
      setStatus("⚠ " + option._warn, true);
      chart.clear();
      showChartMsg(option._warn);
      return;
    }
    setStatus(`当前视图：${chartName()} · ${ctx.rows.length} 行（已筛选）`);
    clearChartMsg();
    chart.setOption(option, true);
    chart.resize();
  }

  function updateZoneHint() {
    const uses = DSCharts.describe(state.chartType);
    document.querySelectorAll(".zone").forEach((el) => {
      const k = el.dataset.zone;
      el.classList.toggle("needed", uses.includes(k));
    });
  }

  function chartName() {
    const t = DSCharts.CHART_TYPES.find((x) => x.id === state.chartType);
    return t ? t.name : state.chartType;
  }

  function showChartMsg(msg) {
    let m = $("chartMsg");
    if (!m) {
      m = document.createElement("div");
      m.id = "chartMsg";
      m.className = "chart-msg";
      $("chart").parentNode.appendChild(m);
    }
    m.textContent = msg;
    m.style.display = "flex";
  }
  function clearChartMsg() {
    const m = $("chartMsg");
    if (m) m.style.display = "none";
  }

  function setStatus(msg, warn) {
    const s = $("statusBar");
    s.textContent = msg;
    s.className = warn ? "warn" : "";
  }

  /* --------------------------- View switching --------------------------- */
  function buildViewTabs() {
    const vt = $("viewTabs");
    [["chart", "📊 图表"], ["pivot", "📑 数据透视"], ["table", "🔢 数据表"], ["stats", "📈 统计摘要"]].forEach(
      ([id, label]) => {
        const b = document.createElement("button");
        b.className = "view-tab" + (id === currentView ? " active" : "");
        b.textContent = label;
        b.onclick = () => switchView(id);
        vt.appendChild(b);
      }
    );
  }
  function switchView(v) {
    currentView = v;
    document.querySelectorAll(".view-tab").forEach((b) =>
      b.classList.toggle("active", b.textContent.includes(viewLabel(v)))
    );
    $("chartPanel").style.display = v === "chart" ? "" : "none";
    $("htmlPanel").style.display = v === "chart" ? "none" : "";
    if (v !== "chart" && chart) chart.clear();
    render();
  }
  function viewLabel(v) {
    return { chart: "图表", pivot: "数据透视", table: "数据表", stats: "统计摘要" }[v];
  }

  /* ---------------------------- HTML views ------------------------------ */
  function renderHTMLView() {
    const panel = $("htmlPanel");
    const rows = filteredRows();
    if (currentView === "pivot") panel.innerHTML = buildPivot(rows);
    else if (currentView === "table") panel.innerHTML = buildDataTable(rows);
    else if (currentView === "stats") panel.innerHTML = buildStats(rows);
  }

  function buildPivot(rows) {
    const xf = state.enc.x,
      cf = state.enc.color,
      mf = state.enc.y;
    if (!xf) return `<div class="empty">请把一个字段拖到 <b>X 轴 / 行</b> 作为透视行维度。</div>`;
    const mode = mf && isNum(state.fields, mf) ? state.agg : "count";
    const measure = mf || xf;
    const rowCats = [...new Set(rows.map((r) => String(r[xf] == null ? "" : r[xf])))].sort();
    const colCats = cf ? [...new Set(rows.map((r) => String(r[cf] == null ? "" : r[cf])))].sort() : ["合计"];
    const agg = (rc, cc) => {
      const sub = rows.filter(
        (r) =>
          String(r[xf] == null ? "" : r[xf]) === rc &&
          (!cf || String(r[cf] == null ? "" : r[cf]) === cc)
      );
      const vals = sub.map((r) => DS.toNumber(r[measure])).filter((v) => !isNaN(v));
      return DS.aggFn(mode)(vals);
    };
    let html = `<h3>数据透视表</h3>
      <p class="muted">行：${xf} ｜ 列：${cf || "—"} ｜ 值：${measure}（${mode}） ｜ 共 ${rows.length} 行</p>
      <div class="table-scroll"><table class="pivot"><thead><tr>
        <th>${xf}</th>${colCats.map((c) => `<th>${c}</th>`).join("")}<th>行合计</th>
      </tr></thead><tbody>`;
    let grand = 0;
    const colTotals = colCats.map(() => 0);
    rowCats.forEach((rc) => {
      let rowTotal = 0;
      html += `<tr><th>${rc}</th>`;
      colCats.forEach((cc, ci) => {
        const v = agg(rc, cc);
        rowTotal += v;
        colTotals[ci] += v;
        html += `<td>${fmt(v)}</td>`;
      });
      grand += rowTotal;
      html += `<td class="total">${fmt(rowTotal)}</td></tr>`;
    });
    html += `<tr class="total-row"><th>列合计</th>${colTotals
      .map((c) => `<td class="total">${fmt(c)}</td>`)
      .join("")}<td class="total">${fmt(grand)}</td></tr>`;
    html += `</tbody></table></div>`;
    return html;
  }

  function buildDataTable(rows) {
    const headers = state.fields.map((f) => f.name);
    const limit = Math.min(rows.length, 300);
    let html = `<h3>数据表（显示前 ${limit} / ${rows.length} 行）</h3>
      <div class="table-scroll"><table class="data"><thead><tr>
        ${headers.map((h) => `<th>${h}</th>`).join("")}
      </tr></thead><tbody>`;
    for (let i = 0; i < limit; i++) {
      html += `<tr>${headers.map((h) => `<td>${escapeHtml(rows[i][h])}</td>`).join("")}</tr>`;
    }
    html += `</tbody></table></div>`;
    return html;
  }

  function buildStats(rows) {
    const nums = state.fields.filter((f) => f.type === "number");
    if (!nums.length) return `<div class="empty">没有数值字段可供统计。</div>`;
    let html = `<h3>描述性统计摘要</h3>
      <div class="table-scroll"><table class="stats"><thead><tr>
        <th>字段</th><th>计数</th><th>缺失</th><th>均值</th><th>标准差</th>
        <th>最小</th><th>Q1</th><th>中位数</th><th>Q3</th><th>最大</th><th>总和</th>
      </tr></thead><tbody>`;
    nums.forEach((f) => {
      const s = DS.stats(rows, f.name);
      if (!s) return;
      html += `<tr><th>${f.name}</th>
        <td>${s.count}</td><td>${s.missing}</td>
        <td>${fmt(s.mean)}</td><td>${fmt(s.std)}</td>
        <td>${fmt(s.min)}</td><td>${fmt(s.q1)}</td><td>${fmt(s.median)}</td>
        <td>${fmt(s.q3)}</td><td>${fmt(s.max)}</td><td>${fmt(s.sum)}</td></tr>`;
    });
    html += `</tbody></table></div>`;
    return html;
  }

  /* ------------------------------ Export -------------------------------- */
  function exportPNG() {
    if (!chart) return;
    const url = chart.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" });
    const a = document.createElement("a");
    a.href = url;
    a.download = "datascope_" + state.chartType + ".png";
    a.click();
  }
  function exportCSV() {
    const rows = filteredRows();
    if (!rows.length) return;
    const headers = state.fields.map((f) => f.name);
    const lines = [headers.join(",")];
    rows.forEach((r) => {
      lines.push(headers.map((h) => csvCell(r[h])).join(","));
    });
    const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "datascope_filtered.csv";
    a.click();
    URL.revokeObjectURL(url);
  }
  function csvCell(v) {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }

  /* ------------------------------ Utils -------------------------------- */
  function isNum(fields, f) {
    const fd = fields.find((x) => x.name === f);
    return fd && fd.type === "number";
  }
  function fmt(v) {
    if (v == null || isNaN(v)) return "—";
    if (Math.abs(v) >= 1e6 || (Math.abs(v) < 1e-3 && v !== 0)) return v.toExponential(2);
    return Math.round(v * 1000) / 1000;
  }
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }

  /* ------------------------------ Boot ---------------------------------- */
  document.addEventListener("DOMContentLoaded", () => {
    buildToolbar();
    buildViewTabs();
    init();
  });
})();
