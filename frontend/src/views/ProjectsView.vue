<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="head">
        <span>项目列表（{{ total }}）</span>
        <el-radio-group :model-value="sort" size="small" @update:model-value="changeSort">
          <el-radio-button value="tokens">Tokens</el-radio-button>
          <el-radio-button value="price">价格</el-radio-button>
          <el-radio-button value="sessions">会话</el-radio-button>
          <el-radio-button value="messages">消息</el-radio-button>
        </el-radio-group>
      </div>
    </template>
    <el-table
      :data="items"
      class="clickable"
      @row-click="(r: ProjectItem) => router.push(`/projects/${r.id}`)"
    >
      <el-table-column label="项目" min-width="170">
        <template #default="{ row }"><b>{{ row.name }}</b></template>
      </el-table-column>
      <el-table-column label="cwd" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.cwd || '—' }}</template>
      </el-table-column>
      <el-table-column prop="sessions" label="会话" width="70" align="right" />
      <el-table-column prop="messages" label="消息" width="80" align="right" />
      <el-table-column prop="subagents" label="子会话" width="80" align="right" />
      <el-table-column :label="display.isPrice ? '价格' : 'Tokens'" width="120" align="right">
        <template #default="{ row }">
          <span :class="{ 'price-val': display.isPrice }">
            {{ display.isPrice ? fmtPrice(row.price.total) : fmtTokens(row.tokens.total) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="最后活跃" width="150" align="right">
        <template #default="{ row }">{{ fmtTime(row.last_seen_at) }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import type { ProjectItem } from '@/types'
import { fmtPrice, fmtTime, fmtTokens } from '@/utils/format'
import { useDisplayStore } from '@/stores/display'

const router = useRouter()
const display = useDisplayStore()
const items = ref<ProjectItem[]>([])
const total = ref(0)
const loading = ref(false)
const sort = ref('tokens')

async function load() {
  loading.value = true
  try {
    const r = await api.projects({ sort: sort.value, order: 'desc', limit: 500 })
    items.value = r.items
    total.value = r.total
  } finally {
    loading.value = false
  }
}

function changeSort(v: string) {
  sort.value = v
  load()
}

onMounted(load)
watch(() => display.mode, load)
</script>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.clickable :deep(.el-table__row) { cursor: pointer; }
.price-val { font-weight: 700; color: #e34948; }
</style>
