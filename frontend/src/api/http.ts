import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '@/utils/auth'

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// 请求拦截：附加 JWT
http.interceptors.request.use((cfg) => {
  const t = getAccessToken()
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

// 响应拦截：统一错误与刷新
let refreshing = false
http.interceptors.response.use(
  (resp) => {
    // 业务包装：{ code, data, message }
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) {
        ElMessage.error(body.message || '请求失败')
        return Promise.reject(body)
      }
      // 返回完整响应对象：调用方通过 res.data 拿到包装体、res.data.data 拿到业务载荷
      // （所有业务模块均使用 res.data.data 约定，切勿在此返回已解包的 body）
      return resp
    }
    return resp
  },
  async (error) => {
    const status = error.response?.status
    const original = error.config || {}
    const url: string = original?.url || ''

    // 公开端点（如平台默认配色）：失败静默，交由调用方处理，不触发登录跳转/错误提示
    if (url.includes('/theme/default')) {
      return Promise.reject(error)
    }

    if (status === 401 && !original._retry) {
      original._retry = true
      const rt = getRefreshToken()
      if (rt && !refreshing) {
        refreshing = true
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: rt })
          setTokens(data.data.access_token, rt)
          refreshing = false
          original.headers = original.headers || {}
          original.headers.Authorization = `Bearer ${data.data.access_token}`
          return http(original)
        } catch {
          refreshing = false
        }
      }
      clearTokens()
      // 已在登录页则不再跳转，避免「重挂载 → 再请求 → 再 401」的闪烁循环
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    ElMessage.error(error.response?.data?.detail || error.message || '网络错误')
    return Promise.reject(error)
  },
)

export default http
