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
        path: 'rfq/new',
        name: 'rfq-create',
        component: () => import('../views/rfq/RfqCreateView.vue'),
        meta: { requiresAuth: true, roles: ['member'] },
      },
      {
        path: 'my/rfqs',
        name: 'my-rfqs',
        component: () => import('../views/rfq/MyRfqListView.vue'),
        meta: { requiresAuth: true, roles: ['member'] },
      },
      {
        path: 'my/rfqs/:id',
        name: 'my-rfq-detail',
        component: () => import('../views/rfq/MyRfqDetailView.vue'),
        meta: { requiresAuth: true, roles: ['member'] },
      },
      {
        path: 'demand-hall',
        name: 'demand-hall',
        component: () => import('../views/factory/DemandHallView.vue'),
        meta: { requiresAuth: true, roles: ['factory'] },
      },
      {
        path: 'demand-hall/:id',
        name: 'demand-detail',
        component: () => import('../views/factory/DemandDetailView.vue'),
        meta: { requiresAuth: true, roles: ['factory'] },
      },
      {
        path: 'factory/quotes',
        name: 'factory-quotes',
        component: () => import('../views/factory/MyQuotesView.vue'),
        meta: { requiresAuth: true, roles: ['factory'] },
      },
      { path: 'shop', name: 'shop', component: () => import('../views/shop/ShopListView.vue') },
      { path: 'shop/products/:id', name: 'product-detail', component: () => import('../views/shop/ProductDetailView.vue') },
      {
        path: 'shop/cart',
        name: 'cart',
        component: () => import('../views/shop/CartView.vue'),
        meta: { requiresAuth: true, roles: ['member'] },
      },
      {
        path: 'shop/checkout',
        name: 'checkout',
        component: () => import('../views/shop/CheckoutView.vue'),
        meta: { requiresAuth: true, roles: ['member'] },
      },
      {
        path: 'my/orders',
        name: 'my-orders',
        component: () => import('../views/shop/OrdersView.vue'),
        meta: { requiresAuth: true, roles: ['member'] },
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
  const roles = to.meta.roles
  if (roles?.length && !roles.includes(auth.role)) {
    if (auth.isFactory) return { name: 'demand-hall' }
    if (auth.isMember) return { name: 'my-rfqs' }
    return { name: 'login' }
  }
})

export default router
