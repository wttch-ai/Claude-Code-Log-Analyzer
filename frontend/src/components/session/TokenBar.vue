<template>
  <el-tooltip placement="top" :disabled="!tokens" :show-after="200">
    <template #content>
      <div class="tbar-tip">
        <div v-for="t of TIERS" :key="t" class="tbar-tip-line">
          <span class="swatch" :style="{ background: TOKEN_TIER_COLORS[t] }" />
          <span class="tier-name">{{ TOKEN_TIER_LABELS[t] }}</span>
          <b>{{ fmtCompact(tokens[t]) }}</b>
        </div>
        <div class="tbar-tip-line total">
          <span>合计</span>
          <b>{{ fmtCompact(tokens.total) }}</b>
        </div>
      </div>
    </template>
    <div class="tbar" :style="{ height: barHeight + 'px' }">
      <div
        v-for="t of TIERS"
        v-show="tokens[t] > 0"
        :key="t"
        class="tbar-seg"
        :style="{ width: pct(tokens[t] / tokens.total) + '%', background: TOKEN_TIER_COLORS[t] }"
      />
    </div>
  </el-tooltip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TokenCounts } from '@/types'
import { TOKEN_TIER_COLORS, TOKEN_TIER_LABELS } from '@/utils/charts'
import { fmtCompact } from '@/utils/format'

const props = withDefaults(
  defineProps<{ tokens?: TokenCounts }>(),
  { tokens: () => ({ input: 0, cache_read: 0, cache_creation: 0, output: 0, total: 0 }) },
)

const TIERS = ['input', 'cache_read', 'cache_creation', 'output'] as const

const barHeight = computed(() => {
  const total = props.tokens?.total ?? 0
  if (total <= 0) return 8
  // 对数映射：1k→8px，1M→~30px，100M→~40px
  const v = Math.log10(1 + total)
  return Math.round(8 + 34 * (v / 9))
})

function pct(x: number): number {
  if (!isFinite(x) || x <= 0) return 0
  return x * 100
}
</script>

<style scoped>
.tbar {
  width: 44px;
  min-height: 8px;
  border-radius: 3px;
  overflow: hidden;
  display: flex;
  flex-direction: row;
  background: #eceff3;
  cursor: pointer;
}
.tbar-seg { height: 100%; }
.tbar-tip { font-size: 12px; line-height: 1.7; min-width: 150px; }
.tbar-tip-line { display: flex; align-items: center; gap: 6px; justify-content: space-between; }
.tbar-tip-line b { font-variant-numeric: tabular-nums; }
.tbar-tip-line.total { margin-top: 4px; padding-top: 4px; border-top: 1px solid #ddd; }
.swatch { width: 10px; height: 10px; border-radius: 2px; }
.tier-name { flex: 1; }
</style>
