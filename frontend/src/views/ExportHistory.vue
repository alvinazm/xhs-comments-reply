<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <router-link to="/" class="text-2xl font-bold text-xhs-red">小红书评论获取</router-link>
        <nav class="flex gap-4">
          <router-link to="/" class="text-gray-600 hover:text-xhs-red">评论获取</router-link>
          <router-link to="/export-history" class="text-gray-600 hover:text-xhs-red font-medium">导出历史</router-link>
        </nav>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-xl font-bold mb-6">导出历史</h2>
        
        <div v-if="exportStore.state.tasks.length === 0" class="text-center py-8 text-gray-500">
          暂无导出记录
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="task in exportStore.state.tasks"
            :key="task.task_id"
            class="border border-gray-200 rounded-lg p-4"
          >
            <div class="flex items-start justify-between mb-3">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <span 
                    class="px-2 py-0.5 text-xs rounded-full"
                    :class="{
                      'bg-yellow-100 text-yellow-700': task.status === 'pending',
                      'bg-blue-100 text-blue-700': task.status === 'running',
                      'bg-green-100 text-green-700': task.status === 'completed',
                      'bg-red-100 text-red-700': task.status === 'failed',
                    }"
                  >
                    {{ statusText(task.status) }}
                  </span>
                  <span class="text-sm text-gray-500">
                    {{ formatTime(task.created_at) }}
                  </span>
                </div>
                <p class="text-sm text-gray-600 truncate max-w-xl">{{ task.url }}</p>
                <p class="text-xs text-gray-400 mt-1">
                  最大评论数: {{ task.max_comments }}
                </p>
              </div>

              <div v-if="task.status === 'completed'" class="ml-4">
                <button
                  @click="downloadTask(task.task_id)"
                  class="bg-green-500 text-white py-1 px-3 rounded-lg hover:bg-green-600 text-sm"
                >
                  下载
                </button>
              </div>
            </div>

            <div v-if="task.status === 'running'" class="mb-2">
              <div class="flex justify-between text-sm mb-1">
                <span class="text-gray-600">进度</span>
                <span class="text-gray-500">{{ task.progress }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div 
                  class="bg-blue-500 h-2 rounded-full transition-all"
                  :style="{ width: task.progress + '%' }"
                ></div>
              </div>
              <p class="text-xs text-gray-500 mt-1">
                已获取 {{ task.total_fetched }} 条评论
              </p>
            </div>

            <div v-if="task.status === 'completed'" class="text-sm text-gray-600">
              已获取 {{ task.total_fetched }} 条评论
            </div>

            <div v-if="task.status === 'failed'" class="text-sm text-red-500">
              失败: {{ task.error_message }}
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { xhsApi } from '../api/xhs'
import { useExportStore } from '../stores/export'

const exportStore = useExportStore()

const statusText = (status) => {
  const map = {
    pending: '等待中',
    running: '进行中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

const formatTime = (isoString) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const downloadTask = async (taskId) => {
  try {
    const response = await fetch(`/api/export-download/${taskId}`)
    const contentType = response.headers.get('content-type') || ''
    if (response.ok && contentType.includes('text/csv')) {
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `comments_${taskId.slice(0, 8)}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(downloadUrl)
    } else {
      const text = await response.text()
      try {
        const json = JSON.parse(text)
        alert(json.error || '下载失败')
      } catch {
        alert(text.substring(0, 100) || '下载失败')
      }
    }
  } catch (e) {
    alert(`下载失败: ${e.message}`)
  }
}

onMounted(() => {
  exportStore.fetchTasks()
  exportStore.startPolling()
})

onUnmounted(() => {
  exportStore.stopPolling()
})
</script>