/* =========================================================================
 * charts.js — Chart engine for DataScope Analytics
 * Builds ECharts options for every view (basic, SandDance 3D, scientific).
 * Exposes global `DSCharts`.
 * ========================================================================= */
(function (global) {
  "use strict";

  /* ----------------------------- Palettes ------------------------------- */
  const PALETTES = {
    classic: ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
      "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"],
    academic: ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
      "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"],
    vivid: ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6",
      "#EC4899", "#14B8A6", "#F97316", "#6366F1", "#84CC16"],
  };
  const VIRIDIS = ["#440154", "#414487", "#2a788e", "#22a884", "#7ad151", "#fde725"];

  function palette(name) {
    return PALETTES[name] || PALETTES.classic;
  }

  /* ------------------------------ Helpers ------------------------------ */
  function isNumField(fields, f) {
    const fd = fields.find((x) => x.name === f);
    return fd && fd.type === "number";
  }
  function colorOf(pal, i) {
    return pal[i % pal.length];
  }
  function catList(rows, f) {
    const s = new Set();
    rows.forEach((r) => s.add(r[f] == null ? "" : String(r[f])));
    return [...s].sort();
  }
  function scaleSize(rows, sf) {
    const vals = rows.map((r) => DS.toNumber(r[sf])).filter((v) => !isNaN(v));
    if (!vals.length) return () => 10;
    const mn = Math.min.apply(null, vals),
      mx = Math.max.apply(null, vals);
    const span = mx - mn || 1;
    return (v) => 6 + ((v - mn) / span) * 34;
  }

  function aggCatSeries(rows, xf, mf, mode, cf, topN, binX, fields) {
    let xvals = rows.map((r) => {
      if (binX && isNumField(fields, xf)) return binLabel(rows, xf, r[xf]);
      return String(r[xf] == null ? "" : r[xf]);
    });
    let catSet = [...new Set(xvals)];
    if (topN && topN > 0 && catSet.length > topN) {
      const totals = {};
      catSet.forEach((c) => (totals[c] = 0));
      rows.forEach((r, i) => {
        const v = DS.toNumber(r[mf]);
        if (!isNaN(v)) totals[xvals[i]] += v;
      });
      catSet = catSet
        .sort((a, b) => (totals[b] || 0) - (totals[a] || 0))
        .slice(0, topN);
    }
    const colorCats = cf
      ? catList(rows, cf)
      : ["_all"];
    const seriesMap = {};
    colorCats.forEach((cc) => {
      seriesMap[cc] = catSet.map((c) => {
        const vals = [];
        rows.forEach((r, i) => {
          if (xvals[i] === c && (!cf || String(r[cf] == null ? "" : r[cf]) === cc)) {
            const v = DS.toNumber(r[mf]);
            if (!isNaN(v)) vals.push(v);
          }
        });
        return DS.aggFn(mode)(vals);
      });
    });
    return { cats: catSet, seriesMap, colorCats };
  }

  function binLabel(rows, xf, raw) {
    const v = DS.toNumber(raw);
    if (isNaN(v)) return "NA";
    const all = rows.map((r) => DS.toNumber(r[xf])).filter((x) => !isNaN(x));
    const mn = Math.min.apply(null, all),
      mx = Math.max.apply(null, all);
    const bins = 12;
    const span = mx - mn || 1;
    let idx = Math.floor(((v - mn) / span) * bins);
    if (idx >= bins) idx = bins - 1;
    if (idx < 0) idx = 0;
    const a = mn + (idx * span) / bins;
    const b = a + span / bins;
    return a.toFixed(1) + "~" + b.toFixed(1);
  }

  function warn(msg) {
    return { _warn: msg };
  }

  /* --------------------------- Chart registry -------------------------- */
  const CHART_TYPES = [
    { id: "scatter", name: "散点图", cat: "基础", uses: ["x", "y", "color", "size"] },
    { id: "scatter3d", name: "3D 散点 · SandDance", cat: "SandDance", uses: ["x", "y", "z", "color", "size"] },
    { id: "bar", name: "柱状图", cat: "基础", uses: ["x", "y", "color"] },
    { id: "line", name: "折线图", cat: "基础", uses: ["x", "y", "color"] },
    { id: "area", name: "面积图", cat: "基础", uses: ["x", "y", "color"] },
    { id: "pie", name: "饼图", cat: "基础", uses: ["x", "y"] },
    { id: "heatmap", name: "热力图", cat: "基础", uses: ["x", "y", "size", "color"] },
    { id: "radar", name: "雷达图", cat: "基础", uses: ["x", "y", "color"] },
    { id: "boxplot", name: "箱线图", cat: "科研", uses: ["x", "y", "color"] },
    { id: "histogram", name: "直方图", cat: "科研", uses: ["y"] },
    { id: "density", name: "密度图 KDE", cat: "科研", uses: ["y", "color"] },
    { id: "violin", name: "小提琴图", cat: "科研", uses: ["x", "y", "color"] },
    { id: "regression", name: "回归散点", cat: "科研", uses: ["x", "y", "color"] },
    { id: "parallel", name: "平行坐标", cat: "科研", uses: ["x", "y", "z", "size", "color"] },
    { id: "sankey", name: "桑基图", cat: "关系", uses: ["x", "y", "size"] },
  ];

  /* ------------------------------ Builders ----------------------------- */
  const builders = {
    scatter(ctx) {
      const { rows, enc, colorTheme } = ctx;
      const pal = palette(colorTheme);
      if (!enc.x || !enc.y) return warn("散点图需要 X 与 Y 字段");
      const mk = (sub, name) => ({
        name,
        type: "scatter",
        data: sub.map((r) => [
          DS.toNumber(r[enc.x]),
          DS.toNumber(r[enc.y]),
          enc.size ? scaleSize(rows, enc.size)(DS.toNumber(r[enc.size])) : 10,
          r[enc.color] || name,
          rows.indexOf(r),
        ]),
        symbolSize: (d) => d[2] || 10,
        itemStyle: enc.color ? { color: colorOf(pal, mk._i) } : undefined,
      });
      const groups = enc.color ? catList(rows, enc.color) : ["_all"];
      const series = groups.map((g, i) => {
        const sub = enc.color ? rows.filter((r) => String(r[enc.color]) === g) : rows;
        const s = mk(sub, g);
        s._i = i;
        s.itemStyle = enc.color ? { color: colorOf(pal, i), opacity: 0.8 } : { opacity: 0.75 };
        return s;
      });
      return {
        tooltip: {
          formatter: (p) =>
            `${enc.x}=${p.data[0]}<br/>${enc.y}=${p.data[1]}` +
            (enc.color ? `<br/>${enc.color}=${p.data[3]}` : ""),
        },
        legend: enc.color ? { data: groups, top: 4 } : { show: false },
        grid: { left: 60, right: 24, top: enc.color ? 40 : 24, bottom: 50 },
        xAxis: { name: enc.x, type: isNumField(ctx.fields, enc.x) ? "value" : "category", scale: true },
        yAxis: { name: enc.y, type: "value", scale: true },
        dataZoom: [{ type: "inside" }, { type: "slider", height: 16, bottom: 12 }],
        series,
      };
    },

    scatter3d(ctx) {
      const { rows, enc, colorTheme } = ctx;
      const pal = palette(colorTheme);
      if (!enc.x || !enc.y || !enc.z) return warn("3D 散点需要 X、Y、Z 三个数值字段");
      const groups = enc.color ? catList(rows, enc.color) : ["_all"];
      const series = groups.map((g, i) => {
        const sub = enc.color ? rows.filter((r) => String(r[enc.color]) === g) : rows;
        return {
          type: "scatter3D",
          name: g,
          data: sub.map((r) => [
            DS.toNumber(r[enc.x]),
            DS.toNumber(r[enc.y]),
            DS.toNumber(r[enc.z]),
          ]),
          symbolSize: enc.size ? 6 : 8,
          itemStyle: enc.color ? { color: colorOf(pal, i), opacity: 0.85 } : { opacity: 0.85 },
        };
      });
      return {
        tooltip: {},
        legend: enc.color ? { show: true, top: 0 } : { show: false },
        xAxis3D: { name: enc.x, type: "value" },
        yAxis3D: { name: enc.y, type: "value" },
        zAxis3D: { name: enc.z, type: "value" },
        grid3D: {
          axisLabel: { show: true },
          environment: "#f7f9fc",
          viewControl: { autoRotate: false, distance: 180 },
          boxWidth: 100, boxDepth: 100, boxHeight: 100,
        },
        series,
      };
    },

    bar(ctx) {
      return catAxisChart(ctx, "bar");
    },
    line(ctx) {
      return catAxisChart(ctx, "line", false);
    },
    area(ctx) {
      return catAxisChart(ctx, "line", true);
    },

    pie(ctx) {
      const { rows, enc, agg, colorTheme } = ctx;
      const pal = palette(colorTheme);
      if (!enc.x) return warn("饼图需要 X（分类）字段");
      const mf = enc.y || enc.x;
      const mode = isNumField(ctx.fields, mf) ? agg : "count";
      const agg2 = DS.aggregate(rows, [enc.x], mf, mode);
      agg2.sort((a, b) => b.value - a.value);
      const data = agg2.map((d, i) => ({
        name: d.dims[0],
        value: d.value,
        itemStyle: { color: colorOf(pal, i) },
      }));
      return {
        tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
        legend: { type: "scroll", orient: "vertical", right: 8, top: 10 },
        series: [
          {
            type: "pie",
            radius: ["38%", "70%"],
            center: ["42%", "52%"],
            data,
            label: { formatter: "{b}\n{d}%" },
            emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0,0,0,0.2)" } },
          },
        ],
      };
    },

    heatmap(ctx) {
      const { rows, enc, agg, colorTheme } = ctx;
      if (!enc.x || !enc.y) return warn("热力图需要 X 与 Y 两个维度字段");
      const mf = enc.size && isNumField(ctx.fields, enc.size) ? enc.size : null;
      const mode = mf ? agg : "count";
      const measure = mf || enc.x;
      const res = DS.aggregate(rows, [enc.x, enc.y], measure, mode);
      const xCats = catList(rows, enc.x);
      const yCats = catList(rows, enc.y);
      const xIdx = {};
      xCats.forEach((c, i) => (xIdx[c] = i));
      const yIdx = {};
      yCats.forEach((c, i) => (yIdx[c] = i));
      const data = res.map((d) => [xIdx[d.dims[0]], yIdx[d.dims[1]], d.value]);
      let max = Math.max.apply(null, data.map((d) => d[2]).concat([1]));
      return {
        tooltip: {
          formatter: (p) =>
            `${enc.x}=${xCats[p.data[0]]}<br/>${enc.y}=${yCats[p.data[1]]}<br/>值=${p.data[2]}`,
        },
        grid: { left: 90, right: 20, top: 20, bottom: 70 },
        xAxis: { type: "category", data: xCats, axisLabel: { rotate: 45 } },
        yAxis: { type: "category", data: yCats },
        visualMap: {
          min: 0, max, calculable: true, orient: "horizontal", bottom: 10,
          inRange: { color: VIRIDIS },
        },
        series: [{ type: "heatmap", data, emphasis: { itemStyle: { borderColor: "#333", borderWidth: 1 } } }],
      };
    },

    radar(ctx) {
      const { rows, enc, agg, colorTheme } = ctx;
      const pal = palette(colorTheme);
      if (!enc.x) return warn("雷达图需要 X（维度）字段");
      const mf = enc.y && isNumField(ctx.fields, enc.y) ? enc.y : enc.x;
      const mode = isNumField(ctx.fields, mf) ? agg : "count";
      const xCats = catList(rows, enc.x);
      const colorCats = enc.color ? catList(rows, enc.color) : ["_all"];
      const indicator = xCats.map((c) => ({ name: c, max: 1 }));
      const seriesData = colorCats.map((cc) => {
        const vals = xCats.map((xc) => {
          const sub = rows.filter(
            (r) =>
              String(r[enc.x]) === xc &&
              (!enc.color || String(r[enc.color]) === cc)
          );
          const v = sub.map((r) => DS.toNumber(r[mf])).filter((x) => !isNaN(x));
          return DS.aggFn(mode)(v);
        });
        return { value: vals, name: cc };
      });
      const mx = Math.max.apply(null, seriesData.flatMap((s) => s.value).concat([1]));
      indicator.forEach((i) => (i.max = mx * 1.1));
      return {
        tooltip: {},
        legend: enc.color ? { data: colorCats, top: 4 } : { show: false },
        radar: { indicator, radius: "68%", center: ["50%", "56%"] },
        series: [
          {
            type: "radar",
            data: seriesData.map((d, i) => ({
              ...d,
              areaStyle: { opacity: 0.15 },
              lineStyle: { color: colorOf(pal, i), width: 2 },
              itemStyle: { color: colorOf(pal, i) },
            })),
          },
        ],
      };
    },

    boxplot(ctx) {
      const { rows, enc, colorTheme } = ctx;
      const pal = palette(colorTheme);
      if (!enc.x || !enc.y) return warn("箱线图需要 X（分类）与 Y（数值）字段");
      if (!isNumField(ctx.fields, enc.y)) return warn("Y 字段必须是数值类型");
      const xCatsAll = catList(rows, enc.x);
      const colorCats = enc.color ? catList(rows, enc.color) : ["_all"];
      // per-(xc,cc) value arrays
      const cell = {};
      const xcMedian = {};
      xCatsAll.forEach((xc) => {
        xcMedian[xc] = null;
        colorCats.forEach((cc) => {
          const sub = rows
            .filter(
              (r) =>
                String(r[enc.x]) === xc &&
                (!enc.color || String(r[enc.color]) === cc)
            )
            .map((r) => DS.toNumber(r[enc.y]))
            .filter((v) => !isNaN(v))
            .sort((a, b) => a - b);
          cell[xc + " " + cc] = sub;
          if (sub.length) {
            const m = DS.quantile(sub, 0.5);
            xcMedian[xc] = xcMedian[xc] == null ? m : (xcMedian[xc] + m) / 2;
          }
        });
      });
      // only keep categories that have at least one usable cell
      const xCats = xCatsAll.filter((xc) =>
        colorCats.some((cc) => (cell[xc + " " + cc] || []).length >= 1)
      );
      const series = colorCats.map((cc, ci) => {
        const data = xCats.map((xc) => {
          const sub = cell[xc + " " + cc] || [];
          if (sub.length >= 2) {
            return [
              sub[0],
              DS.quantile(sub, 0.25),
              DS.quantile(sub, 0.5),
              DS.quantile(sub, 0.75),
              sub[sub.length - 1],
            ];
          }
          // single value -> flat box; none -> fallback to category median (no nulls)
          const v = sub.length === 1 ? sub[0] : xcMedian[xc] != null ? xcMedian[xc] : 0;
          return [v, v, v, v, v];
        });
        return {
          name: cc,
          type: "boxplot",
          data,
          itemStyle: { color: colorOf(pal, ci), borderColor: "#333" },
        };
      });
      return {
        tooltip: { trigger: "item" },
        legend: enc.color ? { data: colorCats, top: 4 } : { show: false },
        grid: { left: 60, right: 20, top: enc.color ? 40 : 20, bottom: 50 },
        xAxis: { type: "category", data: xCats, axisLabel: { rotate: 30 } },
        yAxis: { type: "value", name: enc.y, scale: true },
        series,
      };
    },

    histogram(ctx) {
      const { rows, enc, colorTheme } = ctx;
      if (!enc.y || !isNumField(ctx.fields, enc.y)) return warn("直方图需要 Y（数值）字段");
      const vals = rows.map((r) => DS.toNumber(r[enc.y])).filter((v) => !isNaN(v));
      const bins = DS.histogram(vals, 20);
      return {
        tooltip: { trigger: "axis" },
        grid: { left: 60, right: 20, top: 24, bottom: 50 },
        xAxis: { type: "category", data: bins.map((b) => b.center.toFixed(1)), name: enc.y },
        yAxis: { type: "value", name: "频数" },
        series: [
          {
            type: "bar",
            data: bins.map((b) => b.count),
            itemStyle: { color: palette(colorTheme)[0] },
            barCategoryGap: "2%",
          },
        ],
      };
    },

    density(ctx) {
      const { rows, enc, colorTheme } = ctx;
      const pal = palette(colorTheme);
      if (!enc.y || !isNumField(ctx.fields, enc.y)) return warn("密度图需要 Y（数值）字段");
      const groups = enc.color ? catList(rows, enc.color) : ["_all"];
      const allVals = rows.map((r) => DS.toNumber(r[enc.y])).filter((v) => !isNaN(v));
      const mn = Math.min.apply(null, allVals),
        mx = Math.max.apply(null, allVals);
      const grid = [];
      for (let i = 0; i <= 60; i++) grid.push(mn + ((mx - mn) * i) / 60);
      const series = groups.map((g, i) => {
        const sub = enc.color
          ? rows.filter((r) => String(r[enc.color]) === g).map((r) => DS.toNumber(r[enc.y])).filter((v) => !isNaN(v))
          : allVals;
        const dens = DS.kde(sub, grid);
        return {
          name: g,
          type: "line",
          smooth: true,
          showSymbol: false,
          data: grid.map((x, j) => [x, dens[j]]),
          lineStyle: { color: colorOf(pal, i), width: 2 },
          areaStyle: { color: colorOf(pal, i), opacity: 0.12 },
        };
      });
      return {
        tooltip: { trigger: "axis" },
        legend: enc.color ? { data: groups, top: 4 } : { show: false },
        grid: { left: 60, right: 20, top: enc.color ? 40 : 20, bottom: 50 },
        xAxis: { type: "value", name: enc.y, scale: true },
        yAxis: { type: "value", name: "密度" },
        series,
      };
    },

    violin(ctx) {
      const { rows, enc, colorTheme } = ctx;
      const pal = palette(colorTheme);
      if (!enc.x || !enc.y) return warn("小提琴图需要 X（分类）与 Y（数值）字段");
      if (!isNumField(ctx.fields, enc.y)) return warn("Y 字段必须是数值类型");
      const xCats = catList(rows, enc.x);
      const groups = enc.color ? catList(rows, enc.color) : ["_all"];
      const allVals = rows.map((r) => DS.toNumber(r[enc.y])).filter((v) => !isNaN(v));
      const ymn = Math.min.apply(null, allVals),
        ymx = Math.max.apply(null, allVals);
      const grid = [];
      const GN = 50;
      for (let i = 0; i <= GN; i++) grid.push(ymn + ((ymx - ymn) * i) / GN);
      const halfW = 0.38;
      const renderItems = [];
      xCats.forEach((xc, xi) => {
        groups.forEach((g, gi) => {
          const sub = rows
            .filter(
              (r) =>
                String(r[enc.x]) === xc &&
                (!enc.color || String(r[enc.color]) === g)
            )
            .map((r) => DS.toNumber(r[enc.y]))
            .filter((v) => !isNaN(v));
          if (sub.length < 2) return;
          const dens = DS.kde(sub, grid);
          const dmax = Math.max.apply(null, dens.concat([1e-9]));
          const col = colorOf(pal, gi);
          // build polygon points [leftEdge, y] then [rightEdge, y]
          const pts = [];
          for (let i = 0; i <= GN; i++)
            pts.push([xi - halfW * (dens[i] / dmax), grid[i]]);
          for (let i = GN; i >= 0; i--)
            pts.push([xi + halfW * (dens[i] / dmax), grid[i]]);
          renderItems.push({ xi, xc, g, pts, col, n: sub.length, median: DS.quantile(sub.slice().sort((a, b) => a - b), 0.5) });
        });
      });
      return {
        tooltip: {
          formatter: (p) => {
            const it = renderItems[p.dataIndex];
            return `${it.xc}${enc.color ? " · " + it.g : ""}<br/>中位数=${it.median.toFixed(2)}<br/>样本量=${it.n}`;
          },
        },
        grid: { left: 60, right: 20, top: 20, bottom: 50 },
        xAxis: { type: "value", min: -0.6, max: xCats.length - 0.4, interval: 1,
          axisLabel: { formatter: (v) => xCats[Math.round(v)] || "" } },
        yAxis: { type: "value", name: enc.y, scale: true },
        series: [
          {
            type: "custom",
            renderItem: (params, api) => {
              const it = renderItems[params.dataIndex];
              const pts = it.pts.map((p) => api.coord(p));
              return {
                type: "polygon",
                shape: { points: pts },
                style: { fill: it.col, opacity: 0.55, stroke: it.col },
              };
            },
            data: renderItems.map(() => 0),
            encode: { x: 0, y: 1 },
          },
        ],
      };
    },

    regression(ctx) {
      const { rows, enc, colorTheme } = ctx;
      const pal = palette(colorTheme);
      if (!enc.x || !enc.y) return warn("回归散点需要 X 与 Y 两个数值字段");
      if (!isNumField(ctx.fields, enc.x) || !isNumField(ctx.fields, enc.y))
        return warn("X 与 Y 都必须是数值类型");
      const groups = enc.color ? catList(rows, enc.color) : ["_all"];
      const series = [];
      let eqText = "";
      groups.forEach((g, i) => {
        const sub = rows
          .filter((r) => !enc.color || String(r[enc.color]) === g)
          .map((r) => [DS.toNumber(r[enc.x]), DS.toNumber(r[enc.y])])
          .filter((p) => !isNaN(p[0]) && !isNaN(p[1]));
        if (sub.length < 2) return;
        const xs = sub.map((p) => p[0]),
          ys = sub.map((p) => p[1]);
        const n = xs.length;
        const mx = xs.reduce((a, b) => a + b, 0) / n;
        const my = ys.reduce((a, b) => a + b, 0) / n;
        let sxy = 0, sxx = 0, syy = 0;
        for (let k = 0; k < n; k++) {
          sxy += (xs[k] - mx) * (ys[k] - my);
          sxx += (xs[k] - mx) ** 2;
          syy += (ys[k] - my) ** 2;
        }
        const slope = sxx ? sxy / sxx : 0;
        const intercept = my - slope * mx;
        const r2 = sxx && syy ? (sxy * sxy) / (sxx * syy) : 0;
        const xmin = Math.min.apply(null, xs),
          xmax = Math.max.apply(null, xs);
        series.push({
          name: g,
          type: "scatter",
          data: sub,
          symbolSize: 9,
          itemStyle: { color: colorOf(pal, i), opacity: 0.7 },
        });
        series.push({
          name: g + " 拟合",
          type: "line",
          showSymbol: false,
          data: [
            [xmin, slope * xmin + intercept],
            [xmax, slope * xmax + intercept],
          ],
          lineStyle: { color: colorOf(pal, i), width: 2, type: "dashed" },
          tooltip: { show: false },
        });
        eqText += `${g}: y=${slope.toFixed(3)}x${intercept >= 0 ? "+" : ""}${intercept.toFixed(3)} (R²=${r2.toFixed(3)})  `;
      });
      return {
        title: { text: "回归分析", subtext: eqText, left: 8, top: 4,
          subtextStyle: { fontSize: 11, color: "#555" } },
        tooltip: { trigger: "item" },
        legend: { show: !!enc.color, top: 40 },
        grid: { left: 60, right: 24, top: enc.color ? 70 : 50, bottom: 50 },
        xAxis: { type: "value", name: enc.x, scale: true },
        yAxis: { type: "value", name: enc.y, scale: true },
        series,
      };
    },

    parallel(ctx) {
      const { rows, enc, colorTheme } = ctx;
      const pal = palette(colorTheme);
      const axisFields = [enc.x, enc.y, enc.z, enc.size].filter(
        (f) => f && isNumField(ctx.fields, f)
      );
      if (axisFields.length < 2) return warn("平行坐标需要至少 2 个数值字段（X/Y/Z/Size）");
      const colorCats = enc.color ? catList(rows, enc.color) : ["_all"];
      const series = colorCats.map((g, i) => ({
        name: g,
        type: "parallel",
        lineStyle: enc.color
          ? { color: colorOf(pal, i), width: 1.5, opacity: 0.6 }
          : { width: 1.5, opacity: 0.55 },
        data: rows
          .filter((r) => !enc.color || String(r[enc.color]) === g)
          .map((r) => axisFields.map((f) => DS.toNumber(r[f]))),
      }));
      return {
        tooltip: { trigger: "item" },
        legend: enc.color ? { data: colorCats, top: 4 } : { show: false },
        parallelAxis: axisFields.map((f, i) => ({
          dim: i,
          name: f,
          nameLocation: "end",
        })),
        parallel: { left: 50, right: 30, top: enc.color ? 50 : 30, bottom: 30 },
        series,
      };
    },

    sankey(ctx) {
      const { rows, enc, agg, colorTheme } = ctx;
      if (!enc.x || !enc.y) return warn("桑基图需要 X（源）与 Y（目标）两个字段");
      const mf = enc.size && isNumField(ctx.fields, enc.size) ? enc.size : null;
      const mode = mf ? agg : "count";
      const measure = mf || enc.x;
      const res = DS.aggregate(rows, [enc.x, enc.y], measure, mode);
      const nodeSet = new Set();
      res.forEach((d) => {
        nodeSet.add(String(d.dims[0]));
        nodeSet.add(String(d.dims[1]));
      });
      const nodes = [...nodeSet].map((n, i) => ({ name: n, itemStyle: { color: palette(colorTheme)[i % 10] } }));
      const links = res
        .filter((d) => d.dims[0] !== d.dims[1] && d.value > 0)
        .map((d) => ({ source: String(d.dims[0]), target: String(d.dims[1]), value: d.value }));
      if (!links.length) return warn("没有可用的 源→目标 连线");
      return {
        tooltip: { trigger: "item", formatter: (p) => p.dataType === "edge" ? `${p.data.source} → ${p.data.target}: ${p.data.value}` : p.name },
        series: [
          {
            type: "sankey",
            data: nodes,
            links,
            emphasis: { focus: "adjacency" },
            lineStyle: { color: "gradient", opacity: 0.45 },
            label: { fontSize: 11 },
          },
        ],
      };
    },
  };

  function catAxisChart(ctx, type, area) {
    const { rows, enc, agg, colorTheme, topN, binX } = ctx;
    const pal = palette(colorTheme);
    if (!enc.x) return warn(type === "bar" ? "柱状图需要 X 字段" : "该图表需要 X 字段");
    const mf = enc.y && isNumField(ctx.fields, enc.y) ? enc.y : enc.x;
    const mode = isNumField(ctx.fields, mf) ? agg : "count";
    const a = aggCatSeries(rows, enc.x, mf, mode, enc.color, topN, binX, ctx.fields);
    const series = a.colorCats.map((cc, i) => ({
      name: cc,
      type,
      data: a.seriesMap[cc],
      itemStyle: enc.color ? { color: colorOf(pal, i) } : undefined,
      areaStyle: area ? { opacity: 0.25, color: colorOf(pal, 0) } : undefined,
      smooth: type === "line",
      stack: ctx.stack && enc.color ? "total" : undefined,
      barMaxWidth: 40,
    }));
    const isCat = !isNumField(ctx.fields, enc.x) || binX;
    return {
      tooltip: { trigger: "axis", axisPointer: { type: type === "bar" ? "shadow" : "line" } },
      legend: enc.color ? { data: a.colorCats, top: 4 } : { show: false },
      grid: { left: 60, right: 20, top: enc.color ? 40 : 24, bottom: 80 },
      xAxis: { type: isCat ? "category" : "value", data: isCat ? a.cats : undefined, axisLabel: { rotate: a.cats.length > 8 ? 35 : 0 }, name: enc.x },
      yAxis: { type: "value", name: mf + (mode !== "count" ? ` (${mode})` : " (计数)"), scale: true },
      dataZoom: isCat && a.cats.length > 12 ? [{ type: "slider", bottom: 8, height: 16 }, { type: "inside" }] : undefined,
      series,
    };
  }

  /* ------------------------------- Build -------------------------------- */
  function build(ctx) {
    const fn = builders[ctx.chartType];
    if (!fn) return warn("未知图表类型");
    return fn(ctx);
  }

  function describe(typeId) {
    const t = CHART_TYPES.find((x) => x.id === typeId);
    return t ? t.uses : [];
  }

  global.DSCharts = { build, CHART_TYPES, PALETTES, describe };
})(typeof window !== "undefined" ? window : this);
