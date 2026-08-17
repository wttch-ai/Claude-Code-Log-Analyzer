// 与后端 API 响应对应的类型定义

export interface TokenCounts {
  input: number
  cache_read: number
  cache_creation: number
  output: number
  total: number
  thinking?: number
}

export interface PriceInfo {
  total: number | null
  priced: boolean
  currency?: string | null
}

export interface SeriesCell {
  tokens: number
  price: number
}

export interface AggSeries {
  name: string
  values: SeriesCell[]
  total_tokens: number
  total_price: number
}

export interface AggregateResult {
  dim: string
  granularity: string
  dates: string[]
  series: AggSeries[]
  total_tokens: number
  total_price: number
}

export interface OverviewData {
  totals: { tokens: TokenCounts; price: PriceInfo }
  today: { tokens: TokenCounts; price: PriceInfo }
  week: { tokens: TokenCounts; price: PriceInfo }
  projects_count: number
  main_sessions: number
  subagent_sessions: number
  messages: number
  cache_read_ratio: number
  models: Array<{
    model: string
    tokens: TokenCounts
    price: PriceInfo
    cost_share: number | null
  }>
  compactions: { count: number; dropped_tokens: number }
}

export interface ProjectItem {
  id: number
  slug: string
  name: string
  cwd: string | null
  last_seen_at: string | null
  sessions: number
  messages: number
  subagents: number
  tokens: TokenCounts
  price: PriceInfo
}

export interface ProjectList {
  total: number
  items: ProjectItem[]
}

export interface ProjectDetail {
  id: number
  slug: string
  name: string | null
  cwd: string | null
  first_seen_at: string | null
  last_seen_at: string | null
}

export interface SessionItem {
  session_id: string
  title: string | null
  agent_name: string | null
  version: string | null
  started_at: string | null
  ended_at: string | null
  duration_s: number | null
  message_count: number
  subagent_count: number
  tokens: TokenCounts
  price: PriceInfo
}

export interface ToolUseInfo {
  tool_use_id: string
  name: string
  skill: string | null
  input_preview: { text: string; truncated: boolean } | null
  result_preview: { text: string; truncated: boolean } | null
  result_error: boolean | null
  result_file: string | null
  subagent?: SubagentNode
}

export interface CompactionInfo {
  trigger: string | null
  pre_tokens: number
  post_tokens: number
  dropped_tokens: number
  duration_ms: number
  timestamp?: string | null
}

export interface TimelineNode {
  kind: 'row'
  type: string
  row_uuid: string
  timestamp: string | null
  is_user: boolean
  model?: string
  effort?: string
  stop_reason?: string
  tokens?: TokenCounts
  price?: PriceInfo
  preview?: { text: string; truncated: boolean }
  thinking_preview?: { text: string; truncated: boolean }
  tool_uses?: ToolUseInfo[]
  content?: string | null
  subtype?: string
  compaction?: CompactionInfo | null
  is_compact_summary?: boolean
}

export interface SubagentNode {
  kind: 'subagent'
  agent_id: string
  agent_type: string | null
  description: string | null
  spawn_depth: number
  tokens: TokenCounts
  price: PriceInfo
  message_count: number
  truncated?: boolean
  nodes: TimelineNode[]
}

export interface TimelineData {
  session_id: string
  project: { id: number | null; name: string | null }
  title: string | null
  agent_name: string | null
  version: string | null
  started_at: string | null
  ended_at: string | null
  summary: {
    tokens: TokenCounts
    price: PriceInfo
    message_count: number
    subagent_count: number
    compactions: Array<CompactionInfo & { timestamp: string | null }>
  }
  nodes: TimelineNode[]
}

export interface PriceRow {
  model: string
  input_price: number
  cache_read_price: number
  cache_creation_price: number
  output_price: number
  currency: string
  note: string | null
  updated_at: string | null
}

export interface ScanStatus {
  running: boolean
  has_run: boolean
  id?: number
  mode?: string
  status?: string
  error?: string | null
  started_at?: string | null
  finished_at?: string | null
  projects_found?: number
  main_files?: number
  subagent_files?: number
  entries_found?: number
  new_entries?: number
  unchanged_files?: number
  updated_files?: number
}

export interface MessageDetailToolCall {
  tool_use_id: string
  name: string
  skill: string | null
  input: Record<string, unknown>
  result: unknown
  result_error: boolean | null
  result_file: string | null
  result_file_content?: {
    content?: string
    truncated?: boolean
    error?: string
    path?: string
  }
}

export interface MessageDetail {
  row_uuid: string
  type: string
  timestamp: string | null
  raw: Record<string, unknown>
  message_id?: string | null
  model?: string | null
  effort?: string | null
  stop_reason?: string | null
  tokens?: TokenCounts
  price?: PriceInfo
  content?: unknown[]
  tool_calls?: MessageDetailToolCall[]
  subagents?: Array<{
    agent_id: string
    agent_type: string | null
    description: string | null
    spawn_depth: number
  }>
}
