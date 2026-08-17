<template>
  <div class="scan-page">
    <el-card>
      <template #header>
        <div class="head">
          <span>扫描控制</span>
          <span class="status-line">
            <span class="dot" :class="s.running ? 'running' : s.status === 'done' ? 'done' : 'idle'" />
            {{ statusText }}
          </span>
        </div>
      </template>
      <div class="body">
        <div class="btns">
          <el-button
            type="primary"
            :disabled="s.running"
            :loading="s.running"
            @click="start('incremental')"
          >
            增量扫描
          </el-button>
          <el-button
            type="danger"
            plain
            :disabled="s.running"
            @click="startFull"
          >
            全量扫描
          </el-button>
        </div>
        <p class="hint">
          增量：仅解析 mtime/size 变化之文件，已入库消息不重复解析。<br />
          全量：重建全部 6.9 万行数据，约需 2 分钟。
        </p>
        <el-alert v-if="s.error" type="error" :title="s.error" :closable="false" />
      </div>
    </el-card>

    <el-card>
      <template #header>最近扫描明细</template>
      <template v-if="s.id">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="运行 ID">{{ s.id }}</el-descriptions-item>
          <el-descriptions-item label="模式">{{ s.mode }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ s.status }}</el-descriptions-item>
          <el-descriptions-item label="开始">{{ fmtTime(s.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="结束">{{ fmtTime(s.finished_at) }}</el-descriptions-item>
          <el-descriptions-item label="项目数">{{ s.projects_found }}</el-descriptions-item>
          <el-descriptions-item label="主文件">{{ s.main_files }}</el-descriptions-item>
          <el-descriptions-item label="子 agent 文件">{{ s.subagent_files }}</el-descriptions-item>
          <el-descriptions-item label="扫描行数">{{ fmtTokens(s.entries_found) }}</el-descriptions-item>
          <el-descriptions-item label="新增行">{{ fmtTokens(s.new_entries) }}</el-descriptions-item>
          <el-descriptions-item label="未变文件">{{ s.unchanged_files }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <el-empty v-else description="尚未扫描" :image-size="70" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useScanStore } from '@/stores/scan'
import { api } from '@/api'
import { fmtTime, fmtTokens } from '@/utils/format'

const scan = useScanStore()
const s = computed(() => scan.status)

const statusText = computed(() => {
  if (s.value.running) return '扫描中…'
  if (s.value.status === 'done') return '已完成'
  if (s.value.status === 'failed') return '失败'
  return s.value.has_run ? '已扫描' : '未扫描'
})

async function start(mode: 'incremental' | 'full') {
  await api.startScan(mode)
  ElMessage.success(`已触发${mode === 'full' ? '全量' : '增量'}扫描`)
  scan.refresh()
}

async function startFull() {
  await ElMessageBox.confirm('全量扫描将重建全部数据，约需 2 分钟。确认执行？', '全量扫描', {
    type: 'warning',
  })
  await start('full')
}

onMounted(() => scan.refresh())
</script>

<style scoped>
.scan-page { display: flex; flex-direction: column; gap: 14px; }
.head { display: flex; align-items: center; justify-content: space-between; }
.status-line { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #666; }
.dot { width: 9px; height: 9px; border-radius: 50%; }
.dot.running { background: #f5a623; animation: pulse 1s infinite; }
.dot.done { background: #2ea44f; }
.dot.idle { background: #bbb; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}
.btns { display: flex; gap: 10px; }
.hint { font-size: 12px; color: #888; line-height: 1.8; margin-top: 12px; }
</style>
