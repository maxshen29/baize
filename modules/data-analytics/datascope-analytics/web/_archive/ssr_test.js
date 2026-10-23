// SSR validation: actually run echarts.setOption on every built option.
// Skips scatter3d (requires WebGL/echarts-gl, browser-only).
global.window = undefined; // force echarts SSR path awareness
const echarts = require("../lib/echarts.min.js");
global.window = global;
require("./js/data.js");
require("./js/charts.js");
const DS = global.DS, DSCharts = global.DSCharts;

let pass = 0, fail = 0;
const errors = [];
for (const key of Object.keys(DS.SAMPLES)) {
  const parsed = DS.parseCSV(DS.SAMPLES[key].csv);
  const fields = DS.inferFields(parsed);
  const nums = fields.filter((f) => f.type === "number").map((f) => f.name);
  const cats = fields.filter((f) => f.type !== "number").map((f) => f.name);
  for (const t of DSCharts.CHART_TYPES) {
    if (t.id === "scatter3d") continue; // needs WebGL
    let enc = { x: null, y: null, z: null, color: null, size: null, filter: null };
    switch (t.id) {
      case "scatter": enc = { x: nums[0], y: nums[1], color: cats[0], size: nums[2] }; break;
      case "bar": case "line": case "area": enc = { x: cats[0], y: nums[0], color: cats[1] }; break;
      case "pie": case "radar": enc = { x: cats[0], y: nums[0], color: cats[1] }; break;
      case "heatmap": enc = { x: cats[0], y: cats[1], size: nums[0] }; break;
      case "boxplot": case "violin": enc = { x: cats[0], y: nums[0], color: cats[1] }; break;
      case "histogram": case "density": enc = { y: nums[0], color: cats[0] }; break;
      case "regression": enc = { x: nums[0], y: nums[1], color: cats[0] }; break;
      case "parallel": enc = { x: nums[0], y: nums[1], z: nums[2], size: nums[3], color: cats[0] }; break;
      case "sankey": enc = { x: cats[0], y: cats[1], size: nums[0] }; break;
    }
    const ctx = { rows: parsed.rows, fields, enc, chartType: t.id, agg: "avg", colorTheme: "vivid", topN: 5, binX: false, stack: false };
    const opt = DSCharts.build(ctx);
    if (opt && opt._warn) { pass++; continue; }
    try {
      const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width: 700, height: 450 });
      chart.setOption(opt);
      chart.renderToSVGString();
      chart.dispose();
      pass++;
    } catch (e) {
      fail++;
      errors.push(`${key}/${t.id}: ${e.message}`);
    }
  }
}
console.log(`SSR RESULT: ${pass} passed, ${fail} failed`);
if (errors.length) console.log(errors.join("\n"));
process.exit(fail ? 1 : 0);
