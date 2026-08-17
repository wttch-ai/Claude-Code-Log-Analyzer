// 数值 / 价格 / 时间格式化

export function fmtCompact(n: number): string {
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e4) return (n / 1e3).toFixed(1) + 'k'
  return String(Math.round(n))
}

export function fmtTokens(n: number | undefined): string {
  if (n === undefined || n === null) return '—'
  return Math.round(n).toLocaleString('en-US')
}

export function fmtPrice(n: number | null | undefined): string {
  if (n === undefined || n === null || isNaN(n)) return '—'
  if (n >= 1) return '$' + n.toFixed(2)
  if (n >= 0.01) return '$' + n.toFixed(4)
  if (n > 0) return '$' + n.toFixed(6)
  return '$0.00'
}

export function fmtAxisPrice(n: number): string {
  if (n >= 1) return '$' + n.toFixed(1)
  if (n >= 0.001) return '$' + n.toFixed(3)
  return '$' + n.toFixed(5)
}

export function fmtDuration(s: number | null | undefined): string {
  if (s === null || s === undefined) return '—'
  if (s < 60) return Math.round(s) + 's'
  if (s < 3600) return (s / 60).toFixed(1) + 'm'
  if (s < 86400) return (s / 3600).toFixed(2) + 'h'
  return (s / 86400).toFixed(1) + 'd'
}

export function fmtTime(ts: string | null | undefined): string {
  if (!ts) return ''
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ts
  return d.toLocaleString('zh-CN', { hour12: false })
}

export function fmtDay(day: string): string {
  return day
}

export function pct(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  return (n * 100).toFixed(1) + '%'
}
