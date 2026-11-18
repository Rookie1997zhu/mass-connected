import http from './http'

export const fetchServiceCategories = () => http.get('/public/service-categories')
export const fetchCategories = () => http.get('/public/categories')
export const fetchProducts = (params) => http.get('/public/products', { params })
export const fetchProduct = (id) => http.get(`/public/products/${id}`)
export const fetchCases = (params) => http.get('/public/cases', { params })
export const fetchCase = (id) => http.get(`/public/cases/${id}`)
export const fetchNews = (params) => http.get('/public/news', { params })
export const fetchNewsItem = (id) => http.get(`/public/news/${id}`)
export const fetchBlogCategories = () => http.get('/public/blog/categories')
export const fetchBlogTags = () => http.get('/public/blog/tags')
export const fetchBlogPosts = (params) => http.get('/public/blog/posts', { params })
export const fetchBlogPost = (id) => http.get(`/public/blog/posts/${id}`)
export const fetchBlogComments = (id, params) => http.get(`/public/blog/posts/${id}/comments`, { params })
export const blogLikeCreate = (id) => http.put(`/blog/posts/${id}/like`)
export const blogLikeDelete = (id) => http.delete(`/blog/posts/${id}/like`)
export const blogCommentCreate = (id, data) => http.post(`/blog/posts/${id}/comments`, data)
export const blogCommentDelete = (id) => http.delete(`/blog/comments/${id}`)
export const fetchFaqs = () => http.get('/public/faqs')
export const fetchDownloads = (params) => http.get('/public/downloads', { params })
export const fetchContentPage = (pageKey) => http.get(`/public/content-pages/${pageKey}`)
export const fetchNavigation = () => http.get('/public/navigation')
export const submitInquiry = (data) => http.post('/public/inquiries', data)

export const memberRegister = (data) => http.post('/member/auth/register', data)
export const verifyEmailConfirm = (token) =>
  http.post('/member/auth/verify-email/confirm', { token })
export const verifyEmailResend = () => http.post('/member/auth/verify-email/resend', {})
export const factoryRegister = (data) => http.post('/factory/auth/register', data)
export const memberLogin = (data) => http.post('/member/auth/login', data)
export const memberLogout = () => http.post('/member/auth/logout', {})
export const fetchProfile = () => http.get('/member/profile')
export const fetchFactoryProfile = () => http.get('/factory/profile')
export const fetchPartners = (params) => http.get('/public/partners', { params })
export const fetchPartner = (id) => http.get(`/public/partners/${id}`)

export const createRfq = (data, config = {}) => http.post('/member/rfqs', data, config)
export const uploadRfqAttachment = (id, formData) =>
  http.post(`/member/rfqs/${id}/attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const fetchMyRfqs = (params) => http.get('/member/rfqs', { params })
export const fetchMyRfq = (id) => http.get(`/member/rfqs/${id}`)
export const fetchMyRfqFulfillment = (id) => http.get(`/member/rfqs/${id}/fulfillment`)
export const updateMyRfq = (id, data) => http.patch(`/member/rfqs/${id}`, data)
export const acceptQuote = (rfqId, quoteId, { idempotencyKey } = {}) =>
  http.post(
    `/member/rfqs/${rfqId}/quotes/${quoteId}/accept`,
    {},
    idempotencyKey ? { headers: { 'Idempotency-Key': idempotencyKey } } : undefined,
  )
export const fetchMyQuoteDetail = (rfqId, quoteId) =>
  http.get(`/member/rfqs/${rfqId}/quotes/${quoteId}`)
export const fetchQuoteCounterOffers = (rfqId, quoteId) =>
  http.get(`/member/rfqs/${rfqId}/quotes/${quoteId}/counter-offers`)
export const createQuoteCounterOffer = (rfqId, quoteId, data) =>
  http.post(`/member/rfqs/${rfqId}/quotes/${quoteId}/counter-offers`, data)
export const withdrawQuoteCounterOffer = (rfqId, counterOfferId) =>
  http.post(`/member/rfqs/${rfqId}/counter-offers/${counterOfferId}/withdraw`)
export const fetchSupplierQuoteCounterOffers = (quoteId) =>
  http.get(`/supplier/quotes/${quoteId}/counter-offers`)
export const acceptSupplierCounterOffer = (counterOfferId) =>
  http.post(`/supplier/counter-offers/${counterOfferId}/accept`)
export const rejectSupplierCounterOffer = (counterOfferId) =>
  http.post(`/supplier/counter-offers/${counterOfferId}/reject`)

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
export const fetchBuyerWorkbench = () => http.get('/member/workbench')
export const fetchSupplierDashboard = () => http.get('/supplier/dashboard')
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
export const deleteSupplierProjectFile = (projectId, fileId) =>
  http.delete(`/supplier/projects/${projectId}/files/${fileId}`)
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
export const purchaseDielineTemplate = (data) => http.post('/member/dieline-purchases', data)
export const fetchDielinePurchases = (params) => http.get('/member/dieline-purchases', { params })
export const downloadDielineTemplate = (code, params) =>
  http.get(`/member/dieline-templates/${encodeURIComponent(code)}/download`, {
    params,
    responseType: 'blob',
  })
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
// 解析提交仅入队，短超时即可；结果经 fetchParseJob 轮询
export const stpParse = (formData) =>
  http.post('/member/simple-quotes/parse-stp', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
export const drawingParse = (formData) =>
  http.post('/member/simple-quotes/parse-drawing', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
export const fetchParseJob = (id) =>
  http.get(`/member/simple-quotes/parse-jobs/${id}`, { timeout: 15000 })
export const shippingEstimate = (data) => http.post('/member/simple-quotes/shipping-estimate', data)

export const fetchNdaTemplate = () => http.get('/member/nda/template')
export const fetchNdaList = (params) => http.get('/member/nda', { params })
export const signNda = (data) => http.post('/member/nda/sign', data)

// 项目
export const fetchMyProjects = (params) => http.get('/member/projects', { params })
export const fetchMyProject = (id) => http.get(`/member/projects/${id}`)
export const toggleProjectTodo = (projectId, todoId) =>
  http.post(`/member/projects/${projectId}/todos/${todoId}/toggle`)
export const translateMemberProjectText = (id, data) =>
  http.post(`/member/projects/${id}/translate`, data, { timeout: 45000 })
export const translateMemberProjectFile = (projectId, fileId, data) =>
  http.post(`/member/projects/${projectId}/files/${fileId}/translate`, data, { timeout: 120000 })
export const translateMemberRfqText = (id, data) =>
  http.post(`/member/rfqs/${id}/translate`, data, { timeout: 45000 })
export const translateMemberRfqFile = (rfqId, fileId, data) =>
  http.post(`/member/rfqs/${rfqId}/attachments/${fileId}/translate`, data, { timeout: 120000 })
export const translateMemberQuoteText = (quoteId, data) =>
  http.post(`/member/quotes/${quoteId}/translate`, data, { timeout: 45000 })
export const translateMemberQuoteFile = (quoteId, fileId, data) =>
  http.post(`/member/quotes/${quoteId}/attachments/${fileId}/translate`, data, { timeout: 120000 })
export const fetchSupplierProjects = (params) => http.get('/supplier/projects', { params })
export const fetchSupplierProject = (id) => http.get(`/supplier/projects/${id}`)
export const addSupplierProjectUpdate = (id, data) => http.post(`/supplier/projects/${id}/updates`, data)
export const updateSupplierProjectStage = (id, stageId, data) =>
  http.patch(`/supplier/projects/${id}/stages/${stageId}`, data)
export const addSupplierProjectIssue = (id, data) => http.post(`/supplier/projects/${id}/issues`, data)
export const createSupplierProjectTodo = (id, data) =>
  http.post(`/supplier/projects/${id}/todos`, data)
export const toggleSupplierProjectTodo = (projectId, todoId) =>
  http.post(`/supplier/projects/${projectId}/todos/${todoId}/toggle`)
export const translateSupplierProjectText = (id, data) =>
  http.post(`/supplier/projects/${id}/translate`, data, { timeout: 45000 })
export const translateSupplierProjectFile = (projectId, fileId, data) =>
  http.post(`/supplier/projects/${projectId}/files/${fileId}/translate`, data, { timeout: 120000 })
export const translateSupplierQuoteRequestText = (id, data) =>
  http.post(`/supplier/quote-requests/${id}/translate`, data, { timeout: 45000 })
export const translateSupplierRfqFile = (quoteRequestId, fileId, data) =>
  http.post(
    `/supplier/quote-requests/${quoteRequestId}/rfq-attachments/${fileId}/translate`,
    data,
    { timeout: 120000 },
  )
export const translateSupplierQuoteText = (quoteId, data) =>
  http.post(`/supplier/quotes/${quoteId}/translate`, data, { timeout: 45000 })
export const translateSupplierQuoteFile = (quoteId, fileId, data) =>
  http.post(`/supplier/quotes/${quoteId}/attachments/${fileId}/translate`, data, { timeout: 120000 })

// 合同 / 付款
export const fetchMyContracts = (params) => http.get('/member/contracts', { params })
export const signContract = (id, formData) =>
  http.post(`/member/contracts/${id}/sign`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
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

// 订阅权益
export const fetchPublicSubscriptionPlans = () => http.get('/public/subscription/plans')
export const fetchMemberEntitlements = () => http.get('/member/subscription/entitlements')
export const fetchMemberUsageLedgers = (params) =>
  http.get('/member/subscription/ledgers', { params })
export const createSubscriptionOrder = (formData) =>
  http.post('/member/subscription/orders', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const fetchMemberSubscriptionOrders = (params) =>
  http.get('/member/subscription/orders', { params })

// 通知
export const fetchNotifications = (params) => http.get('/member/notifications', { params })
export const fetchUnreadCount = () => http.get('/member/notifications/unread-count')
export const markNotificationRead = (id) => http.post(`/member/notifications/${id}/read`)
export const markAllNotificationsRead = () => http.post('/member/notifications/read-all')
export const fetchSupplierNotifications = (params) => http.get('/supplier/notifications', { params })
export const fetchSupplierUnreadCount = () => http.get('/supplier/notifications/unread-count')
export const markSupplierNotificationRead = (id) => http.post(`/supplier/notifications/${id}/read`)
export const markAllSupplierNotificationsRead = () => http.post('/supplier/notifications/read-all')

// 聊天
const chatBase = (role) => (role === 'supplier' ? '/supplier/chat' : '/member/chat')
export const fetchChatConversations = (role, params) =>
  http.get(`${chatBase(role)}/conversations`, { params })
export const openChatConversation = (role, quoteRequestId) =>
  http.post(`${chatBase(role)}/conversations`, { quote_request_id: quoteRequestId })
export const fetchChatMessages = (role, conversationId, params) =>
  http.get(`${chatBase(role)}/conversations/${conversationId}/messages`, { params })
export const sendChatMessage = (role, conversationId, body) =>
  http.post(`${chatBase(role)}/conversations/${conversationId}/messages`, { body })
export const uploadChatAttachment = (role, conversationId, formData) =>
  http.post(`${chatBase(role)}/conversations/${conversationId}/attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const markChatConversationRead = (role, conversationId) =>
  http.post(`${chatBase(role)}/conversations/${conversationId}/read`)
export const openChatDispute = (role, conversationId, reason = '') =>
  http.post(`${chatBase(role)}/conversations/${conversationId}/dispute/open`, { reason })
export const resolveChatDispute = (role, conversationId) =>
  http.post(`${chatBase(role)}/conversations/${conversationId}/dispute/resolve`)
export const fetchChatUnreadCount = (role) => http.get(`${chatBase(role)}/unread-count`)
export const createChatWsTicket = (role) => http.post(`${chatBase(role)}/ws-ticket`, {})
export const translateChatMessage = (role, conversationId, messageId, data) =>
  http.post(
    `${chatBase(role)}/conversations/${conversationId}/messages/${messageId}/translate`,
    data,
    { timeout: 45000 },
  )
// 翻译任务短轮询：缓存未命中时由 translateChatMessage 返回 job_id
export const fetchChatTranslateJob = (role, jobId) =>
  http.get(`${chatBase(role)}/translate-jobs/${jobId}`, { timeout: 15000 })
export const fetchRemindableOrders = (role, conversationId, params) =>
  http.get(`${chatBase(role)}/conversations/${conversationId}/remindable-orders`, { params })
export const sendChatOrderReminder = (role, conversationId, data) =>
  http.post(`${chatBase(role)}/conversations/${conversationId}/messages/order-reminder`, data)

export const fetchCart = () => http.get('/member/cart')
export const addToCart = (data) => http.post('/member/cart/items', data)
export const updateCartItem = (id, data) => http.patch(`/member/cart/items/${id}`, data)
export const removeCartItem = (id) => http.delete(`/member/cart/items/${id}`)
export const createOrder = (data) => http.post('/member/orders', data)
export const fetchOrders = (params) => http.get('/member/orders', { params })
export const fetchOrder = (id) => http.get(`/member/orders/${id}`)
