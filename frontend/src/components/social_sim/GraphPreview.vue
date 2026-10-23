<template>
  <div class="gp-root">
    <div ref="chartEl" class="gp-chart" />
    <div class="gp-legend">
      <div class="gp-legend__title">ENTITY TYPES</div>
      <div class="gp-legend__items">
        <div v-for="item in legendItems" :key="item.type" class="gp-legend__item">
          <span class="gp-legend__dot" :style="{ background: item.color }" />
          <span class="gp-legend__label">{{ item.label }}</span>
          <span class="gp-legend__count">{{ item.count }}</span>
        </div>
      </div>
      <div class="gp-legend__meta">
        <span>节点：{{ graph.nodes.length }}</span>
        <span>关系：{{ graph.edges.length }}</span>
      </div>
      <el-switch v-model="showEdgeLabels" active-text="显示边标签" class="gp-legend__switch" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { GraphData, GraphNode } from '@/api/social_sim'

const props = defineProps<{ graph: GraphData; loading?: boolean }>()
const emit = defineEmits<{ (e: 'node-click', node: GraphNode): void }>()

const chartEl = ref<HTMLElement | null>(null)
const showEdgeLabels = ref(true)
let chart: echarts.ECharts | null = null

const TYPE_LABELS: Record<string, string> = {
  Organization: '组织/机构',
  Person: '人物',
  MediaOutlet: '媒体',
  University: '大学/学校',
  Student: '学生',
  Professor: '专家/教授',
  GovernmentAgency: '政府部门',
  LegalAuthority: '司法/法律',
  Alumni: '校友',
  OpinionLeader: '意见领袖',
  Event: '事件',
  Concept: '概念/议题',
  Location: '地点',
  Other: '其他',
}

const legendItems = computed(() => {
  const map = new Map<string, { type: string; label: string; color: string; count: number }>()
  for (const n of props.graph.nodes) {
    const t = n.type || 'Other'
    const exist = map.get(t)
    if (exist) {
      exist.count += 1
    } else {
      map.set(t, { type: t, label: TYPE_LABELS[t] || t, color: n.color || '#999', count: 1 })
    }
  }
  return Array.from(map.values()).sort((a, b) => b.count - a.count)
})

function buildOption(): echarts.EChartsOption {
  const nodes = props.graph.nodes.map((n) => ({
    id: n.id,
    name: n.name,
    value: n.description || n.name,
    symbolSize: 28 + Math.min(22, (props.graph.edges.filter((e) => e.source === n.id || e.target === n.id).length || 1) * 3),
    itemStyle: { color: n.color || '#999' },
    category: n.type || 'Other',
    emphasis: { focus: 'adjacency' as const, label: { show: true } },
    _type: n.type || 'Other',
    _description: n.description || '',
  }))
  const edges = props.graph.edges.map((e) => ({
    source: e.source,
    target: e.target,
    relation: e.relation,
    label: {
      show: showEdgeLabels.value,
      formatter: e.relation,
      fontSize: 11,
      color: '#666',
    },
    lineStyle: { curveness: 0.15 },
  }))

  return {
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => {
        if (p.dataType === 'edge') {
          return `${p.data.source} → ${p.data.target}<br/>${p.data.relation || ''}`
        }
        return `<strong>${p.data.name}</strong><br/>${TYPE_LABELS[p.data._type] || p.data._type}${p.data._description ? '<br/>' + p.data._description : ''}`
      },
    },
    animationDuration: 1200,
    animationEasingUpdate: 'quinticInOut',
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: edges,
        roam: true,
        draggable: true,
        label: { show: true, position: 'right', fontSize: 12, formatter: '{b}' },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [4, 10],
        force: {
          repulsion: 320,
          gravity: 0.08,
          edgeLength: [80, 180],
          layoutAnimation: true,
        },
        emphasis: { focus: 'adjacency', lineStyle: { width: 4 } },
        lineStyle: { color: 'source', curveness: 0.15, width: 1.5 },
        categories: legendItems.value.map((i) => ({ name: i.label })),
      },
    ],
  }
}

function render() {
  if (!chartEl.value) return
  if (!chart) {
    chart = echarts.init(chartEl.value)
    chart.on('click', (params: any) => {
      if (params.dataType === 'node') {
        const node = props.graph.nodes.find((n) => n.id === params.data.id)
        if (node) emit('node-click', node)
      }
    })
    window.addEventListener('resize', resize)
  }
  chart.setOption(buildOption(), true)
}

function resize() {
  chart?.resize()
}

watch(() => props.graph, () => nextTick(render), { deep: true })
watch(showEdgeLabels, () => chart?.setOption(buildOption(), true))

onMounted(() => nextTick(render))
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.gp-root { position: relative; width: 100%; height: 100%; min-height: 0; }
.gp-chart { width: 100%; height: 100%; min-height: 0; }
.gp-legend {
  position: absolute;
  left: 12px;
  bottom: 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  padding: 12px 14px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
  min-width: 170px;
  max-width: 220px;
  backdrop-filter: blur(4px);
}
.gp-legend__title { font-size: 11px; font-weight: 700; color: var(--c-text-3); letter-spacing: 1px; margin-bottom: 8px; }
.gp-legend__items { max-height: 220px; overflow: auto; }
.gp-legend__item { display: flex; align-items: center; gap: 8px; font-size: 12px; margin-bottom: 6px; }
.gp-legend__dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.gp-legend__label { flex: 1; color: var(--c-text-2); }
.gp-legend__count { color: var(--c-text-3); font-size: 11px; }
.gp-legend__meta { display: flex; gap: 12px; font-size: 12px; color: var(--c-text-3); margin: 10px 0 8px; padding-top: 8px; border-top: 1px solid var(--c-border); }
.gp-legend__switch { --el-switch__label-font-size: 12px; }
</style>
