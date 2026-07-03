import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', name: 'home', component: () => import('../views/HomeView.vue') },
      { path: 'about/:section?', name: 'about', component: () => import('../views/AboutView.vue') },
      { path: 'capabilities/:section?', name: 'capabilities', component: () => import('../views/CapabilitiesView.vue') },
      { path: 'oem-odm', name: 'oem-odm', component: () => import('../views/OemOdmView.vue') },
      { path: 'cases', name: 'cases', component: () => import('../views/CasesView.vue') },
      { path: 'cases/:id', name: 'case-detail', component: () => import('../views/CaseDetailView.vue') },
      { path: 'news', name: 'news', component: () => import('../views/NewsView.vue') },
      { path: 'news/:id', name: 'news-detail', component: () => import('../views/NewsDetailView.vue') },
      { path: 'support/:tab?', name: 'support', component: () => import('../views/SupportView.vue') },
      { path: 'contact', name: 'contact', component: () => import('../views/ContactView.vue') },
      { path: 'login', name: 'login', component: () => import('../views/LoginView.vue') },
      { path: 'register', name: 'register', component: () => import('../views/RegisterView.vue') },
      { path: 'partners', name: 'partners', component: () => import('../views/factory/PartnerApplyView.vue') },
      {
        path: 'my',
        name: 'my-page',
        component: () => import('../views/mypage/MyPageView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'my/projects/:id',
        name: 'my-project-detail',
        component: () => import('../views/mypage/MyProjectDetailView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'simple-quote',
        name: 'simple-quote',
        component: () => import('../views/quote/SimpleQuoteView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'rfq/new',
        name: 'rfq-create',
        component: () => import('../views/rfq/RfqCreateView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'my/rfqs',
        name: 'my-rfqs',
        component: () => import('../views/rfq/MyRfqListView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'my/rfqs/:id',
        name: 'my-rfq-detail',
        component: () => import('../views/rfq/MyRfqDetailView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'my/production-orders',
        name: 'my-production-orders',
        component: () => import('../views/rfq/MyProductionOrdersView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'my/production-orders/:id',
        name: 'my-production-order-detail',
        component: () => import('../views/rfq/MyProductionOrderDetailView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'demand-hall',
        name: 'demand-hall',
        component: () => import('../views/factory/DemandHallView.vue'),
      },
      {
        path: 'demand-hall/:id',
        name: 'demand-detail',
        component: () => import('../views/factory/DemandDetailView.vue'),
      },
      {
        path: 'factory/quotes',
        name: 'factory-quotes',
        component: () => import('../views/factory/MyQuotesView.vue'),
        meta: { requiresAuth: true, requiresSupplier: true },
      },
      {
        path: 'supplier/quote-requests',
        name: 'supplier-quote-requests',
        component: () => import('../views/supplier/QuoteRequestsView.vue'),
        meta: { requiresAuth: true, requiresSupplier: true },
      },
      {
        path: 'supplier/quote-requests/:id',
        name: 'supplier-quote-request-detail',
        component: () => import('../views/supplier/QuoteRequestDetailView.vue'),
        meta: { requiresAuth: true, requiresSupplier: true },
      },
      {
        path: 'supplier/orders',
        name: 'supplier-orders',
        component: () => import('../views/supplier/SupplierOrdersView.vue'),
        meta: { requiresAuth: true, requiresSupplier: true },
      },
      {
        path: 'supplier/projects',
        name: 'supplier-projects',
        component: () => import('../views/supplier/SupplierProjectsView.vue'),
        meta: { requiresAuth: true, requiresSupplier: true },
      },
      {
        path: 'supplier/projects/:id',
        name: 'supplier-project-detail',
        component: () => import('../views/supplier/SupplierProjectDetailView.vue'),
        meta: { requiresAuth: true, requiresSupplier: true },
      },
      { path: 'shop', name: 'shop', component: () => import('../views/shop/ShopListView.vue') },
      { path: 'shop/products/:id', name: 'product-detail', component: () => import('../views/shop/ProductDetailView.vue') },
      {
        path: 'shop/cart',
        name: 'cart',
        component: () => import('../views/shop/CartView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'shop/checkout',
        name: 'checkout',
        component: () => import('../views/shop/CheckoutView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'my/orders',
        name: 'my-orders',
        component: () => import('../views/shop/OrdersView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
      {
        path: 'my/orders/:id',
        name: 'my-order-detail',
        component: () => import('../views/shop/OrderDetailView.vue'),
        meta: { requiresAuth: true, requiresBuyer: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (!to.meta.requiresAuth) return
  const auth = useAuthStore()
  if (!auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresSupplier && !auth.isSupplier) {
    return { name: 'my-rfqs' }
  }
  if (to.meta.requiresBuyer && !auth.isBuyer) {
    return { name: 'login' }
  }
})

export default router
