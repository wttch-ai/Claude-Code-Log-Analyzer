import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

// 全局唯一显示模式：tokens | price。切换不重取数据（后端双字段返回）。
export const useDisplayStore = defineStore('display', () => {
  const mode = ref<'tokens' | 'price'>('tokens')

  function toggle() {
    mode.value = mode.value === 'tokens' ? 'price' : 'tokens'
  }

  // aggregate 系列单元格：{tokens, price}
  function cellVal(cell: { tokens: number; price: number }) {
    return mode.value === 'price' ? cell.price : cell.tokens
  }

  // 一般场景：给定 tokens 总数与价格，按模式取值；未定价回退 tokens
  function numVal(tokens: number, price: number | null | undefined): number {
    if (mode.value === 'price' && price !== null && price !== undefined) return price
    return tokens
  }

  const isPrice = computed(() => mode.value === 'price')

  return { mode, isPrice, toggle, cellVal, numVal }
})
