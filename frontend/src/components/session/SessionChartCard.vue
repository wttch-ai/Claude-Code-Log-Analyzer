<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="head">
        <span>按天消耗</span>
        <el-radio-group :model-value="dim" size="small" @update:model-value="switchDim">
          <el-radio-button value="skill">Skill 堆叠</el-radio-button>
          <el-radio-button value="tool">Tool 堆叠</el-radio-button>
        </el-radio-group>
      </div>
    </template>
    <StackedBarChart v-if="data" :data="data" height="300px" />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api'
import type { AggregateResult } from '@/types'
import StackedBarChart from '@/components/common/StackedBarChart.vue'

const props = defineProps<{ sessionId: string }>()

const dim = ref<'skill' | 'tool'>('skill')
const data = ref<AggregateResult>()
const loading = ref(false)
const cache: Partial<Record<'skill' | 'tool', AggregateResult>> = {}

async function load() {
  if (cache[dim.value]) {
    data.value = cache[dim.value]
    return
  }
  loading.value = true
  try {
    const r = await api.aggregate({ dim: dim.value, session: props.sessionId })
    cache[dim.value] = r
    data.value = r
  } finally {
    loading.value = false
  }
}

function switchDim(v: string | number | boolean | undefined) {
  dim.value = v as 'skill' | 'tool'
  load()
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; align-items: center; justify-content: space-between; }
</style>
