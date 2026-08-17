import { http } from './http'
import type {
  AggregateResult,
  MessageDetail,
  OverviewData,
  PriceRow,
  ProjectDetail,
  ProjectList,
  ScanStatus,
  SessionItem,
  TierSeriesResult,
  TimelineData,
} from '@/types'

export interface AggregateParams {
  dim: 'skill' | 'tool' | 'project' | 'model'
  granularity?: 'day' | 'week'
  start?: string
  end?: string
  project?: number
  session?: string
}

export const api = {
  health: () => http.get('/health').then((r) => r.data),

  scanLatest: () => http.get<ScanStatus>('/scan/latest').then((r) => r.data),
  startScan: (mode: 'incremental' | 'full') =>
    http.post(`/scan?mode=${mode}`).then((r) => r.data),

  overview: () => http.get<OverviewData>('/overview').then((r) => r.data),
  aggregate: (params: AggregateParams) =>
    http.get<AggregateResult>('/aggregate', { params }).then((r) => r.data),

  tiers: (params: { granularity?: 'day' | 'week'; start?: string; end?: string; project?: number; session?: string } = {}) =>
    http.get<TierSeriesResult>('/tiers', { params }).then((r) => r.data),

  projects: (params: { sort?: string; order?: string; offset?: number; limit?: number } = {}) =>
    http.get<ProjectList>('/projects', { params }).then((r) => r.data),
  projectDetail: (pid: number) =>
    http.get<ProjectDetail>(`/projects/${pid}`).then((r) => r.data),
  projectSessions: (pid: number) =>
    http.get<SessionItem[]>(`/projects/${pid}/sessions`).then((r) => r.data),

  timeline: (sid: string) =>
    http.get<TimelineData>(`/sessions/${sid}/timeline`).then((r) => r.data),
  messageDetail: (rowUuid: string) =>
    http.get<MessageDetail>(`/messages/${rowUuid}`).then((r) => r.data),

  prices: () => http.get<PriceRow[]>('/prices').then((r) => r.data),
  upsertPrice: (model: string, body: Partial<PriceRow>) =>
    http.put<PriceRow>(`/prices/${encodeURIComponent(model)}`, body).then((r) => r.data),
  deletePrice: (model: string) =>
    http.delete(`/prices/${encodeURIComponent(model)}`).then((r) => r.data),
  applyDefault: () => http.post('/prices/default').then((r) => r.data),
  models: () => http.get<string[]>('/models').then((r) => r.data),
}
