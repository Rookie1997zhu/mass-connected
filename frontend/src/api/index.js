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

export const createRfq = (data) => http.post('/member/rfqs', data)
export const uploadRfqAttachment = (id, formData) =>
  http.post(`/member/rfqs/${id}/attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const fetchMyRfqs = (params) => http.get('/member/rfqs', { params })
export const fetchMyRfq = (id) => http.get(`/member/rfqs/${id}`)
export const acceptQuote = (rfqId, quoteId) =>
  http.post(`/member/rfqs/${rfqId}/quotes/${quoteId}/accept`)

export const fetchDemandHall = (params) => http.get('/factory/rfqs', { params })
export const fetchDemandDetail = (id) => http.get(`/factory/rfqs/${id}`)
export const submitFactoryQuote = (rfqId, data) => http.post(`/factory/rfqs/${rfqId}/quotes`, data)
export const fetchMyFactoryQuotes = (params) => http.get('/factory/quotes', { params })

export const fetchCart = () => http.get('/member/cart')
export const addToCart = (data) => http.post('/member/cart/items', data)
export const updateCartItem = (id, data) => http.patch(`/member/cart/items/${id}`, data)
export const removeCartItem = (id) => http.delete(`/member/cart/items/${id}`)
export const createOrder = (data) => http.post('/member/orders', data)
export const fetchOrders = (params) => http.get('/member/orders', { params })
export const fetchOrder = (id) => http.get(`/member/orders/${id}`)
