<template>
  <div ref="el" class="ctc-chart" :style="{ height }" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { TimelineNode, TokenCounts } from '@/types'
import { GRID_HAIRLINE, TEXT_MUTED } from '@/utils/charts'
import { fmtAxisPrice, fmtCompact } from '@/utils/format'
import { TIER3_COLORS, TIER3_LABELS, type TierKey } from '@/utils/tiers'
import { useDisplayStore } from '@/stores/display'

const props = defineProps<{
  nodes: TimelineNode[]
  height?: string
}>()
const emit = defineEmits<{ (e: 'show-detail', rowUuid: string): void }>()

const el = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const display = useDisplayStore()

const T4 = ['input', 'cache_read', 'cache_creation', 'output'] as const
type T4Key = (typeof T4)[number]
const TIERS3: TierKey[] = ['input', 'output', 'cache']

interface Item {
  key: string
  time: string
  kind: 'main' | 'sub'
  depth: number
  agent: string | null
  t4: Record<T4Key, { tokens: number; price: number }>
}

const EMPTY: TokenCounts = { input: 0, cache_read: 0, cache_creation: 0, output: 0, total: 0 }

function fmtHHMM(ts: string | null | undefined): string {
  if (!ts) return '—'
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ts.slice(11, 16)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function flatten(nodes: TimelineNode[], out: Item[] = [], depth = 0): Item[] {
  for (const n of nodes) {
    if (n.type !== 'assistant') continue
    const toks = n.tokens ?? EMPTY
    // 四档 tokens + 价格；价格缺失（未定价）回退 tokens 值
    const bd = (n.price as any)?.breakdown ?? null
    const t4 = {} as Record<T4Key, { tokens: number; price: number }>
    for (const t of T4) {
      t4[t] = {
        tokens: toks[t],
        price: bd ? (bd[t] ?? 0) : toks[t],
      }
    }
    out.push({
      key: n.row_uuid,
      time: fmtHHMM(n.timestamp),
      kind: 'main',
      depth,
      agent: null,
      t4,
    })
    for (const tu of n.tool_uses ?? []) {
      if (tu.subagent) {
        flatten(tu.subagent.nodes, out, depth + 1)
      }
    }
  }
  return out
}

let items: Item[] = []

// 按显示模式取档位值（三分类合并 cache）
function tierVal(it: Item, k: TierKey, isPrice: boolean): number {
  if (k === 'cache') {
    return isPrice ? it.t4.cache_read.price + it.t4.cache_creation.price : it.t4.cache_read.tokens + it.t4.cache_creation.tokens
  }
  return isPrice ? it.t4[k].price : it.t4[k].tokens
}

function render() {
  if (!chart) return
  items = flatten(props.nodes)
  const isPrice = display.isPrice
  const labels = items.map((it) =>
    it.kind === 'main'
      ? it.time
      : '▸'.repeat(Math.min(it.depth, 4)) + ' ' + it.time,
  )

  const series = TIERS3.map((k) => ({
    name: TIER3_LABELS[k],
    type: 'bar' as const,
    stack: 'total',
    barMaxWidth: 30,
    emphasis: { focus: 'series' as const },
    itemStyle: { color: TIER3_COLORS[k] },
    data: items.map((it) => tierVal(it, k, isPrice)),
  }))

  const totals = items.map((it) => TIERS3.reduce((s, k) => s + tierVal(it, k, isPrice), 0))

  const formatter = (ps: any[]) => {
    const idx = ps[0]?.dataIndex ?? 0
    const it = items[idx]
    const kindTag =
      it.kind === 'main'
        ? '<b>主交互</b>'
        : `<b style="color:#1d6fe0">${'▸'.repeat(Math.min(it.depth, 4))} subagent${it.agent ? ' · ' + it.agent : ''}</b>`
    const lines = TIERS3.map((k) => {
      const v = isPrice ? fmtAxisPrice(tierVal(it, k, true)) : fmtCompact(tierVal(it, k, false))
      return `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${TIER3_COLORS[k]};margin-right:6px"></span><b>${v}</b> · ${TIER3_LABELS[k]}`
    }).join('<br/>')
    const cr = isPrice ? fmtAxisPrice(it.t4.cache_read.price) : fmtCompact(it.t4.cache_read.tokens)
    const cc = isPrice ? fmtAxisPrice(it.t4.cache_creation.price) : fmtCompact(it.t4.cache_creation.tokens)
    const total = isPrice ? fmtAxisPrice(totals[idx]) : fmtCompact(totals[idx])
    return `<div style="font-weight:700;margin-bottom:4px">${kindTag} <span style="color:#999;font-weight:400">${it.time}</span></div>${lines}<div style="color:#999;font-size:11px;padding-left:16px;margin-top:2px">├ cache_read ${cr}<br/>└ cache_creation ${cc}</div><hr style="margin:6px 0;border:none;border-top:1px solid #eee"/><b>合计 ${total}</b>`
  }

  chart.setOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter, confine: true },
      grid: { left: 8, right: 16, top: 24, bottom: 46, containLabel: true },
      dataZoom: [
        { type: 'inside', xAxisIndex: 0, start: 0, end: 100 },
        {
          type: 'slider',
          xAxisIndex: 0,
          height: 16,
          bottom: 8,
          start: 0,
          end: 100,
        },
      ],
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: TEXT_MUTED } },
        axisTick: { show: false },
        axisLabel: {
          fontSize: 10,
          interval: 0,
          rotate: 45,
          color: (value: string) => (value.startsWith('▸') ? '#1d6fe0' : '#555'),
        },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: GRID_HAIRLINE } },
        axisLabel: { fontSize: 11, formatter: (v: number) => (isPrice ? fmtAxisPrice(v) : fmtCompact(v)) },
      },
      series,
    },
    true,
  )
}

function onChartClick(params: any) {
  const it = items[params?.dataIndex]
  if (it) emit('show-detail', it.key)
}

function resize() {
  chart?.resize()
}

onMounted(() => {
  chart = echarts.init(el.value!)
  render()
  chart.on('click', onChartClick)
  window.addEventListener('resize', resize)
})
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})
watch(
  () => [props.nodes, display.mode] as const,
  () => render(),
  { deep: true },
)
</script>

<style scoped>
.ctc-chart { width: 100%; }
</style>
