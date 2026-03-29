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

              <div v-if="task.status === 'completed'" class="ml-4 flex gap-2">
                <button
                  @click="downloadTask(task.task_id)"
                  class="bg-green-500 text-white py-1 px-3 rounded-lg hover:bg-green-600 text-sm"
                >
                  下载
                </button>
                <button
                  v-if="task.classification_status === 'none'"
                  @click="handleClassify(task)"
                  class="bg-purple-500 text-white py-1 px-3 rounded-lg hover:bg-purple-600 text-sm"
                >
                  AI智能分类
                </button>
                <button
                  v-if="task.classification_status === 'completed'"
                  @click="downloadClassified(task)"
                  class="bg-blue-500 text-white py-1 px-3 rounded-lg hover:bg-blue-600 text-sm"
                >
                  下载分类CSV
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

            <div v-if="task.classification_status === 'running'" class="mb-2 mt-2">
              <div class="flex justify-between text-sm mb-1">
                <span class="text-purple-600">AI分类中...</span>
                <span class="text-gray-500">{{ task.classification_progress }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div 
                  class="bg-purple-500 h-2 rounded-full transition-all"
                  :style="{ width: task.classification_progress + '%' }"
                ></div>
              </div>
            </div>

            <div v-if="task.classification_status === 'completed'" class="mt-2">
              <div class="inline-flex items-center gap-2 px-3 py-1 bg-purple-50 rounded-full">
                <span class="text-sm text-purple-700">AI分类完成:</span>
                <span class="text-xs text-gray-600">
                  正面: {{ task.classification_summary?.positive || 0 }},
                  负面: {{ task.classification_summary?.negative || 0 }},
                  问题: {{ task.classification_summary?.question || 0 }}
                </span>
              </div>
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
import { onMounted, onUnmounted, ref } from 'vue'
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

const handleClassify = async (task) => {
  try {
    await xhsApi.startClassify(task.task_id)
    pollClassificationStatus(task.task_id)
  } catch (e) {
    console.error('分类失败', e)
  }
}

const classificationPollInterval = ref(null)
const MAX_POLL_ATTEMPTS = 150

const pollClassificationStatus = async (taskId) => {
  let attempts = 0
  classificationPollInterval.value = setInterval(async () => {
    attempts++
    if (attempts >= MAX_POLL_ATTEMPTS) {
      clearInterval(classificationPollInterval.value)
      return
    }
    try {
      const res = await xhsApi.getClassificationStatus(taskId)
      const data = res.data.data
      if (data.classification_status === 'completed' || data.classification_status === 'failed') {
        clearInterval(classificationPollInterval.value)
        await exportStore.fetchTasks()
      }
    } catch (e) {
      console.error('获取分类状态失败', e)
    }
  }, 2000)
}

const downloadClassified = async (task) => {
  try {
    const res = await xhsApi.downloadClassifiedFile(task.task_id)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `classified_${task.task_id.slice(0, 8)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error('下载失败', e)
  }
}

onMounted(() => {
  exportStore.fetchTasks()
  exportStore.startPolling()
})

onUnmounted(() => {
  exportStore.stopPolling()
  if (classificationPollInterval.value) {
    clearInterval(classificationPollInterval.value)
  }
})
</script>