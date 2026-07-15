import http from './http'

export const fetchServiceCategories = () => http.get('/public/service-categories')
export const fetchCategories = () => http.get('/public/categories')
export const fetchProducts = (params) => http.get('/public/products', { params })
export const fetchProduct = (id) => http.get(`/public/products/${id}`)
export const fetchCases = (params) => http.get('/public/cases', { params })
export const fetchCase = (id) => http.get(`/public/cases/${id}`)
export const fetchNews = (params) => http.get('/public/news', { params })
export const fetchNewsItem = (id) => http.get(`/public/news/${id}`)
export const fetchFaqs = () => http.get('/public/faqs')
export const fetchDownloads = (params) => http.get('/public/downloads', { params })
export const fetchContentPage = (pageKey) => http.get(`/public/content-pages/${pageKey}`)
export const fetchNavigation = () => http.get('/public/navigation')
export const submitInquiry = (data) => http.post('/public/inquiries', data)

export const memberRegister = (data) => http.post('/member/auth/register', data)
export const factoryRegister = (data) => http.post('/factory/auth/register', data)
export const memberLogin = (data) => http.post('/member/auth/login', data)
export const fetchProfile = () => http.get('/member/profile')
export const fetchFactoryProfile = () => http.get('/factory/profile')
export const fetchPartners = (params) => http.get('/public/partners', { params })

export const createRfq = (data) => http.post('/member/rfqs', data)
export const uploadRfqAttachment = (id, formData) =>
  http.post(`/member/rfqs/${id}/attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const fetchMyRfqs = (params) => http.get('/member/rfqs', { params })
export const fetchMyRfq = (id) => http.get(`/member/rfqs/${id}`)
export const fetchMyRfqFulfillment = (id) => http.get(`/member/rfqs/${id}/fulfillment`)
export const updateMyRfq = (id, data) => http.patch(`/member/rfqs/${id}`, data)
export const acceptQuote = (rfqId, quoteId) =>
  http.post(`/member/rfqs/${rfqId}/quotes/${quoteId}/accept`)
export const fetchMyQuoteDetail = (rfqId, quoteId) =>
  http.get(`/member/rfqs/${rfqId}/quotes/${quoteId}`)

export const fetchDemandHall = (params) => http.get('/public/demand-hall', { params })
export const fetchDemandDetail = (id) => http.get(`/public/demand-hall/${id}`)
export const grabDemand = (rfqId) => http.post(`/supplier/demand-hall/${rfqId}/grab`)
export const fetchMyFactoryQuotes = (params) => http.get('/supplier/quotes', { params })

// 供应商抢单报价请求
export const fetchSupplierQuoteRequests = (params) => http.get('/supplier/quote-requests', { params })
export const fetchSupplierQuoteRequest = (id) => http.get(`/supplier/quote-requests/${id}`)
export const fetchSupplierQuoteRequestFulfillment = (id) =>
  http.get(`/supplier/quote-requests/${id}/fulfillment`)
export const submitSupplierQuote = (id, data) => {
  if (data instanceof FormData) {
    return http.post(`/supplier/quote-requests/${id}/quotes`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }
  return http.post(`/supplier/quote-requests/${id}/quotes`, data)
}
export const updateSupplierQuote = (id, data) => {
  if (data instanceof FormData) {
    return http.patch(`/supplier/quote-requests/${id}/quotes`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }
  return http.patch(`/supplier/quote-requests/${id}/quotes`, data)
}
export const uploadSupplierQuoteAttachment = (quoteId, formData) =>
  http.post(`/supplier/quotes/${quoteId}/attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const deleteSupplierQuoteAttachment = (quoteId, fileId) =>
  http.delete(`/supplier/quotes/${quoteId}/attachments/${fileId}`)

export const updateFactoryProfile = (data) => http.patch('/factory/profile', data)
export const uploadSupplierProfileAttachment = (formData) =>
  http.post('/supplier/profile/attachments', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const deleteSupplierProfileAttachment = (attachmentId) =>
  http.delete('/supplier/profile/attachments', { data: { attachment_id: attachmentId } })

export const fetchMyProductionOrders = (params) => http.get('/member/production-orders', { params })
export const fetchMyProductionOrder = (id) => http.get(`/member/production-orders/${id}`)
export const fetchSupplierProductionOrders = (params) => http.get('/supplier/production-orders', { params })
export const confirmProductionOrder = (id) => http.post(`/supplier/production-orders/${id}/confirm`)
export const rejectProductionOrder = (id) => http.post(`/supplier/production-orders/${id}/reject`)

// MY PAGE 概览
export const fetchMemberDashboard = () => http.get('/member/dashboard')
export const updateProfile = (data) => http.patch('/member/profile', data)
export const updateProfileMultipart = (formData) =>
  http.patch('/member/profile', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const fetchMemberTodos = () => http.get('/member/todos')
export const fetchMemberFiles = () => http.get('/member/files')
export const fetchMyProjectFiles = (projectId) => http.get(`/member/projects/${projectId}/files`)
export const uploadSupplierProjectFile = (projectId, formData) =>
  http.post(`/supplier/projects/${projectId}/files`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const downloadDefectReportTemplate = () =>
  http.get('/member/defect-report-template', { responseType: 'blob' })
export const downloadSupplierDefectReportTemplate = () =>
  http.get('/supplier/defect-report-template', { responseType: 'blob' })
export const downloadRfqQuotePdf = (id) =>
  http.get(`/member/rfqs/${id}/quote-pdf`, { responseType: 'blob' })

// 简单报价
export const fetchSimpleQuotes = (params) => http.get('/member/simple-quotes', { params })
export const fetchSimpleQuote = (id) => http.get(`/member/simple-quotes/${id}`)
export const createSimpleQuote = (data) => http.post('/member/simple-quotes', data)
export const fetchFefcoCatalog = () => http.get('/packaging/fefco-catalog')
export const convertSimpleQuote = (id, data) => http.post(`/member/simple-quotes/${id}/convert`, data)
export const previewSimpleQuote = (data) => http.post('/member/simple-quotes/preview', data)
export const fetchPrint3dOptions = () => http.get('/member/simple-quotes/print3d/options')
export const createPrint3dSliceJob = (formData) =>
  http.post('/member/simple-quotes/print3d/slice-jobs', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
export const fetchPrint3dSliceJob = (id) =>
  http.get(`/member/simple-quotes/print3d/slice-jobs/${id}`)
// 几何/OCR 解析为同步计算，耗时可达数十秒，需覆盖后端解析超时（STP 20s / OCR 25s）
export const stpParse = (formData) =>
  http.post('/member/simple-quotes/parse-stp', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
export const drawingParse = (formData) =>
  http.post('/member/simple-quotes/parse-drawing', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
export const shippingEstimate = (data) => http.post('/member/simple-quotes/shipping-estimate', data)

export const fetchNdaTemplate = () => http.get('/member/nda/template')
export const fetchNdaList = (params) => http.get('/member/nda', { params })
export const signNda = (data) => http.post('/member/nda/sign', data)

// 项目
export const fetchMyProjects = (params) => http.get('/member/projects', { params })
export const fetchMyProject = (id) => http.get(`/member/projects/${id}`)
export const toggleProjectTodo = (projectId, todoId) =>
  http.post(`/member/projects/${projectId}/todos/${todoId}/toggle`)
export const fetchSupplierProjects = (params) => http.get('/supplier/projects', { params })
export const fetchSupplierProject = (id) => http.get(`/supplier/projects/${id}`)
export const addSupplierProjectUpdate = (id, data) => http.post(`/supplier/projects/${id}/updates`, data)
export const updateSupplierProjectStage = (id, stageId, data) =>
  http.patch(`/supplier/projects/${id}/stages/${stageId}`, data)
export const addSupplierProjectIssue = (id, data) => http.post(`/supplier/projects/${id}/issues`, data)

// 合同 / 付款
export const fetchMyContracts = (params) => http.get('/member/contracts', { params })
export const signContract = (id) => http.post(`/member/contracts/${id}/sign`)
export const fetchMyPayments = (params) => http.get('/member/payments', { params })
export const fetchPayment = (id) => http.get(`/member/payments/${id}`)
export const uploadPaymentProof = (id, formData) =>
  http.post(`/member/payments/${id}/proof`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const confirmSupplierPayment = (id) => http.post(`/supplier/payments/${id}/confirm`)

// 供应商合同
export const fetchSupplierContracts = (params) => http.get('/supplier/contracts', { params })
export const fetchSupplierContract = (id) => http.get(`/supplier/contracts/${id}`)

// 积分
export const fetchPointWallet = () => http.get('/member/points/wallet')
export const fetchPointTransactions = (params) => http.get('/member/points/transactions', { params })
export const createRecharge = (formData) =>
  http.post('/member/points/recharge', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const fetchRecharges = (params) => http.get('/member/points/recharge', { params })

// 通知
export const fetchNotifications = (params) => http.get('/member/notifications', { params })
export const fetchUnreadCount = () => http.get('/member/notifications/unread-count')
export const markNotificationRead = (id) => http.post(`/member/notifications/${id}/read`)
export const markAllNotificationsRead = () => http.post('/member/notifications/read-all')
export const fetchSupplierNotifications = (params) => http.get('/supplier/notifications', { params })
export const fetchSupplierUnreadCount = () => http.get('/supplier/notifications/unread-count')
export const markSupplierNotificationRead = (id) => http.post(`/supplier/notifications/${id}/read`)
export const markAllSupplierNotificationsRead = () => http.post('/supplier/notifications/read-all')

export const fetchCart = () => http.get('/member/cart')
export const addToCart = (data) => http.post('/member/cart/items', data)
export const updateCartItem = (id, data) => http.patch(`/member/cart/items/${id}`, data)
export const removeCartItem = (id) => http.delete(`/member/cart/items/${id}`)
export const createOrder = (data) => http.post('/member/orders', data)
export const fetchOrders = (params) => http.get('/member/orders', { params })
export const fetchOrder = (id) => http.get(`/member/orders/${id}`)
