import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

let refreshPromise = null

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
          original.headers.Authorization = `Bearer ${window.__adminAccessToken}`
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

export const adminLogin = (data) => http.post('/admin/auth/login', data)
export const fetchAdminStats = () => http.get('/admin/stats')
export const fetchServiceCategories = () => http.get('/admin/service-categories')
export const saveServiceCategory = (data) => http.post('/admin/service-categories', data)
export const updateServiceCategory = (id, data) => http.patch(`/admin/service-categories/${id}`, data)
export const fetchRfqs = (params) => http.get('/admin/rfqs', { params })
export const fetchRfq = (id) => http.get(`/admin/rfqs/${id}`)
export const updateRfqStatus = (id, data) => http.patch(`/admin/rfqs/${id}/status`, data)
export const createRfqQuote = (id, data) => http.post(`/admin/rfqs/${id}/quotes`, data)
export const updateRfqQuote = (quoteId, data) => http.patch(`/admin/quotes/${quoteId}`, data)
export const fetchInquiries = (params) => http.get('/admin/inquiries', { params })
export const fetchInquiry = (id) => http.get(`/admin/inquiries/${id}`)
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
export const fetchProductionOrders = (params) => http.get('/admin/production-orders', { params })
export const updateProductionOrder = (id, data) => http.patch(`/admin/production-orders/${id}`, data)
export const fetchCategories = () => http.get('/admin/categories')
export const saveCategory = (data) => http.post('/admin/categories', data)
export const updateCategory = (id, data) => http.patch(`/admin/categories/${id}`, data)
export const fetchProducts = (params) => http.get('/admin/products', { params })
export const saveProduct = (data) => http.post('/admin/products', data)
export const updateProduct = (id, data) => http.patch(`/admin/products/${id}`, data)
export const fetchOrders = (params) => http.get('/admin/orders', { params })
export const updateOrder = (id, data) => http.patch(`/admin/orders/${id}`, data)

// 供应商管理（管理员建号）
export const fetchSuppliers = (params) => http.get('/admin/suppliers', { params })
export const createSupplier = (data) => http.post('/admin/suppliers', data)
export const fetchSupplier = (id) => http.get(`/admin/suppliers/${id}`)
export const updateSupplier = (id, data) => http.patch(`/admin/suppliers/${id}`, data)
export const addSupplierTag = (id, data) => http.post(`/admin/suppliers/${id}/tags`, data)
export const deleteSupplierTag = (id, data) => http.delete(`/admin/suppliers/${id}/tags`, { data })
export const addSupplierAttachment = (id, formData) =>
  http.post(`/admin/suppliers/${id}/attachments`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const deleteSupplierAttachment = (id, data) => http.delete(`/admin/suppliers/${id}/attachments`, { data })

// RFQ 指派 & 报价请求
export const fetchRfqQuoteRequests = (id) => http.get(`/admin/rfqs/${id}/quote-requests`)
export const reviseQuoteRequest = (id) => http.post(`/admin/quote-requests/${id}/revise`)
export const cancelQuoteRequest = (id) => http.post(`/admin/quote-requests/${id}/cancel`)

export const fetchAdminNotifications = (params) => http.get('/admin/notifications', { params })
export const fetchAdminUnreadCount = () => http.get('/admin/notifications/unread-count')
export const markAdminNotificationRead = (id) => http.post(`/admin/notifications/${id}/read`)
export const markAllAdminNotificationsRead = () => http.post('/admin/notifications/read-all')

// 积分
export const fetchPointRules = () => http.get('/admin/points/rules')
export const savePointRule = (data) => http.post('/admin/points/rules', data)
export const updatePointRule = (id, data) => http.patch(`/admin/points/rules/${id}`, data)
export const fetchRecharges = (params) => http.get('/admin/points/recharges', { params })
export const confirmRecharge = (id) => http.post(`/admin/points/recharges/${id}/confirm`)
export const adjustUserPoints = (userId, data) => http.post(`/admin/points/users/${userId}`, data)
export const fetchUserPoints = (userId) => http.get(`/admin/points/users/${userId}`)

// 会员
export const fetchMembers = (params) => http.get('/admin/members', { params })

// 简单报价参数
export const fetchQuoteParams = (params) => http.get('/admin/quote-params', { params })
export const saveQuoteParam = (data) => http.post('/admin/quote-params', data)
export const updateQuoteParam = (id, data) => http.patch(`/admin/quote-params/${id}`, data)

export const fetchQuoteTables = (params) => http.get('/admin/quote-tables', { params })
export const saveQuoteTable = (data) => http.post('/admin/quote-tables', data)
export const updateQuoteTable = (id, data) => http.patch(`/admin/quote-tables/${id}`, data)

export const fetchPrint3dConfig = () => http.get('/admin/print3d-config')
export const savePrint3dConfig = (data) => http.put('/admin/print3d-config', data)
export const previewPrint3dConfig = (data) => http.post('/admin/print3d-config/preview', data)

export const fetchDielineTemplates = () => http.get('/admin/dieline-templates')
export const fetchDielineCategories = () => http.get('/admin/dieline-categories')
export const saveDielineCategory = (data) => http.post('/admin/dieline-categories', data)
export const updateDielineCategory = (id, data) => http.patch(`/admin/dieline-categories/${id}`, data)
export const deleteDielineCategory = (id) => http.delete(`/admin/dieline-categories/${id}`)
export const saveDielineTemplate = (formData) =>
  http.post('/admin/dieline-templates', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const updateDielineTemplate = (id, formData) =>
  http.patch(`/admin/dieline-templates/${id}`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const deleteDielineTemplate = (id) => http.delete(`/admin/dieline-templates/${id}`)
export const fetchDielineTemplateAssets = (templateId) => http.get(`/admin/dieline-templates/${templateId}/assets`)
export const uploadDielineTemplateAsset = (templateId, formData) =>
  http.post(`/admin/dieline-templates/${templateId}/assets`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const updateDielineTemplateAsset = (templateId, assetId, data) =>
  http.patch(`/admin/dieline-templates/${templateId}/assets/${assetId}`, data)
export const activateDielineTemplateAsset = (templateId, assetId) =>
  http.post(`/admin/dieline-templates/${templateId}/assets/${assetId}/activate`)
export const deleteDielineTemplateAsset = (templateId, assetId) =>
  http.delete(`/admin/dieline-templates/${templateId}/assets/${assetId}`)

// 项目
export const fetchProjects = (params) => http.get('/admin/projects', { params })
export const fetchProject = (id) => http.get(`/admin/projects/${id}`)
export const updateProject = (id, data) => http.patch(`/admin/projects/${id}`, data)
export const createProjectTodo = (id, data) => http.post(`/admin/projects/${id}/todos`, data)

// 合同 / 付款
export const fetchContracts = (params) => http.get('/admin/contracts', { params })
export const fetchPayments = (params) => http.get('/admin/payments', { params })
export const confirmPayment = (id) => http.post(`/admin/payments/${id}/confirm`)

// 聊天纠纷介入
export const fetchAdminChatDisputes = (params) => http.get('/admin/chat/disputes', { params })
export const fetchAdminChatMessages = (id, params) =>
  http.get(`/admin/chat/conversations/${id}/messages`, { params })
export const sendAdminChatMessage = (id, body) =>
  http.post(`/admin/chat/conversations/${id}/messages`, { body })
export const resolveAdminChatDispute = (id) =>
  http.post(`/admin/chat/conversations/${id}/dispute/resolve`)

