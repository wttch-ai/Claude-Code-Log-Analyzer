<template>
  <div class="project-detail" v-loading="loading">
    <el-page-header @back="router.back()" class="page-head">
      <template #content>{{ proj?.name || proj?.slug || '项目' }}</template>
    </el-page-header>

    <el-card class="info-card">
      <div class="meta">
        <span class="meta-item">cwd：<code>{{ proj?.cwd || '—' }}</code></span>
        <span class="meta-item">首次 {{ fmtTime(proj?.first_seen_at) }}</span>
        <span class="meta-item">最近 {{ fmtTime(proj?.last_seen_at) }}</span>
      </div>
    </el-card>

    <el-card>
      <template #header>按天消耗</template>
      <StackedBarChart v-if="byDay" :data="byDay" height="320px" />
    </el-card>

    <el-card>
      <template #header>会话列表（{{ sessions.length }}）</template>
      <el-table
        :data="sessions"
        class="clickable"
        @row-click="(r: SessionItem) => router.push(`/sessions/${r.session_id}`)"
      >
        <el-table-column label="标题" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">{{ row.title || '（无标题）' }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">{{ fmtTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="时长" width="80" align="right">
          <template #default="{ row }">{{ fmtDuration(row.duration_s) }}</template>
        </el-table-column>
        <el-table-column prop="message_count" label="消息" width="70" align="right" />
        <el-table-column prop="subagent_count" label="子会话" width="70" align="right" />
        <el-table-column :label="display.isPrice ? '价格' : 'Tokens'" width="120" align="right">
          <template #default="{ row }">
            <span :class="{ 'price-val': display.isPrice }">
              {{ display.isPrice ? fmtPrice(row.price.total) : fmtTokens(row.tokens.total) }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import type { AggregateResult, ProjectDetail, SessionItem } from '@/types'
import StackedBarChart from '@/components/common/StackedBarChart.vue'
import { fmtDuration, fmtPrice, fmtTime, fmtTokens } from '@/utils/format'
import { useDisplayStore } from '@/stores/display'

const route = useRoute()
const router = useRouter()
const display = useDisplayStore()
const proj = ref<ProjectDetail>()
const sessions = ref<SessionItem[]>([])
const byDay = ref<AggregateResult>()
const loading = ref(true)

const pid = Number(route.params.id)

onMounted(async () => {
  try {
    const [pd, ss, agg] = await Promise.all([
      api.projectDetail(pid),
      api.projectSessions(pid),
      api.aggregate({ dim: 'project', project: pid }),
    ])
    proj.value = pd
    sessions.value = ss
    byDay.value = agg
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.project-detail { display: flex; flex-direction: column; gap: 14px; }
.page-head { margin-bottom: 4px; }
.info-card :deep(.el-card__body) { padding: 12px 18px; }
.meta { display: flex; gap: 24px; flex-wrap: wrap; font-size: 13px; color: #555; }
.meta-item code { background: #f2f4f7; padding: 1px 6px; border-radius: 4px; }
.clickable :deep(.el-table__row) { cursor: pointer; }
.price-val { font-weight: 700; color: #e34948; }
</style>
