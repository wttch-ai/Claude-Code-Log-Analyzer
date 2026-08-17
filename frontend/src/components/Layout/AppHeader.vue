<template>
  <div class="header-inner">
    <div class="brand">
      Claude Code <span class="brand-sub">日志分析</span>
    </div>
    <nav class="nav">
      <router-link to="/" exact-active-class="active">概览</router-link>
      <router-link to="/projects" active-class="active">项目</router-link>
      <router-link to="/prices" active-class="active">价格配置</router-link>
      <router-link to="/scan" active-class="active">扫描</router-link>
    </nav>
    <div class="header-right">
      <el-switch
        :model-value="display.isPrice"
        @change="display.toggle()"
        inline-prompt
        active-text="价格"
        inactive-text="Tokens"
      />
      <router-link to="/scan" class="scan-link">
        <span class="dot" :class="scan.status.running ? 'running' : 'idle'" />
        {{ scan.status.running ? '扫描中' : scan.status.has_run ? '已扫描' : '未扫描' }}
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDisplayStore } from '@/stores/display'
import { useScanStore } from '@/stores/scan'

const display = useDisplayStore()
const scan = useScanStore()
</script>

<style scoped>
.header-inner {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 24px;
}
.brand {
  font-weight: 700;
  font-size: 15px;
  white-space: nowrap;
}
.brand-sub {
  color: #888;
  font-weight: 400;
  margin-left: 4px;
}
.nav {
  display: flex;
  gap: 6px;
  flex: 1;
}
.nav a {
  text-decoration: none;
  color: #555;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 14px;
}
.nav a:hover { background: #f0f2f5; }
.nav a.active { background: #e8f1fe; color: #1d6fe0; font-weight: 600; }
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.scan-link {
  display: flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  color: #666;
  font-size: 13px;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
}
.dot.running { background: #f5a623; animation: pulse 1s infinite; }
.dot.idle { background: #2ea44f; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}
</style>
