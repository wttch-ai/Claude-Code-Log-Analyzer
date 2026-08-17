<template>
  <div ref="el" class="chart" :style="{ height }" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { AggregateResult } from '@/types'
import { GRID_HAIRLINE, TEXT_MUTED, colorFor } from '@/utils/charts'
import { fmtAxisPrice, fmtCompact } from '@/utils/format'
import { useDisplayStore } from '@/stores/display'

const props = defineProps<{
  data: AggregateResult
  height?: string
}>()

const el = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const display = useDisplayStore()

function render() {
  if (!chart) return
  const isPrice = display.isPrice
  const dates = props.data.dates
  const series = props.data.series.map((s) => ({
    name: s.name,
    type: 'bar' as const,
    stack: 'total',
    barMaxWidth: 42,
    emphasis: { focus: 'series' as const },
    itemStyle: { color: colorFor(s.name) },
    data: s.values.map((v) => (isPrice ? v.price : v.tokens)),
  }))
  const totalOfDay = dates.map((_, i) =>
    series.reduce((sum, s) => sum + (s.data[i] as number), 0)
  )

  const formatter = (ps: any[]) => {
    const idx = ps[0]?.dataIndex ?? 0
    const lines = ps
      .map((p: any) => {
        const c = colorFor(p.seriesName)
        const v = isPrice ? fmtAxisPrice(p.value) : fmtCompact(p.value)
        return `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${c};margin-right:6px"></span><b>${v}</b> · ${p.seriesName}`
      })
      .join('<br/>')
    const total = isPrice ? fmtAxisPrice(totalOfDay[idx]) : fmtCompact(totalOfDay[idx])
    return `<div style="font-weight:700;margin-bottom:4px">${dates[idx]}</div>${lines}<hr style="margin:6px 0;border:none;border-top:1px solid #eee"/><b>合计 ${total}</b>`
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
        axisLabel: {
          fontSize: 11,
          interval: Math.max(0, Math.floor(dates.length / 16) - 1),
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
.chart { width: 100%; }
</style>
