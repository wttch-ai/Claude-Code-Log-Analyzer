// 展示层三分类：输入 / 输出 / Cache。cache = cache_read + cache_creation。
// 底层数据保留四档，此处合并供各处 token 展示统一口径。

import { TOKEN_TIER_COLORS } from './charts'
import type { TokenCounts } from '@/types'

export type TierKey = 'input' | 'output' | 'cache'

export const TIER3_KEYS: TierKey[] = ['input', 'output', 'cache']

export const TIER3_COLORS: Record<TierKey, string> = {
  input: TOKEN_TIER_COLORS.input,
  output: TOKEN_TIER_COLORS.output,
  cache: TOKEN_TIER_COLORS.cache_read,
}

export const TIER3_LABELS: Record<TierKey, string> = {
  input: '输入',
  output: '输出',
  cache: 'Cache',
}

// 四档 tokens → 三分类
export function toTiers(t: TokenCounts): Record<TierKey, number> {
  return {
    input: t.input,
    output: t.output,
    cache: t.cache_read + t.cache_creation,
  }
}

// 四档价格 breakdown → 三分类；未定价返回 null
export function tiersFromBreakdown(
  b: { input: number; cache_read: number; cache_creation: number; output: number } | null | undefined,
): Record<TierKey, number> | null {
  if (!b) return null
  return {
    input: b.input,
    output: b.output,
    cache: b.cache_read + b.cache_creation,
  }
}
