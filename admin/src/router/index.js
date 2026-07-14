import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AdminLayout from '../layouts/AdminLayout.vue'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
  {
    path: '/',
    component: AdminLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
      { path: 'service-categories', name: 'service-categories', component: () => import('../views/ServiceCategoriesView.vue') },
      { path: 'factories', name: 'factories', component: () => import('../views/FactoriesView.vue') },
      { path: 'suppliers', name: 'suppliers', component: () => import('../views/SuppliersView.vue') },
      { path: 'rfqs', name: 'rfqs', component: () => import('../views/RfqsView.vue') },
      { path: 'quote-params', name: 'quote-params', component: () => import('../views/QuoteParamsView.vue') },
      { path: 'print3d-config', name: 'print3d-config', component: () => import('../views/Print3dConfigView.vue') },
      { path: 'quote-tables', name: 'quote-tables', component: () => import('../views/QuoteTablesView.vue') },
      { path: 'dieline-templates', name: 'dieline-templates', component: () => import('../views/DielineTemplatesView.vue') },
      { path: 'points', name: 'points', component: () => import('../views/PointsView.vue') },
      { path: 'members', name: 'members', component: () => import('../views/MembersView.vue') },
      { path: 'projects', name: 'projects', component: () => import('../views/ProjectsView.vue') },
      { path: 'contracts', name: 'contracts', component: () => import('../views/ContractsView.vue') },
      { path: 'payments', name: 'payments', component: () => import('../views/PaymentsView.vue') },
      { path: 'production-orders', name: 'production-orders', component: () => import('../views/ProductionOrdersView.vue') },
      { path: 'categories', name: 'categories', component: () => import('../views/CategoriesView.vue') },
      { path: 'products', name: 'products', component: () => import('../views/ProductsView.vue') },
      { path: 'orders', name: 'orders', component: () => import('../views/OrdersView.vue') },
      { path: 'inquiries', name: 'inquiries', component: () => import('../views/InquiriesView.vue') },
      { path: 'cases', name: 'cases', component: () => import('../views/CasesView.vue') },
      { path: 'news', name: 'news', component: () => import('../views/NewsView.vue') },
      { path: 'faqs', name: 'faqs', component: () => import('../views/FaqsView.vue') },
      { path: 'downloads', name: 'downloads', component: () => import('../views/DownloadsView.vue') },
      { path: 'content-pages', name: 'content-pages', component: () => import('../views/ContentPagesView.vue') },
      { path: 'navigation', name: 'navigation', component: () => import('../views/NavigationView.vue') },
      { path: 'admin-users', name: 'admin-users', component: () => import('../views/AdminUsersView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.VITE_ADMIN_BASE_PATH || '/admin'),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) return { name: 'login' }
  if (to.name === 'login' && auth.isLoggedIn) return { name: 'dashboard' }
})

export default router
