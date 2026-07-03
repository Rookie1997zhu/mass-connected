import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

let refreshPromise = null

http.interceptors.request.use((config) => {
  const token = window.__memberAccessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const locale = localStorage.getItem('locale') || 'ko'
  config.headers['Accept-Language'] = locale
  return config
})

http.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response.data
    }
    const payload = response.data
    if (payload && payload.code && payload.code !== 'OK') {
      return Promise.reject(payload)
    }
    return payload
  },
  async (error) => {
    const original = error.config
    const status = error.response?.status
    if (status === 401 && original && !original._retry && !original.url?.includes('/auth/refresh')) {
      const auth = useAuthStore()
      if (auth.refreshToken) {
        original._retry = true
        try {
          if (!refreshPromise) {
            refreshPromise = auth.refreshAccessToken().finally(() => {
              refreshPromise = null
            })
          }
          await refreshPromise
          original.headers.Authorization = `Bearer ${window.__memberAccessToken}`
          return http(original)
        } catch {
          auth.logout()
        }
      }
    }
    return Promise.reject(error.response?.data || error)
  }
)

export default http
