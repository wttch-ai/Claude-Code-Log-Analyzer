<template>
  <el-drawer v-model="visible" :size="620" :title="`消息详情`">
    <div v-loading="loading" class="md">
      <template v-if="detail">
        <div class="md-meta">
          <span class="md-time">{{ fmtTime(detail.timestamp) }}</span>
          <span v-if="detail.model" class="tag model">{{ detail.model }}</span>
          <span v-if="detail.effort" class="tag">{{ detail.effort }}</span>
          <span v-if="detail.stop_reason" class="tag">stop: {{ detail.stop_reason }}</span>
        </div>

        <div class="md-tokens">
          <div class="md-token-item"><span>input</span><b>{{ fmtTokens(detail.tokens!.input) }}</b></div>
          <div class="md-token-item"><span>cache_read</span><b>{{ fmtTokens(detail.tokens!.cache_read) }}</b></div>
          <div class="md-token-item"><span>cache_creation</span><b>{{ fmtTokens(detail.tokens!.cache_creation) }}</b></div>
          <div class="md-token-item"><span>output</span><b>{{ fmtTokens(detail.tokens!.output) }}</b></div>
          <div class="md-token-item" v-if="detail.tokens!.thinking"><span>thinking</span><b>{{ fmtTokens(detail.tokens!.thinking) }}</b></div>
          <div class="md-token-item total"><span>合计</span><b>{{ fmtTokens(detail.tokens!.total) }}</b></div>
          <div class="md-token-item price"><span>成本</span><b>{{ fmtPrice(detail.price?.total) }}</b></div>
        </div>

        <el-tabs v-model="tab" class="md-tabs">
          <el-tab-pane label="回复" name="text">
            <pre v-if="textContent" class="md-pre">{{ textContent }}</pre>
            <el-empty v-else description="无文本回复" :image-size="60" />
          </el-tab-pane>

          <el-tab-pane label="思考" name="think">
            <pre v-if="thinkingContent" class="md-pre think">{{ thinkingContent }}</pre>
            <el-empty v-else description="无思考内容" :image-size="60" />
          </el-tab-pane>

          <el-tab-pane v-if="detail.tool_calls?.length" label="工具" name="tools">
            <div v-for="tc in detail.tool_calls" :key="tc.tool_use_id" class="tool-card">
              <div class="tool-head">
                <span class="chip" :class="{ agent: tc.name === 'Agent' }">
                  {{ tc.skill ? '📘 ' + tc.skill : '🔧 ' + tc.name }}
                </span>
                <span v-if="tc.result_error" class="err-tag">error</span>
              </div>
              <div class="io-block">
                <div class="io-label">输入</div>
                <pre class="md-pre">{{ fmtJson(tc.input) }}</pre>
                <div class="io-label">输出</div>
                <pre v-if="tc.result_file_content?.content" class="md-pre result">{{ tc.result_file_content.content }}<span v-if="tc.result_file_content.truncated" class="trunc">…（已截断）</span></pre>
                <pre v-else class="md-pre result">{{ fmtJson(tc.result) }}</pre>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="用量" name="usage">
            <table class="usage-table">
              <tbody>
                <tr v-for="row of usageRows" :key="row.label">
                  <td>{{ row.label }}</td>
                  <td>{{ fmtTokens(row.tokens) }}</td>
                  <td class="price-cell">{{ fmtPrice(row.price) }}</td>
                </tr>
              </tbody>
            </table>
          </el-tab-pane>

          <el-tab-pane v-if="detail.subagents?.length" label="子会话" name="subs">
            <div v-for="sa in detail.subagents" :key="sa.agent_id" class="sub-item">
              <span class="chip">{{ sa.agent_type || 'agent' }}</span>
              <span>{{ sa.description }}</span>
              <span class="sub-depth">depth {{ sa.spawn_depth }}</span>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '@/api'
import type { MessageDetail, MessageDetailToolCall } from '@/types'
import { fmtPrice, fmtTime, fmtTokens } from '@/utils/format'

const visible = defineModel<boolean>({ required: true })
const props = defineProps<{ rowUuid: string | null }>()

const detail = ref<MessageDetail>()
const loading = ref(false)
const tab = ref('text')

const textContent = computed(() => {
  const blocks = detail.value?.content ?? []
  return blocks
    .filter((b) => b && typeof b === 'object' && (b as any).type === 'text')
    .map((b) => (b as any).text ?? '')
    .join('\n')
})
const thinkingContent = computed(() => {
  const blocks = detail.value?.content ?? []
  return blocks
    .filter((b) => b && typeof b === 'object' && (b as any).type === 'thinking')
    .map((b) => (b as any).thinking ?? '')
    .join('\n')
})

const usageRows = computed(() => {
  const t = detail.value?.tokens
  if (!t) return []
  const p = detail.value?.price as any
  const bk = (p?.breakdown ?? {}) as Record<string, number>
  return [
    { label: 'input', tokens: t.input, price: bk.input ?? null },
    { label: 'cache_read', tokens: t.cache_read, price: bk.cache_read ?? null },
    { label: 'cache_creation', tokens: t.cache_creation, price: bk.cache_creation ?? null },
    { label: 'output', tokens: t.output, price: bk.output ?? null },
    { label: 'thinking', tokens: t.thinking ?? 0, price: null },
  ]
})

function fmtJson(v: unknown): string {
  if (v === null || v === undefined) return ''
  if (typeof v === 'string') return v
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

watch(
  () => props.rowUuid,
  async (uuid) => {
    if (!uuid) return
    loading.value = true
    detail.value = undefined
    tab.value = 'text'
    try {
      detail.value = await api.messageDetail(uuid)
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.md { display: flex; flex-direction: column; gap: 12px; }
.md-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.md-time { font-size: 12px; color: #999; }
.tag {
  font-size: 11px; padding: 1px 8px; border-radius: 10px;
  background: #eef2f7; color: #444;
}
.tag.model { background: #e8f1fe; color: #1d6fe0; }

.md-tokens {
  display: flex; flex-wrap: wrap; gap: 8px;
  background: #fafbfc; border: 1px solid #eee; border-radius: 8px; padding: 10px 12px;
}
.md-token-item {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  min-width: 78px; padding: 4px 8px; border-radius: 6px; background: #fff;
  border: 1px solid #eceff3;
}
.md-token-item span { font-size: 11px; color: #888; }
.md-token-item b { font-size: 13px; font-variant-numeric: tabular-nums; }
.md-token-item.total { border-color: #1d6fe0; }
.md-token-item.total b { color: #1d6fe0; }
.md-token-item.price { border-color: #e34948; }
.md-token-item.price b { color: #e34948; }

.md-tabs { margin-top: 2px; }
.md-pre {
  font-family: ui-monospace, "SF Mono", Consolas, monospace;
  font-size: 12px; line-height: 1.7;
  white-space: pre-wrap; word-break: break-word;
  background: #fafbfc; border-radius: 8px; padding: 12px;
  max-height: 55vh; overflow: auto;
  margin: 0;
}
.md-pre.think { background: #f7f4fc; color: #4a308c; }
.md-pre.result { background: #f0faf4; }

.tool-card { border: 1px solid #eef0f3; border-radius: 8px; margin-bottom: 10px; overflow: hidden; }
.tool-head {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; background: #f8f9fb; border-bottom: 1px solid #eef0f3;
}
.chip {
  font-size: 12px; padding: 2px 10px; border-radius: 12px;
  background: #f2f4f7; border: 1px solid #e3e6ea; color: #3a3f45;
}
.chip.agent { background: #e8f1fe; border-color: #b6d0f6; color: #1d6fe0; font-weight: 600; }
.err-tag { font-size: 11px; color: #c0392b; font-weight: 700; }
.io-block { padding: 10px 12px; }
.io-label { font-size: 11px; color: #999; margin: 8px 0 4px; }
.io-label:first-child { margin-top: 0; }
.trunc { color: #999; font-weight: 700; }

.usage-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.usage-table td { padding: 7px 10px; border-bottom: 1px solid #f0f0f0; }
.usage-table td:first-child { color: #666; }
.price-cell { color: #e34948; font-variant-numeric: tabular-nums; }

.sub-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px;
}
.sub-depth { margin-left: auto; color: #999; font-size: 12px; }
</style>
