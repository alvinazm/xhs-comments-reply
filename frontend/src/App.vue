<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <h1 class="text-2xl font-bold text-xhs-red">小红书评论获取</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div v-if="!chromeStarted" class="bg-white rounded-lg shadow-md p-8 mb-6">
        <div class="text-center">
          <div class="mb-6">
            <svg class="w-20 h-20 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 class="text-xl font-bold text-gray-800 mb-2">第一步：启动 Chrome 并登录</h2>
          <p class="text-gray-500 mb-6">点击下方按钮启动 Chrome 并打开小红书，请手动登录</p>
          <button
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
        <div class="flex items-center gap-3 mb-4">
          <span class="w-3 h-3 bg-green-500 rounded-full"></span>
          <span class="text-green-700 font-medium">Chrome 已启动</span>
        </div>

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
          {{ loading ? '加载中...' : '获取评论' }}
        </button>
      </div>

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
        {{ error }}
      </div>

      <div v-if="note" class="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 class="text-xl font-bold mb-4">{{ note.title }}</h2>
        <div class="flex items-center gap-4 mb-4">
          <span class="text-gray-600">作者: {{ note.user.nickname }}</span>
          <span class="text-gray-400">|</span>
          <span class="text-gray-600">IP属地: {{ note.ip_location }}</span>
        </div>
        <div class="flex gap-6 text-sm text-gray-500">
          <span>👍 {{ note.interact_info.liked_count }}</span>
          <span>⭐ {{ note.interact_info.collected_count }}</span>
          <span>💬 {{ note.interact_info.comment_count }}</span>
          <span>↗️ {{ note.interact_info.shared_count }}</span>
        </div>
      </div>

      <div v-if="comments.length > 0" class="bg-white rounded-lg shadow-md p-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">评论列表 (展示 {{ displayedComments.length }} 条，共 {{ totalComments }} 条)</h3>
          <button
            @click="downloadCsv"
            class="bg-green-500 text-white py-1 px-3 rounded-lg hover:bg-green-600 text-sm"
          >
            下载CSV
          </button>
        </div>

        <div v-if="totalComments > displayedComments.length" class="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg mb-4 text-sm">
          完整 {{ totalComments }} 条评论请下载 CSV 查看
        </div>

        <div class="space-y-4">
          <div
            v-for="comment in displayedComments"
            :key="comment.id"
            class="border-b border-gray-100 pb-4 last:border-0"
          >
            <div class="flex items-start gap-3">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <span class="font-medium">{{ comment.user.nickname }}</span>
                  <span class="text-xs text-gray-500">(ID: {{ comment.user.user_id }})</span>
                  <span class="text-xs text-gray-400">{{ comment.ip_location }}</span>
                </div>
                <p class="text-gray-800 mb-2">{{ comment.content }}</p>
                <div class="flex flex-wrap items-center gap-4 text-sm text-gray-500 mb-2">
                  <span>👍 {{ comment.like_count }}</span>
                  <span>🕐 {{ comment.create_time_str }}</span>
                  <span>ID: {{ comment.id }}</span>
                </div>
                <button
                  @click="openReplyModal(comment)"
                  class="text-xhs-red hover:underline text-sm"
                >
                  回复
                </button>

                <div v-if="comment.sub_comments && comment.sub_comments.length > 0" class="mt-3 pl-4 border-l-2 border-gray-100 space-y-3">
                  <div v-for="sub in comment.sub_comments" :key="sub.id" class="text-sm">
                    <div class="flex items-center gap-2">
                      <span class="font-medium">{{ sub.user.nickname }}</span>
                      <span class="text-xs text-gray-400">{{ sub.ip_location }}</span>
                    </div>
                    <p class="text-gray-700 mt-1">{{ sub.content }}</p>
                  </div>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { xhsApi } from './api/xhs'

const chromeStarted = ref(false)
const startingChrome = ref(false)
const chromeError = ref('')
const url = ref('')
const maxComments = ref(20)
const loading = ref(false)
const replying = ref(false)
const error = ref('')
const note = ref(null)
const comments = ref([])
const totalComments = ref(0)
const displayedCount = 5
const sessionId = ref(null)
const showReplyModal = ref(false)
const replyTarget = ref(null)
const replyContent = ref('')

const displayedComments = computed(() => {
  return comments.value.slice(0, displayedCount)
})

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
    chromeStarted.value = res.running || false
  } catch (e) {
    chromeStarted.value = false
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
      sessionId.value = res.data.session_id
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

onMounted(() => {
  checkChromeStatus()
})

const downloadCsv = async () => {
  if (!sessionId.value) {
    error.value = '请先获取评论后再下载'
    return
  }
  try {
    const response = await fetch('/api/download-cached-csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value }),
    })
    const contentType = response.headers.get('content-type') || ''
    if (response.ok && contentType.includes('text/csv')) {
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `comments_${note.value?.note_id || 'export'}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(downloadUrl)
    } else {
      const text = await response.text()
      try {
        const json = JSON.parse(text)
        error.value = json.error || '下载 CSV 失败'
      } catch {
        error.value = text.substring(0, 100) || '下载 CSV 失败'
      }
    }
  } catch (e) {
    error.value = `下载 CSV 失败: ${e.message}`
  }
}
</script>
