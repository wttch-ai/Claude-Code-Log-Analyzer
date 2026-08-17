<template>
  <div class="stat-card">
    <div class="label">{{ label }}</div>
    <div class="value">{{ text }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDisplayStore } from '@/stores/display'
import { fmtCompact, fmtPrice } from '@/utils/format'

const props = defineProps<{
  label: string
  tokens: number
  price?: number | null
  sub?: string
}>()

const display = useDisplayStore()
const text = computed(() => {
  const v = display.numVal(props.tokens, props.price)
  if (v <= 0 && props.tokens === 0) return '—'
  return display.isPrice ? fmtPrice(v) : fmtCompact(v)
})
</script>

<style scoped>
.stat-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 10px;
  padding: 16px 20px;
  min-width: 0;
}
.label { font-size: 13px; color: #888; }
.value { font-size: 26px; font-weight: 700; margin-top: 6px; font-variant-numeric: tabular-nums; }
.sub { font-size: 12px; color: #999; margin-top: 4px; }
</style>
