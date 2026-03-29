import { reactive } from 'vue'

const state = reactive({
  tasks: [],
  pollInterval: null,
})

export function useExportStore() {
  const fetchTasks = async () => {
    try {
      const { xhsApi } = await import('../api/xhs')
      const res = await xhsApi.getAllExportTasks()
      if (res.success) {
        state.tasks = res.data
      }
    } catch (e) {
      console.error('获取导出任务失败:', e)
    }
  }

  const startPolling = () => {
    if (state.pollInterval) return
    fetchTasks()
    state.pollInterval = setInterval(fetchTasks, 2000)
  }

  const stopPolling = () => {
    if (state.pollInterval) {
      clearInterval(state.pollInterval)
      state.pollInterval = null
    }
  }

  return {
    state,
    fetchTasks,
    startPolling,
    stopPolling,
  }
}