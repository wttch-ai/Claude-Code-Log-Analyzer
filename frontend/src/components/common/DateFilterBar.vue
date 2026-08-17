<template>
  <div class="filter-bar">
    <el-radio-group :model-value="preset" @update:model-value="onPreset">
      <el-radio-button value="today">今天</el-radio-button>
      <el-radio-button value="7">近7天</el-radio-button>
      <el-radio-button value="30">近30天</el-radio-button>
      <el-radio-button value="90">近90天</el-radio-button>
      <el-radio-button value="all">全部</el-radio-button>
      <el-radio-button value="custom">自定义</el-radio-button>
    </el-radio-group>
    <el-date-picker
      v-if="preset === 'custom'"
      v-model="customRange"
      type="daterange"
      value-format="YYYY-MM-DD"
      range-separator="至"
      start-placeholder="开始"
      end-placeholder="结束"
      @change="emitRange()"
    />
    <el-select
      v-if="dims && dims.length"
      :model-value="dim"
      @update:model-value="(v: string) => emit('update:dim', v)"
      class="dim-select"
    >
      <el-option v-for="d in dims" :key="d.value" :label="d.label" :value="d.value" />
    </el-select>
    <span v-if="rangeText" class="range-text">{{ rangeText }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  dims?: { label: string; value: string }[]
  dim?: string
  start?: string
  end?: string
}>()
const emit = defineEmits<{
  (e: 'update:dim', v: string): void
  (e: 'update:range', start: string | undefined, end: string | undefined): void
}>()

const preset = ref('30')
const customRange = ref<[string, string] | null>(null)

function todayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function onPreset(v: string) {
  preset.value = v
  if (v === 'custom') {
    emit('update:range', customRange.value?.[0], customRange.value?.[1])
  } else if (v === 'all') {
    emit('update:range', undefined, undefined)
  } else if (v === 'today') {
    emit('update:range', todayStr(), todayStr())
  } else {
    const n = parseInt(v, 10)
    emit('update:range', daysAgo(n - 1), todayStr())
  }
}

function emitRange() {
  if (preset.value !== 'custom') return
  emit('update:range', customRange.value?.[0], customRange.value?.[1])
}

const rangeText = computed(() => {
  if (!props.start) return '全部时间'
  if (props.start === props.end) return props.start
  return `${props.start} ~ ${props.end}`
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 4px 0;
}
.dim-select { width: 130px; }
.range-text { font-size: 12px; color: #999; }
</style>
