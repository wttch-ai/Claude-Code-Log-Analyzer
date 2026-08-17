// 图表配色：颜色 = 实体，跨视图/过滤稳定。token 档位色固定。

export const PALETTE = [
  '#2a78d6',
  '#eb6834',
  '#1baf7a',
  '#eda100',
  '#e87ba4',
  '#008300',
  '#4a3aa7',
  '#e34948',
]

const colorMap = new Map<string, string>()
let next = 0

export function colorFor(name: string): string {
  if (!colorMap.has(name)) {
    colorMap.set(name, PALETTE[next % PALETTE.length])
    next++
  }
  return colorMap.get(name)!
}

// token 四档堆叠色（TokenBar 用）
export const TOKEN_TIER_COLORS: Record<string, string> = {
  input: '#2a78d6',
  cache_read: '#1baf7a',
  cache_creation: '#eb6834',
  output: '#e87ba4',
}

export const TOKEN_TIER_LABELS: Record<string, string> = {
  input: 'input',
  cache_read: 'cache_read',
  cache_creation: 'cache_creation',
  output: 'output',
}

export const TEXT_MUTED = '#898781'
export const GRID_HAIRLINE = '#e1e0d9'

// 高 token 告警阈值
export const ALERT_HIGH = 200_000
export const ALERT_CRITICAL = 1_000_000
