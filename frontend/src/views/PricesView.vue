<template>
  <div class="prices-page">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="tip"
      title="单价为 USD / 1M tokens。cache_creation 合并为一档。模型精确匹配，否则回退到 * 兜底价；未定价模型返回 priced:false。"
    />

    <el-card v-loading="loading">
      <template #header>
        <div class="head">
          <span>模型价格配置（{{ rows.length }}）</span>
          <div class="actions">
            <el-select v-model="addModel" placeholder="选择未定价模型" size="small" clearable style="width: 180px">
              <el-option v-for="m in unpriced" :key="m" :value="m" :label="m" />
            </el-select>
            <el-button size="small" type="primary" :disabled="!addModel" @click="openAdd">添加</el-button>
            <el-button size="small" @click="applyDefault">按 * 批量兜底</el-button>
          </div>
        </div>
      </template>
      <el-table :data="rows" size="small">
        <el-table-column prop="model" label="模型" min-width="160">
          <template #default="{ row }">
            <b :class="{ fallback: row.model === '*' }">{{ row.model }}</b>
            <span v-if="row.model === '*'" class="fallback-tag">兜底</span>
          </template>
        </el-table-column>
        <el-table-column label="input" align="right" min-width="90">
          <template #default="{ row }">{{ fmtRate(row.input_price) }}</template>
        </el-table-column>
        <el-table-column label="cache_read" align="right" min-width="90">
          <template #default="{ row }">{{ fmtRate(row.cache_read_price) }}</template>
        </el-table-column>
        <el-table-column label="cache_creation" align="right" min-width="100">
          <template #default="{ row }">{{ fmtRate(row.cache_creation_price) }}</template>
        </el-table-column>
        <el-table-column label="output" align="right" min-width="90">
          <template #default="{ row }">{{ fmtRate(row.output_price) }}</template>
        </el-table-column>
        <el-table-column prop="currency" label="币种" width="70" align="center" />
        <el-table-column prop="note" label="备注" min-width="140" show-overflow-tooltip />
        <el-table-column label="更新时间" width="150" align="right">
          <template #default="{ row }">{{ fmtTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-if="row.model !== '*'"
              size="small"
              text
              type="danger"
              @click="remove(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing?.model || '新增价格'" width="520">
      <el-form label-width="140px">
        <el-form-item label="input / 1M">
          <el-input-number v-model="form.input_price" :min="0" :step="0.05" :precision="4" style="width: 100%" />
        </el-form-item>
        <el-form-item label="cache_read / 1M">
          <el-input-number v-model="form.cache_read_price" :min="0" :step="0.01" :precision="4" style="width: 100%" />
        </el-form-item>
        <el-form-item label="cache_creation / 1M">
          <el-input-number v-model="form.cache_creation_price" :min="0" :step="0.05" :precision="4" style="width: 100%" />
        </el-form-item>
        <el-form-item label="output / 1M">
          <el-input-number v-model="form.output_price" :min="0" :step="0.05" :precision="4" style="width: 100%" />
        </el-form-item>
        <el-form-item label="币种">
          <el-select v-model="form.currency" style="width: 100%">
            <el-option value="USD" label="USD" />
            <el-option value="CNY" label="CNY" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api'
import type { PriceRow } from '@/types'
import { fmtTime } from '@/utils/format'

const rows = ref<PriceRow[]>([])
const allModels = ref<string[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editing = ref<PriceRow | null>(null)
const addModel = ref('')

const form = reactive({
  input_price: 0,
  cache_read_price: 0,
  cache_creation_price: 0,
  output_price: 0,
  currency: 'USD',
  note: '',
})

const unpriced = computed(() =>
  allModels.value.filter((m) => !rows.value.some((r) => r.model === m)),
)

function fmtRate(n: number): string {
  return Number.isInteger(n) ? String(n) : String(n)
}

async function load() {
  loading.value = true
  try {
    const [p, m] = await Promise.all([api.prices(), api.models()])
    rows.value = p
    allModels.value = m
  } finally {
    loading.value = false
  }
}

function openEdit(row: PriceRow) {
  editing.value = row
  Object.assign(form, {
    input_price: row.input_price,
    cache_read_price: row.cache_read_price,
    cache_creation_price: row.cache_creation_price,
    output_price: row.output_price,
    currency: row.currency,
    note: row.note ?? '',
  })
  dialogVisible.value = true
}

function openAdd() {
  editing.value = null
  Object.assign(form, {
    input_price: 0,
    cache_read_price: 0,
    cache_creation_price: 0,
    output_price: 0,
    currency: 'USD',
    note: '',
  })
  dialogVisible.value = true
}

async function save() {
  const model = editing.value?.model ?? addModel.value
  if (!model) return
  saving.value = true
  try {
    await api.upsertPrice(model, { ...form })
    ElMessage.success('已保存')
    dialogVisible.value = false
    addModel.value = ''
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(row: PriceRow) {
  await ElMessageBox.confirm(`删除模型 ${row.model} 的价格配置？`, '确认', { type: 'warning' })
  await api.deletePrice(row.model)
  ElMessage.success('已删除')
  await load()
}

async function applyDefault() {
  await api.applyDefault()
  ElMessage.success('已按 * 兜底价补齐未定价模型')
  await load()
}

onMounted(load)
</script>

<style scoped>
.prices-page { display: flex; flex-direction: column; gap: 14px; }
.tip { margin-bottom: 2px; }
.head { display: flex; align-items: center; justify-content: space-between; }
.actions { display: flex; gap: 8px; }
.fallback { color: #1d6fe0; }
.fallback-tag {
  font-size: 11px; background: #1d6fe0; color: #fff;
  border-radius: 8px; padding: 0 6px; margin-left: 6px;
}
</style>
