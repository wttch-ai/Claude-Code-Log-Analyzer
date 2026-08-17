<template>
  <div class="overview">
    <div class="cards">
      <StatCard
        label="总量"
        :tokens="o.totals?.tokens.total ?? 0"
        :price="o.totals?.price.total"
        :sub="tokensSub(o.totals?.tokens)"
      />
      <StatCard label="今日" :tokens="o.today?.tokens.total ?? 0" :price="o.today?.price.total" />
      <StatCard label="近7天" :tokens="o.week?.tokens.total ?? 0" :price="o.week?.price.total" />
      <StatCard label="cache_read 占比" :tokens="o.totals?.tokens.cache_read ?? 0" :price="null" :sub="pct(o.cache_read_ratio)" />
      <StatCard
        label="项目 / 会话"
        :tokens="o.projects_count ?? 0"
        :price="null"
        :sub="`主 ${o.main_sessions ?? 0} · 子 ${o.subagent_sessions ?? 0}`"
      />
      <StatCard label="压缩事件" :tokens="o.compactions?.count ?? 0" :price="null" :sub="`丢弃 ${fmtCompact(o.compactions?.dropped_tokens ?? 0)} tokens`" />
    </div>

    <DateFilterBar
      :start="start"
      :end="end"
      @update:range="(s, e) => { start = s; end = e; loadCharts() }"
    />

    <div class="charts">
      <el-card v-loading="loading" class="chart-card">
        <template #header>按天 × 项目（堆叠）</template>
        <StackedBarChart v-if="byProject" :data="byProject" height="360px" />
      </el-card>
      <el-card v-loading="loading" class="chart-card">
        <template #header>按天 × Skill（堆叠）</template>
        <StackedBarChart v-if="bySkill" :data="bySkill" height="360px" />
      </el-card>
    </div>

    <el-card class="model-card">
      <template #header>模型分布</template>
      <el-table :data="o.models ?? []" size="small">
        <el-table-column prop="model" label="模型" min-width="150" />
        <el-table-column label="tokens" align="right" min-width="110">
          <template #default="{ row }">{{ fmtTokens(row.tokens.total) }}</template>
        </el-table-column>
        <el-table-column label="价格" align="right" min-width="100">
          <template #default="{ row }">{{ fmtPrice(row.price.total) }}</template>
        </el-table-column>
        <el-table-column label="成本占比" align="right" min-width="90">
          <template #default="{ row }">{{ pct(row.cost_share) }}</template>
        </el-table-column>
        <el-table-column label="input" align="right" min-width="90">
          <template #default="{ row }">{{ fmtCompact(row.tokens.input) }}</template>
        </el-table-column>
        <el-table-column label="cache_read" align="right" min-width="100">
          <template #default="{ row }">{{ fmtCompact(row.tokens.cache_read) }}</template>
        </el-table-column>
        <el-table-column label="cache_creation" align="right" min-width="110">
          <template #default="{ row }">{{ fmtCompact(row.tokens.cache_creation) }}</template>
        </el-table-column>
        <el-table-column label="output" align="right" min-width="90">
          <template #default="{ row }">{{ fmtCompact(row.tokens.output) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api'
import type { AggregateResult, OverviewData, TokenCounts } from '@/types'
import DateFilterBar from '@/components/common/DateFilterBar.vue'
import StackedBarChart from '@/components/common/StackedBarChart.vue'
import StatCard from '@/components/common/StatCard.vue'
import { fmtCompact, fmtPrice, fmtTokens, pct } from '@/utils/format'

const o = ref<OverviewData>({} as OverviewData)
const byProject = ref<AggregateResult>()
const bySkill = ref<AggregateResult>()
const start = ref<string>()
const end = ref<string>()
const loading = ref(false)

function tokensSub(t?: TokenCounts): string {
  if (!t) return ''
  return `in ${fmtCompact(t.input)} · cr ${fmtCompact(t.cache_read)} · cc ${fmtCompact(t.cache_creation)} · out ${fmtCompact(t.output)}`
}

async function loadOverview() {
  try {
    o.value = await api.overview()
  } catch {
    /* 忽略 */
  }
}

async function loadCharts() {
  loading.value = true
  try {
    const [p, s] = await Promise.all([
      api.aggregate({ dim: 'project', start: start.value, end: end.value }),
      api.aggregate({ dim: 'skill', start: start.value, end: end.value }),
    ])
    byProject.value = p
    bySkill.value = s
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadOverview()
  loadCharts()
})
</script>

<style scoped>
.overview { display: flex; flex-direction: column; gap: 16px; }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
}
.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 1100px) {
  .charts { grid-template-columns: 1fr; }
}
.chart-card :deep(.el-card__body) { padding: 8px 8px 0; }
</style>
