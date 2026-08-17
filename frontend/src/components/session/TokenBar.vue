<template>
  <el-tooltip placement="top" :disabled="!tokens" :show-after="200">
    <template #content>
      <div class="tbar-tip">
        <div v-for="t of TIERS3" :key="t" class="tbar-tip-line">
          <span class="swatch" :style="{ background: TIER3_COLORS[t] }" />
          <span class="tier-name">{{ TIER3_LABELS[t] }}</span>
          <b>{{ fmtCompact(three(t)) }}</b>
        </div>
        <div v-if="tokens.cache_read + tokens.cache_creation > 0" class="tbar-tip-sub">
          <span class="tier-name">　└ 读 {{ fmtCompact(tokens.cache_read) }} · 写 {{ fmtCompact(tokens.cache_creation) }}</span>
        </div>
        <div class="tbar-tip-line total">
          <span>合计</span>
          <b>{{ fmtCompact(tokens.total) }}</b>
        </div>
      </div>
    </template>
    <div class="tbar" :style="{ height: barHeight + 'px' }">
      <div
        v-for="t of TIERS3"
        v-show="three(t) > 0"
        :key="t"
        class="tbar-seg"
        :style="{ width: pct(three(t) / tokens.total) + '%', background: TIER3_COLORS[t] }"
      />
    </div>
  </el-tooltip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TokenCounts } from '@/types'
import { fmtCompact } from '@/utils/format'
import { TIER3_COLORS, TIER3_KEYS, TIER3_LABELS, type TierKey } from '@/utils/tiers'

const props = withDefaults(
  defineProps<{ tokens?: TokenCounts }>(),
  { tokens: () => ({ input: 0, cache_read: 0, cache_creation: 0, output: 0, total: 0 }) },
)

const TIERS3 = TIER3_KEYS

// 三分类取值：cache = cache_read + cache_creation
function three(t: TierKey): number {
  const tk = props.tokens
  if (t === 'cache') return tk.cache_read + tk.cache_creation
  return tk[t]
}

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
.tbar-tip-sub { display: flex; font-size: 11px; color: #888; padding-left: 4px; }
.tbar-tip-line.total { margin-top: 4px; padding-top: 4px; border-top: 1px solid #ddd; }
.swatch { width: 10px; height: 10px; border-radius: 2px; }
.tier-name { flex: 1; }
</style>
