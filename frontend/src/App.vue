<template>
  <el-container class="app-shell">
    <el-header class="app-header" height="56px">
      <AppHeader />
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import AppHeader from '@/components/Layout/AppHeader.vue'
import { useScanStore } from '@/stores/scan'

const scan = useScanStore()
onMounted(() => scan.startPolling())
onUnmounted(() => scan.stopPolling())
</script>

<style>
html, body, #app { height: 100%; margin: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
  background: #f5f6f8;
}
.app-shell { height: 100%; }
.app-header {
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  padding: 0 20px;
}
.app-main { padding: 20px; overflow: auto; }
</style>
