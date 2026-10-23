import axios from 'axios'

// 统一调用 FastAPI（baseURL 为 /api，由 vite 代理或 nginx 反代）。
const http = axios.create({
  baseURL: '/api',
  timeout: 300000, // 生成/解析可能较慢
})

export default http
