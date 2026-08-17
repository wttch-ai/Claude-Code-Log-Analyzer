<template>
  <div class="cm">
    <span class="cm-icon">🗜</span>
    <span>上下文压缩</span>
    <span class="cm-nums">{{ fmtCompact(info.pre_tokens) }} → {{ fmtCompact(info.post_tokens) }}</span>
    <span class="cm-drop">丢弃 -{{ fmtCompact(info.dropped_tokens) }} tokens</span>
    <span v-if="info.trigger" class="cm-meta">· {{ info.trigger }}</span>
    <span v-if="info.duration_ms" class="cm-meta">· {{ (info.duration_ms / 1000).toFixed(1) }}s</span>
  </div>
</template>

<script setup lang="ts">
import type { CompactionInfo } from '@/types'
import { fmtCompact } from '@/utils/format'

defineProps<{ info: CompactionInfo }>()
</script>

<style scoped>
.cm {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #8a6d1a;
  background: #fdf6e3;
  border: 1px dashed #e6c76f;
  border-radius: 6px;
  padding: 6px 12px;
  margin: 2px 0;
}
.cm-icon { font-size: 13px; }
.cm-nums { font-weight: 600; font-variant-numeric: tabular-nums; }
.cm-drop { color: #c0392b; font-weight: 600; }
.cm-meta { color: #a0802a; }
</style>
