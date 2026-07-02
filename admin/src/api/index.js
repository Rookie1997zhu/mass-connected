import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const token = window.__adminAccessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (response) => {
    const payload = response.data
    if (payload?.code && payload.code !== 'OK') return Promise.reject(payload)
    return payload
  },
  (error) => Promise.reject(error.response?.data || error)
)

export default http

export const adminLogin = (data) => http.post('/admin/auth/login', data)
export const fetchServiceCategories = () => http.get('/admin/service-categories')
export const saveServiceCategory = (data) => http.post('/admin/service-categories', data)
export const updateServiceCategory = (id, data) => http.patch(`/admin/service-categories/${id}`, data)
export const fetchRfqs = (params) => http.get('/admin/rfqs', { params })
export const fetchRfq = (id) => http.get(`/admin/rfqs/${id}`)
export const updateRfqStatus = (id, status) => http.patch(`/admin/rfqs/${id}/status`, { status })
export const createRfqQuote = (id, data) => http.post(`/admin/rfqs/${id}/quotes`, data)
export const updateRfqQuote = (quoteId, data) => http.patch(`/admin/quotes/${quoteId}`, data)
export const fetchInquiries = (params) => http.get('/admin/inquiries', { params })
export const updateInquiry = (id, data) => http.patch(`/admin/inquiries/${id}`, data)
export const fetchCases = () => http.get('/admin/cases')
export const saveCase = (data) => http.post('/admin/cases', data)
export const updateCase = (id, data) => http.patch(`/admin/cases/${id}`, data)
export const deleteCase = (id) => http.delete(`/admin/cases/${id}`)
export const fetchNews = () => http.get('/admin/news')
export const saveNews = (data) => http.post('/admin/news', data)
export const updateNews = (id, data) => http.patch(`/admin/news/${id}`, data)
export const deleteNews = (id) => http.delete(`/admin/news/${id}`)
export const fetchFaqs = () => http.get('/admin/faqs')
export const saveFaq = (data) => http.post('/admin/faqs', data)
export const updateFaq = (id, data) => http.patch(`/admin/faqs/${id}`, data)
export const deleteFaq = (id) => http.delete(`/admin/faqs/${id}`)
export const fetchDownloads = () => http.get('/admin/downloads')
export const saveDownload = (data) => http.post('/admin/downloads', data, { headers: { 'Content-Type': 'multipart/form-data' } })
export const fetchContentPages = () => http.get('/admin/content-pages')
export const saveContentPage = (data) => http.post('/admin/content-pages', data)
export const updateContentPage = (id, data) => http.patch(`/admin/content-pages/${id}`, data)
export const fetchNavigation = () => http.get('/admin/navigation')
export const saveNavigationItem = (data) => http.post('/admin/navigation', data)
export const updateNavigationItem = (id, data) => http.patch(`/admin/navigation/${id}`, data)
export const deleteNavigationItem = (id) => http.delete(`/admin/navigation/${id}`)
export const fetchAdminUsers = () => http.get('/admin/admin-users')
export const saveAdminUser = (data) => http.post('/admin/admin-users', data)
export const fetchFactories = (params) => http.get('/admin/factories', { params })
export const updateFactory = (id, data) => http.patch(`/admin/factories/${id}`, data)
export const fetchCategories = () => http.get('/admin/categories')
export const saveCategory = (data) => http.post('/admin/categories', data)
export const updateCategory = (id, data) => http.patch(`/admin/categories/${id}`, data)
export const fetchProducts = (params) => http.get('/admin/products', { params })
export const saveProduct = (data) => http.post('/admin/products', data)
export const updateProduct = (id, data) => http.patch(`/admin/products/${id}`, data)
export const fetchOrders = (params) => http.get('/admin/orders', { params })
export const updateOrder = (id, data) => http.patch(`/admin/orders/${id}`, data)
