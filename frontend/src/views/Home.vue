<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
        <h1 class="text-2xl font-bold text-xhs-red">小红书评论获取</h1>
        <button
          @click="showSettings = true"
          class="flex items-center gap-2 text-gray-600 hover:text-gray-800"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span>设置</span>
        </button>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div v-if="!clientConnected" class="bg-yellow-50 border border-yellow-200 p-4 rounded-lg mb-4">
        <p class="text-yellow-800 mb-2">请先运行连接脚本：</p>
        <div class="bg-gray-800 text-green-400 p-3 rounded font-mono text-sm overflow-x-auto">
          <pre class="whitespace-pre-wrap">curl -s {{ serverHost }}:{{ serverPort }}/connector/connector.sh | bash</pre>
        </div>
        <button @click="checkClientStatus" class="mt-2 text-sm text-blue-600 hover:underline">
          点击检测连接状态
        </button>
      </div>

      <div v-if="checkingChrome" class="bg-white rounded-lg shadow-md p-8 mb-6">
        <div class="text-center">
          <div class="mb-6">
            <svg class="w-20 h-20 mx-auto text-gray-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <p class="text-gray-500">检查 Chrome 状态中...</p>
        </div>
      </div>

      <div v-else-if="!chromeStarted" class="bg-white rounded-lg shadow-md p-8 mb-6">
        <div class="text-center">
          <div class="mb-6">
            <svg class="w-20 h-20 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 class="text-xl font-bold text-gray-800 mb-2">第一步：启动 Chrome 并登录</h2>
          <p v-if="isRemoteMode" class="text-gray-500 mb-6">
            请在本地手动启动 Chrome 调试模式，端口：{{ chromePort }}<br>
            <span class="text-sm text-gray-400">命令：chrome --remote-debugging-port={{ chromePort }}</span>
          </p>
          <p v-else class="text-gray-500 mb-6">点击下方按钮启动 Chrome 并打开小红书，请手动登录</p>
          <button
            v-if="!isRemoteMode"
            @click="startChrome"
            :disabled="startingChrome"
            class="bg-xhs-red text-white py-3 px-8 rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-lg"
          >
            {{ startingChrome ? '启动中...' : '启动 Chrome' }}
          </button>
          <p v-if="chromeError" class="text-red-500 mt-4">{{ chromeError }}</p>
        </div>
      </div>

      <div v-else class="bg-white rounded-lg shadow-md p-6 mb-6">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            小红书链接
          </label>
          <input
            v-model="url"
            type="text"
            placeholder="https://xiaohongshu.com/explore/xxxxxxxx?xsec_token=xxxxxx"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-xhs-red focus:border-transparent"
          />
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            最大评论数
          </label>
          <input
            v-model.number="maxComments"
            type="number"
            min="1"
            max="100"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-xhs-red focus:border-transparent"
          />
        </div>

        <button
          @click="fetchComments"
          :disabled="loading"
          class="w-full bg-xhs-red text-white py-2 px-4 rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ loading ? '获取中...' : '获取评论' }}
        </button>
      </div>

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 flex items-center justify-between">
        <span>{{ error }}</span>
        <button
          @click="fetchComments"
          class="ml-4 text-sm bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600"
        >
          重试
        </button>
      </div>

      <div class="bg-white rounded-lg shadow-md p-6 mt-6">
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
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span 
                  class="px-2 py-0.5 text-xs rounded-full"
                  :class="{
                    'bg-yellow-100 text-yellow-700': task.status === 'pending',
                    'bg-blue-100 text-blue-700': task.status === 'running',
                    'bg-green-100 text-green-700': task.status === 'completed',
                    'bg-red-100 text-red-700': task.status === 'failed',
                  }"
                >
                  {{ task.status === 'completed' ? '已完成' : task.status === 'running' ? '获取中' : task.status === 'failed' ? '获取失败' : '等待中' }}
                </span>
                <span v-if="task.status === 'running'" class="text-xs text-gray-400">
                  获取进度: {{ task.progress }}%
                </span>
                <span v-else-if="task.note_title" class="text-sm font-medium text-gray-800">
                  {{ task.note_title }}
                </span>
                <span class="text-sm text-gray-500">
                  {{ formatTime(task.created_at) }}
                </span>
                <span v-if="task.comment_count" class="text-xs text-gray-400">
                  共 {{ task.comment_count }} 条评论
                </span>
              </div>

              <div v-if="task.status === 'running'" class="mt-2">
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

              <div class="flex gap-2">
                <button
                  v-if="task.status === 'completed'"
                  @click="downloadTask(task.task_id)"
                  class="bg-green-500 text-white py-1 px-3 rounded-lg hover:bg-green-600 text-sm"
                >
                  下载CSV
                </button>
                <button
                  v-if="task.status === 'completed' && task.classification_status === 'none'"
                  @click="handleClassify(task)"
                  class="bg-purple-500 text-white py-1 px-3 rounded-lg hover:bg-purple-600 text-sm"
                >
                  AI智能分类
                </button>
                <button
                  v-if="task.status === 'completed' && task.classification_status === 'completed'"
                  @click="downloadClassified(task)"
                  class="bg-blue-500 text-white py-1 px-3 rounded-lg hover:bg-blue-600 text-sm"
                >
                  下载分类CSV
                </button>
              </div>
            </div>
            
            <p class="text-xs text-blue-500 hover:underline cursor-pointer mb-1" @click="openUrl(task.url)">
              {{ task.url }}
            </p>
            
            <p v-if="task.status === 'completed'" class="text-sm text-gray-600">
              已获取 {{ task.total_fetched }} 条评论
            </p>

            <div v-if="task.classification_status === 'running'" class="mt-2">
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
                  正面: {{ task.classification_summary?.praise || 0 }},
                  问题: {{ task.classification_summary?.question || 0 }},
                  中性: {{ task.classification_summary?.neutral || 0 }},
                  建设性: {{ task.classification_summary?.constructive || 0 }},
                  垃圾: {{ task.classification_summary?.spam || 0 }},
                  攻击性: {{ task.classification_summary?.hate || 0 }}
                </span>
              </div>

              <div class="mt-3 flex gap-2 flex-wrap">
                <span class="text-sm text-gray-500">回复:</span>
                <div v-if="replyProgress[task.task_id]?.completed" class="flex items-center gap-2">
                  <span class="text-sm text-green-600 bg-green-50 px-3 py-1 rounded">
                    已完成
                  </span>
                </div>
                <div v-else class="flex gap-2">
                  <label 
                    v-if="!replyData[task.task_id]?.fileName"
                    class="cursor-pointer bg-blue-500 text-white py-1 px-3 rounded-lg hover:bg-blue-600 text-sm"
                  >
                    上传CSV回复
                    <input
                      type="file"
                      accept=".csv"
                      class="hidden"
                      @change="(e) => handleCsvUpload(e, task)"
                    />
                  </label>
                  <div v-if="replyData[task.task_id]?.fileName" class="flex items-center gap-2">
                    <span class="text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded">
                      {{ replyData[task.task_id].fileName }}
                    </span>
                    <button
                      @click="() => removeUploadedFile(task.task_id)"
                      class="text-red-500 hover:text-red-700 text-sm"
                    >
                      删除
                    </button>
                  </div>
                  <button
                    v-if="task.classification_status === 'completed'"
                    @click="() => directReply(task)"
                    class="bg-purple-500 text-white py-1 px-3 rounded-lg hover:bg-purple-600 text-sm"
                  >
                    直接回复
                  </button>
                </div>
              </div>

              <div v-if="replyData[task.task_id]?.to_reply > 0" class="mt-3 bg-green-50 border border-green-200 rounded-lg p-3">
                <div v-if="replyProgress[task.task_id]?.completed">
                  <p class="text-sm text-green-700">
                    成功回复 {{ replyProgress[task.task_id].sended }} 条
                  </p>
                </div>
                <div v-else>
                  <p class="text-sm text-green-700 mb-2">
                    确认发送 {{ replyData[task.task_id].to_reply }} 条回复？
                  </p>
                  <button
                    @click="() => confirmReply(task)"
                    :disabled="replyProgress[task.task_id]?.running"
                    class="bg-green-500 text-white py-1 px-3 rounded-lg hover:bg-green-600 text-sm disabled:opacity-50"
                  >
                    确认发送
                  </button>
                </div>
              </div>

              <div v-if="replyProgress[task.task_id]?.running" class="mt-3 bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p class="text-sm text-blue-700">
                  正在发送 {{ replyProgress[task.task_id].current }}/{{ replyProgress[task.task_id].total }}
                </p>
                <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
                  <div 
                    class="bg-blue-500 h-2 rounded-full"
                    :style="{ width: (replyProgress[task.task_id].current / replyProgress[task.task_id].total * 100) + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <div v-if="showReplyModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h3 class="text-lg font-bold mb-4">回复评论</h3>
        
        <div v-if="replyTarget" class="mb-4 p-3 bg-gray-50 rounded-lg text-sm">
          <p class="text-gray-600">回复: {{ replyTarget.user.nickname }}</p>
          <p class="text-gray-800 mt-1">{{ replyTarget.content }}</p>
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            回复内容
          </label>
          <textarea
            v-model="replyContent"
            rows="3"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-xhs-red focus:border-transparent"
            placeholder="输入回复内容..."
          ></textarea>
        </div>

        <div class="flex gap-3">
          <button
            @click="submitReply"
            :disabled="replying"
            class="flex-1 bg-xhs-red text-white py-2 px-4 rounded-lg hover:bg-red-600 disabled:opacity-50"
          >
            {{ replying ? '发送中...' : '发送' }}
          </button>
          <button
            @click="closeReplyModal"
            class="flex-1 bg-gray-200 text-gray-800 py-2 px-4 rounded-lg hover:bg-gray-300"
          >
            取消
          </button>
        </div>
      </div>
    </div>

    <div v-if="showSettings" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h3 class="text-lg font-bold mb-4">白名单设置</h3>
        
        <p class="text-sm text-gray-600 mb-3">请输入要排除的用户ID，每行一个：</p>
        
        <textarea
          v-model="whitelistInput"
          rows="10"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-xhs-red focus:border-transparent font-mono text-sm"
          placeholder="user_id_1
user_id_2
user_id_3"
        ></textarea>

        <p class="text-xs text-gray-500 mt-2">白名单用户的评论不会被保存到CSV中</p>
        
        <div class="flex gap-3 mt-4">
          <button
            @click="saveWhitelist"
            :disabled="savingWhitelist"
            class="flex-1 bg-xhs-red text-white py-2 px-4 rounded-lg hover:bg-red-600 disabled:opacity-50"
          >
            {{ savingWhitelist ? '保存中...' : '保存' }}
          </button>
          <button
            @click="showSettings = false"
            class="flex-1 bg-gray-200 text-gray-800 py-2 px-4 rounded-lg hover:bg-gray-300"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { xhsApi } from '../api/xhs'
import { useExportStore } from '../stores/export'

const router = useRouter()
const exportStore = useExportStore()

const chromeStarted = ref(false)
const checkingChrome = ref(true)
const startingChrome = ref(false)
const chromeError = ref('')
const isRemoteMode = ref(false)
const chromePort = ref(9292)
const clientConnected = ref(false)
const url = ref('')
const maxComments = ref(20)
const loading = ref(false)
const replying = ref(false)
const error = ref('')
const note = ref(null)
const comments = ref([])
const totalComments = ref(0)
const displayedCount = 5
const showReplyModal = ref(false)
const replyTarget = ref(null)
const replyContent = ref('')
const replyData = ref({})
const replyProgress = ref({})
let replyInterval = null
const showSettings = ref(false)
const whitelistInput = ref('')
const savingWhitelist = ref(false)

const serverHost = typeof __SERVER_HOST__ !== 'undefined' ? __SERVER_HOST__ : 'localhost'
const serverPort = typeof __SERVER_PORT__ !== 'undefined' ? __SERVER_PORT__ : 5000

const displayedComments = computed(() => {
  return comments.value.slice(0, displayedCount)
})

const goToExportHistory = async () => {
  if (!url.value) {
    error.value = '请先输入小红书链接'
    return
  }
  
  try {
    await xhsApi.exportCommentsAsync(url.value, maxComments.value)
    exportStore.startPolling()
    router.push('/export-history')
  } catch (e) {
    error.value = e.message || '启动导出失败'
  }
}

const startChrome = async () => {
  startingChrome.value = true
  chromeError.value = ''

  try {
    const res = await xhsApi.startChrome()
    if (res.success) {
      chromeStarted.value = true
    } else {
      chromeError.value = res.error || '启动 Chrome 失败'
    }
  } catch (e) {
    chromeError.value = e.message || '网络错误'
  } finally {
    startingChrome.value = false
  }
}

const checkChromeStatus = async () => {
  try {
    const res = await xhsApi.checkChrome()
    chromeStarted.value = res.data?.running || false
    isRemoteMode.value = res.data?.is_remote || false
    chromePort.value = res.data?.chrome_port || 9292
  } catch (e) {
    chromeStarted.value = false
  } finally {
    checkingChrome.value = false
  }
}

const checkClientStatus = async () => {
  try {
    const res = await fetch('/api/client-status')
    const json = await res.json()
    clientConnected.value = json.connected
  } catch {
    clientConnected.value = false
  }
}

const fetchComments = async () => {
  if (!url.value) {
    error.value = '请输入小红书链接'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const res = await xhsApi.getComments(url.value, maxComments.value)
    if (res.success) {
      note.value = res.data.note
      comments.value = res.data.comments
      totalComments.value = res.data.total_comments
      await exportStore.fetchTasks()
    } else {
      error.value = res.error || '获取评论失败'
    }
  } catch (e) {
    error.value = e.message || '网络错误'
  } finally {
    loading.value = false
  }
}

const openReplyModal = (comment) => {
  replyTarget.value = comment
  showReplyModal.value = true
}

const closeReplyModal = () => {
  showReplyModal.value = false
  replyTarget.value = null
  replyContent.value = ''
}

const submitReply = async () => {
  if (!replyContent.value) {
    error.value = '请输入回复内容'
    return
  }

  replying.value = true
  error.value = ''

  try {
    const res = await xhsApi.replyComment(
      url.value,
      replyContent.value,
      replyTarget.value?.id || '',
      replyTarget.value?.user?.user_id || ''
    )
    if (res.success) {
      closeReplyModal()
    } else {
      error.value = res.error || '回复失败'
    }
  } catch (e) {
    error.value = e.message || '网络错误'
  } finally {
    replying.value = false
  }
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

const classificationPollInterval = ref(null)

const handleClassify = async (task) => {
  if (classificationPollInterval.value) {
    clearInterval(classificationPollInterval.value)
  }
  try {
    await xhsApi.startClassify(task.task_id)
    await exportStore.fetchTasks()
    pollClassificationStatus(task.task_id)
  } catch (e) {
    console.error('分类失败', e)
  }
}

const pollClassificationStatus = async (taskId) => {
  let attempts = 0
  classificationPollInterval.value = setInterval(async () => {
    attempts++
    if (attempts >= 150) {
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
    const url = window.URL.createObjectURL(new Blob([res]))
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

onUnmounted(() => {
  if (replyInterval) clearInterval(replyInterval)
  exportStore.stopPolling()
})

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
    }
  } catch (e) {
    console.error('下载失败', e)
  }
}

const openUrl = (url) => {
  window.open(url, '_blank')
}

const handleCsvUpload = async (event, task) => {
  const file = event.target.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await fetch('/api/reply-from-csv', {
      method: 'POST',
      body: formData,
    })
    const json = await res.json()
    if (json.success) {
      replyData.value = { ...replyData.value, [task.task_id]: { ...json.data, fileName: file.name } }
    } else {
      alert(json.error || '上传失败')
    }
  } catch (e) {
    alert(`上传失败: ${e.message}`)
  }
  event.target.value = ''
}

const removeUploadedFile = (taskId) => {
  const newReplyData = { ...replyData.value }
  delete newReplyData[taskId]
  replyData.value = newReplyData
}

const confirmReply = async (task) => {
  const data = replyData.value[task.task_id]
  if (!data || data.to_reply === 0) return

  try {
    await fetch('/api/reply-confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: task.url,
        comments: data.comments,
      }),
    })
    replyProgress.value = {
      ...replyProgress.value,
      [task.task_id]: { running: true, current: 0, total: data.to_reply, sended: 0, completed: false },
    }
    pollReplyStatus(task.task_id)
  } catch (e) {
    alert(`发送失败: ${e.message}`)
  }
}

const directReply = async (task) => {
  try {
    const res = await fetch('/api/reply-direct', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: task.task_id }),
    })
    const json = await res.json()
    if (json.success) {
      replyData.value = {
        ...replyData.value,
        [task.task_id]: { to_reply: json.data.to_reply, fileName: 'AI分类回复' },
      }
      replyProgress.value = {
        ...replyProgress.value,
        [task.task_id]: { running: true, current: 0, total: json.data.to_reply, sended: 0, completed: false },
      }
      pollReplyStatus(task.task_id)
    } else {
      alert(json.error || '直接回复失败')
    }
  } catch (e) {
    alert(`直接回复失败: ${e.message}`)
  }
}

const pollReplyStatus = (taskId) => {
  if (replyInterval) clearInterval(replyInterval)

  replyInterval = setInterval(async () => {
    try {
      const res = await fetch('/api/reply-status')
      const json = await res.json()
      if (json.success) {
        const status = json.data
        replyProgress.value = {
          ...replyProgress.value,
          [taskId]: {
            current: status.current,
            total: status.total,
            sended: status.sended,
            failed: status.failed,
            running: status.running,
            completed: !status.running,
          },
        }
        if (!status.running) {
          clearInterval(replyInterval)
          replyInterval = null
        }
      }
    } catch (e) {
      console.error('查询状态失败', e)
    }
  }, 2000)
}

const loadWhitelist = async () => {
  try {
    const res = await xhsApi.getWhitelist()
    if (res.success) {
      whitelistInput.value = (res.data.user_ids || []).join('\n')
    }
  } catch (e) {
    console.error('加载白名单失败', e)
  }
}

const saveWhitelist = async () => {
  savingWhitelist.value = true
  try {
    const userIds = whitelistInput.value
      .split('\n')
      .map(s => s.trim())
      .filter(s => s)
    
    await xhsApi.saveWhitelist(userIds)
    showSettings.value = false
    alert('白名单已保存')
  } catch (e) {
    alert('保存失败: ' + e.message)
  } finally {
    savingWhitelist.value = false
  }
}

onMounted(() => {
  checkClientStatus()
  checkChromeStatus()
  exportStore.fetchTasks()
  exportStore.startPolling()
  loadWhitelist()
})
</script>