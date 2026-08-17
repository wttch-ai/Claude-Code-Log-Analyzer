<template>
  <div class="mrow" :style="{ paddingLeft: dep * 14 + 'px' }" :class="alertCls">
    <template v-if="node.type === 'assistant'">
      <div class="row-head">
        <TokenBar :tokens="node.tokens" />
        <span class="row-time">{{ fmtTime(node.timestamp) }}</span>
        <span v-if="node.model" class="tag model">{{ node.model }}</span>
        <span v-if="node.effort" class="tag effort">{{ node.effort }}</span>
        <span v-if="node.stop_reason === 'max_tokens'" class="tag max">max_tokens</span>
        <span class="row-total">
          {{ display.isPrice ? fmtPrice(node.price?.total) : fmtTokens(node.tokens?.total ?? 0) }}
        </span>
        <span class="spacer" />
        <el-button size="small" text type="primary" @click="emit('show-detail', node.row_uuid)">
          详情
        </el-button>
      </div>
      <div v-if="node.tool_uses?.length" class="tools">
        <span
          v-for="tu in node.tool_uses"
          :key="tu.tool_use_id"
          class="chip"
          :class="tu.name === 'Agent' ? 'agent' : ''"
        >
          {{ tu.skill ? '📘 ' + tu.skill : '🔧 ' + tu.name }}
        </span>
      </div>
      <div v-if="node.preview?.text" class="preview">
        {{ node.preview.text }}<span v-if="node.preview.truncated" class="trunc">…</span>
      </div>
      <div v-if="node.thinking_preview?.text" class="think-preview">
        <span class="think-label">思考</span> {{ node.thinking_preview.text
        }}<span v-if="node.thinking_preview.truncated" class="trunc">…</span>
      </div>
      <div
        v-for="tu in node.tool_uses?.filter((t) => t.subagent)"
        :key="tu.subagent!.agent_id"
        class="sub-block"
      >
        <div class="sub-head" @click="toggleSub(tu)">
          <span class="caret" :class="{ open: isSubOpen(tu) }">▸</span>
          <span class="sub-badge">subagent</span>
          <span class="sub-type">{{ tu.subagent!.agent_type || 'agent' }}</span>
          <span v-if="tu.subagent!.description" class="sub-desc">{{ tu.subagent!.description }}</span>
          <span class="sub-tokens">
            {{ display.isPrice ? fmtPrice(tu.subagent!.price.total) : fmtTokens(tu.subagent!.tokens.total) }}
            · {{ tu.subagent!.message_count }} 条
          </span>
        </div>
        <div v-if="isSubOpen(tu)" class="sub-inner">
          <template v-for="n in tu.subagent!.nodes" :key="n.row_uuid">
            <CompactionMarker v-if="n.type === 'system' && n.compaction" :info="n.compaction" />
            <MessageRow v-else :node="n" :depth="dep + 1" @show-detail="emit('show-detail', $event)" />
          </template>
        </div>
      </div>
    </template>

    <template v-else-if="node.type === 'user'">
      <div class="user-row">
        <span class="user-icon">👤</span>
        <div class="user-body">
          <span v-if="node.is_compact_summary" class="tag summary">compact summary</span>
          <div class="preview">{{ node.preview?.text || '…' }}</div>
        </div>
      </div>
    </template>

    <template v-else-if="node.type === 'system'">
      <div class="system-row"><span class="sys-icon">⚙</span>{{ node.content || node.subtype }}</div>
    </template>

    <template v-else>
      <div class="other-row">{{ node.content }}</div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TimelineNode, ToolUseInfo } from '@/types'
import { ALERT_CRITICAL, ALERT_HIGH } from '@/utils/charts'
import { fmtPrice, fmtTime, fmtTokens } from '@/utils/format'
import { useDisplayStore } from '@/stores/display'
import CompactionMarker from './CompactionMarker.vue'
import TokenBar from './TokenBar.vue'

const props = defineProps<{
  node: TimelineNode
  depth?: number
}>()
const emit = defineEmits<{ (e: 'show-detail', rowUuid: string): void }>()

const display = useDisplayStore()
const dep = computed(() => props.depth ?? 0)
const openSubs = ref(new Set<string>())

function isSubOpen(tu: ToolUseInfo): boolean {
  return openSubs.value.has(tu.subagent!.agent_id)
}
function toggleSub(tu: ToolUseInfo) {
  const id = tu.subagent!.agent_id
  const s = new Set(openSubs.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  openSubs.value = s
}

const alertCls = computed(() => {
  const total = props.node.tokens?.total ?? 0
  if (total >= ALERT_CRITICAL) return 'alert-critical'
  if (total >= ALERT_HIGH) return 'alert-high'
  return ''
})
</script>

<style scoped>
.mrow { border-bottom: 1px solid #f0f0f0; padding-top: 8px; padding-bottom: 8px; }
.alert-high { background: #fff8ec; box-shadow: inset 3px 0 0 #eda100; }
.alert-critical { background: #fdeeee; box-shadow: inset 3px 0 0 #e34948; }

.row-head { display: flex; align-items: center; gap: 10px; }
.row-time { font-size: 12px; color: #999; min-width: 78px; }
.row-total { font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; color: #333; }
.spacer { flex: 1; }

.tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  background: #eef2f7;
  color: #444;
  white-space: nowrap;
}
.tag.model { background: #e8f1fe; color: #1d6fe0; }
.tag.effort { background: #efe8fb; color: #6b3fc0; }
.tag.max { background: #fdecec; color: #c0392b; }
.tag.summary { background: #fdf6e3; color: #8a6d1a; }

.tools { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.chip {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 12px;
  background: #f2f4f7;
  color: #3a3f45;
  border: 1px solid #e3e6ea;
}
.chip.agent {
  background: #e8f1fe;
  border-color: #b6d0f6;
  color: #1d6fe0;
  font-weight: 600;
}

.preview {
  margin-top: 6px;
  font-size: 13px;
  color: #444;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.think-preview {
  margin-top: 6px;
  font-size: 12px;
  color: #6b3fc0;
  background: #f7f4fc;
  border-radius: 6px;
  padding: 6px 10px;
  white-space: pre-wrap;
  word-break: break-word;
}
.think-label { font-weight: 700; }
.trunc { color: #999; font-weight: 700; }

.sub-block {
  margin-top: 8px;
  border: 1px solid #dbe7f8;
  border-radius: 8px;
  background: #f6faff;
  overflow: hidden;
}
.sub-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
}
.sub-head:hover { background: #eef4fd; }
.caret { transition: transform 0.15s; display: inline-block; color: #1d6fe0; }
.caret.open { transform: rotate(90deg); }
.sub-badge {
  font-size: 11px;
  background: #1d6fe0;
  color: #fff;
  border-radius: 10px;
  padding: 1px 8px;
}
.sub-type { font-weight: 600; color: #1d6fe0; }
.sub-desc { color: #666; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 40%; }
.sub-tokens { margin-left: auto; font-weight: 700; color: #333; font-variant-numeric: tabular-nums; }
.sub-inner { padding: 4px 12px 8px; }

.user-row { display: flex; gap: 10px; align-items: flex-start; }
.user-icon { font-size: 16px; margin-top: 2px; }
.user-body { flex: 1; }

.system-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #777;
  background: #fafbfc;
  border-radius: 6px;
  padding: 5px 12px;
}
.sys-icon { font-size: 12px; }
.other-row { font-size: 12px; color: #888; }
</style>
