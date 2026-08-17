import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'
import type { ScanStatus } from '@/types'

export const useScanStore = defineStore('scan', () => {
  const status = ref<ScanStatus>({ running: false, has_run: false })
  let timer: number | null = null

  async function refresh() {
    try {
      status.value = await api.scanLatest()
    } catch {
      /* 服务未就绪时静默 */
    }
  }

  function startPolling() {
    if (timer !== null) return
    refresh()
    timer = window.setInterval(refresh, 3000)
  }

  function stopPolling() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  }

  return { status, refresh, startPolling, stopPolling }
})
