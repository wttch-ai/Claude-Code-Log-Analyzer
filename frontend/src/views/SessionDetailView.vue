<template>
  <div class="session-detail" v-loading="loading">
    <template v-if="tl">
      <el-page-header @back="router.back()" class="page-head">
        <template #content>
          {{ tl.title || '会话' }}
          <span v-if="tl.agent_name" class="agent-tag">{{ tl.agent_name }}</span>
        </template>
      </el-page-header>

      <div class="summary-cards">
        <StatCard label="总量" :tokens="tl.summary.tokens.total" :price="tl.summary.price.total" />
        <StatCard label="消息数" :tokens="tl.summary.message_count" :price="null" />
        <StatCard label="子会话" :tokens="tl.summary.subagent_count" :price="null" />
        <StatCard
          label="压缩事件"
          :tokens="tl.summary.compactions.length"
          :price="null"
          :sub="compDropped"
        />
        <div class="range-card">
          <div class="label">时间范围</div>
          <div class="value range">{{ fmtTime(tl.started_at) }} → {{ fmtTime(tl.ended_at) }}</div>
        </div>
      </div>

      <SessionChartCard :session-id="tl.session_id" />

      <el-card v-loading="loading">
        <template #header>按天 · 输入 / 输出 / Cache（堆叠）</template>
        <TierStackedChart v-if="tiers" :data="tiers" height="300px" />
      </el-card>

      <el-card v-if="tl">
        <template #header>
          <div class="head">
            <span>对话时间轴 · 每次交互 token（▸ = subagent 并排）</span>
            <span class="hint">点击柱子查看消息详情</span>
          </div>
        </template>
        <ConversationTokenChart :nodes="tl.nodes" height="320px" @show-detail="openDetail" />
      </el-card>

      <el-card>
        <template #header>
          <div class="head">
            <span>对话时间轴（{{ nodeTotal }} 节点）</span>
            <span v-if="tl.summary.compactions.length" class="hint">🗜 = 上下文压缩</span>
          </div>
        </template>
        <div class="timeline">
          <template v-for="(group, gi) in dayGroups" :key="gi">
            <div class="day-head">
              <span class="day-date">{{ group.day }}</span>
              <span class="day-total">
                {{ display.isPrice ? fmtPrice(group.price) : fmtCompact(group.tokens) }}
              </span>
            </div>
            <template v-for="n in group.nodes" :key="n.row_uuid">
              <CompactionMarker v-if="n.type === 'system' && n.compaction" :info="n.compaction" />
              <MessageRow v-else :node="n" :depth="0" @show-detail="openDetail" />
            </template>
          </template>
          <el-empty v-if="!tl.nodes.length" description="无节点" :image-size="70" />
        </div>
      </el-card>
    </template>

    <MessageDetailDrawer v-model="drawerVisible" :row-uuid="currentRowUuid" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import type { TierSeriesResult, TimelineData, TimelineNode } from '@/types'
import MessageDetailDrawer from '@/components/session/MessageDetailDrawer.vue'
import MessageRow from '@/components/session/MessageRow.vue'
import SessionChartCard from '@/components/session/SessionChartCard.vue'
import ConversationTokenChart from '@/components/session/ConversationTokenChart.vue'
import TierStackedChart from '@/components/common/TierStackedChart.vue'
import CompactionMarker from '@/components/session/CompactionMarker.vue'
import StatCard from '@/components/common/StatCard.vue'
import { fmtCompact, fmtPrice, fmtTime } from '@/utils/format'
import { useDisplayStore } from '@/stores/display'

const route = useRoute()
const router = useRouter()
const display = useDisplayStore()

const tl = ref<TimelineData>()
const tiers = ref<TierSeriesResult>()
const loading = ref(true)
const drawerVisible = ref(false)
const currentRowUuid = ref<string | null>(null)

const compDropped = computed(() => {
  const c = tl.value?.summary.compactions ?? []
  const dropped = c.reduce((s, x) => s + (x.dropped_tokens || 0), 0)
  return dropped ? `丢弃 ${fmtCompact(dropped)} tokens` : ''
})

// 按天分组，含子会话递归合计
function collectDay(nodes: TimelineNode[], acc: Map<string, { tokens: number; price: number }>) {
  for (const n of nodes) {
    if (n.timestamp) {
      const day = dayKey(n.timestamp)
      if (!acc.has(day)) acc.set(day, { tokens: 0, price: 0 })
      const total = n.tokens?.total ?? 0
      const price = n.price?.total ?? 0
      acc.get(day)!.tokens += total
      acc.get(day)!.price += price
    }
    for (const tu of n.tool_uses ?? []) {
      if (tu.subagent) collectDay(tu.subagent.nodes, acc)
    }
  }
}

function dayKey(ts: string): string {
  const d = new Date(ts)
  if (isNaN(d.getTime())) return (ts || '').slice(0, 10)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const dayGroups = computed(() => {
  const acc = new Map<string, { tokens: number; price: number }>()
  collectDay(tl.value?.nodes ?? [], acc)
  const groups: { day: string; tokens: number; price: number; nodes: TimelineNode[] }[] = []
  let cur: (typeof groups)[number] | null = null
  for (const n of tl.value?.nodes ?? []) {
    const key = n.timestamp ? dayKey(n.timestamp) : '—'
    if (!cur || cur.day !== key) {
      cur = { day: key, tokens: 0, price: 0, nodes: [] }
      groups.push(cur)
    }
    cur.nodes.push(n)
  }
  for (const g of groups) {
    const s = acc.get(g.day)
    g.tokens = s?.tokens ?? 0
    g.price = s?.price ?? 0
  }
  return groups
})

const nodeTotal = computed(() => {
  let c = 0
  function walk(nodes: TimelineNode[]) {
    for (const n of nodes) {
      c++
      for (const tu of n.tool_uses ?? []) if (tu.subagent) walk(tu.subagent.nodes)
    }
  }
  walk(tl.value?.nodes ?? [])
  return c
})

function openDetail(rowUuid: string) {
  currentRowUuid.value = rowUuid
  drawerVisible.value = true
}

onMounted(async () => {
  try {
    const sid = String(route.params.sessionId)
    const [t, tr] = await Promise.all([
      api.timeline(sid),
      api.tiers({ granularity: 'day', session: sid }),
    ])
    tl.value = t
    tiers.value = tr
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.session-detail { display: flex; flex-direction: column; gap: 14px; }
.page-head { margin-bottom: 4px; }
.agent-tag {
  font-size: 12px; color: #1d6fe0; background: #e8f1fe;
  border-radius: 10px; padding: 1px 10px; margin-left: 8px; font-weight: 400;
}
.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}
.range-card {
  background: #fff; border: 1px solid #eee; border-radius: 10px; padding: 16px 20px;
}
.range-card .label { font-size: 13px; color: #888; }
.range-card .value { font-size: 14px; font-weight: 600; margin-top: 6px; }
.range { font-variant-numeric: tabular-nums; }
.head { display: flex; align-items: center; justify-content: space-between; }
.hint { font-size: 12px; color: #999; }
.timeline { display: flex; flex-direction: column; }
.day-head {
  display: flex; align-items: center; justify-content: space-between;
  background: #f5f7fa; border-radius: 6px;
  padding: 6px 12px; margin: 14px 0 4px;
  position: sticky; top: 0; z-index: 2;
}
.day-head:first-child { margin-top: 0; }
.day-date { font-weight: 700; color: #444; }
.day-total { font-weight: 700; color: #1d6fe0; font-variant-numeric: tabular-nums; }
</style>
