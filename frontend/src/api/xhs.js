import axios from 'axios'

const API_BASE_URL = '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.error || error.message || '网络错误'
    return Promise.reject(new Error(message))
  }
)

export const xhsApi = {
  startChrome() {
    return apiClient.post('/start-chrome')
  },

  checkChrome() {
    return apiClient.get('/check-chrome')
  },

  parseUrl(url) {
    return apiClient.post('/parse-url', { url })
  },

  getComments(url, maxComments = 20) {
    return apiClient.post('/get-comments', { url, max_comments: maxComments })
  },

  replyComment(url, content, commentId = '', userId = '') {
    return apiClient.post('/reply-comment', {
      url,
      content,
      comment_id: commentId,
      user_id: userId,
    })
  },

  exportCommentsAsync(url, maxComments) {
    return apiClient.post('/export-comments-async', { url, max_comments: maxComments })
  },

  getExportStatus(taskId) {
    return apiClient.get(`/export-status/${taskId}`)
  },

  downloadExportFile(taskId) {
    return apiClient.get(`/export-download/${taskId}`, {
      responseType: 'blob',
    })
  },

  getAllExportTasks() {
    return apiClient.get('/export-tasks')
  },

  startClassify(taskId, batchSize = 20, workers = 5) {
    return apiClient.post(`/classify/${taskId}`, { batch_size: batchSize, workers })
  },

  getClassificationStatus(taskId) {
    return apiClient.get(`/classification-status/${taskId}`)
  },

  downloadClassifiedFile(taskId) {
    return apiClient.get(`/download-classified/${taskId}`, { responseType: 'blob' })
  },
}

export default xhsApi
