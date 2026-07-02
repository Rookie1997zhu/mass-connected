import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

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
    const payload = response.data
    if (payload && payload.code && payload.code !== 'OK') {
      return Promise.reject(payload)
    }
    return payload
  },
  (error) => Promise.reject(error.response?.data || error)
)

export default http
