<template>
  <div ref="el" class="tsc-chart" :style="{ height }" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { TierSeriesResult } from '@/types'
import { GRID_HAIRLINE, TEXT_MUTED } from '@/utils/charts'
import { fmtAxisPrice, fmtCompact } from '@/utils/format'
import { TIER3_COLORS, TIER3_KEYS, TIER3_LABELS, type TierKey } from '@/utils/tiers'
import { useDisplayStore } from '@/stores/display'

const props = defineProps<{
  data: TierSeriesResult
  height?: string
}>()

const el = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const display = useDisplayStore()

// 三分类：输入 / 输出 / Cache（cache = cache_read + cache_creation 合并 tokens 与 price）
function merged() {
  const dates = props.data.dates
  const by: Record<string, { tokens: number; price: number }[]> = {}
  for (const t of ['input', 'cache_read', 'cache_creation', 'output']) {
    by[t] = props.data.series.find((s) => s.name === t)?.values ?? dates.map(() => ({ tokens: 0, price: 0 }))
  }
  const row = (i: number, k: TierKey) =>
    k === 'cache'
      ? {
          tokens: by.cache_read[i].tokens + by.cache_creation[i].tokens,
          price: by.cache_read[i].price + by.cache_creation[i].price,
        }
      : { tokens: by[k][i].tokens, price: by[k][i].price }
  return dates.map((_, i) => {
    const out: Record<TierKey, { tokens: number; price: number }> = { input: row(i, 'input'), output: row(i, 'output'), cache: row(i, 'cache') }
    return out
  })
}

function render() {
  if (!chart) return
  const isPrice = display.isPrice
  const dates = props.data.dates
  const rows = merged()
  const series = TIER3_KEYS.map((k) => ({
    name: TIER3_LABELS[k],
    type: 'bar' as const,
    stack: 'total',
    barMaxWidth: 42,
    emphasis: { focus: 'series' as const },
    itemStyle: { color: TIER3_COLORS[k] },
    data: rows.map((r) => (isPrice ? r[k].price : r[k].tokens)),
  }))
  const totalOfDay = rows.map((r) => (isPrice ? r.cache.price + r.input.price + r.output.price : r.cache.tokens + r.input.tokens + r.output.tokens))
  // 细分（cache 拆读/写）
  const sub = dates.map((_, i) => {
    const cr = byIdx('cache_read', i)
    const cc = byIdx('cache_creation', i)
    return { cr, cc }
  })
  function byIdx(name: string, i: number): number {
    const s = props.data.series.find((x) => x.name === name)
    const v = s?.values[i]
    return isPrice ? (v?.price ?? 0) : (v?.tokens ?? 0)
  }

  const formatter = (ps: any[]) => {
    const idx = ps[0]?.dataIndex ?? 0
    const lines = ps
      .map((p: any) => {
        const c = TIER3_COLORS[p.seriesName as TierKey]
        const v = isPrice ? fmtAxisPrice(p.value) : fmtCompact(p.value)
        return `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${c};margin-right:6px"></span><b>${v}</b> · ${p.seriesName}`
      })
      .join('<br/>')
    const s = sub[idx]
    const cr = isPrice ? fmtAxisPrice(s.cr) : fmtCompact(s.cr)
    const cc = isPrice ? fmtAxisPrice(s.cc) : fmtCompact(s.cc)
    const total = isPrice ? fmtAxisPrice(totalOfDay[idx]) : fmtCompact(totalOfDay[idx])
    return `<div style="font-weight:700;margin-bottom:4px">${dates[idx]}</div>${lines}<div style="color:#999;font-size:11px;padding-left:16px;margin-top:2px">├ cache_read ${cr}<br/>└ cache_creation ${cc}</div><hr style="margin:6px 0;border:none;border-top:1px solid #eee"/><b>合计 ${total}</b>`
  }

  chart.setOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter, confine: true },
      legend: {
        type: 'scroll',
        bottom: 0,
        itemWidth: 12,
        itemHeight: 8,
        textStyle: { fontSize: 11 },
      },
      grid: { left: 8, right: 16, top: 16, bottom: 48, containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: TEXT_MUTED } },
        axisTick: { show: false },
        axisLabel: { fontSize: 11, interval: Math.max(0, Math.floor(dates.length / 16) - 1) },
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

function resize() {
  chart?.resize()
}

onMounted(() => {
  chart = echarts.init(el.value!)
  render()
  window.addEventListener('resize', resize)
})
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})
watch(
  () => [props.data, display.mode] as const,
  () => render(),
  { deep: true },
)
</script>

<style scoped>
.tsc-chart { width: 100%; }
</style>
