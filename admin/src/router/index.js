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
      { path: '', name: 'dashboard', meta: { titleKey: 'nav.dashboard' }, component: () => import('../views/DashboardView.vue') },
      { path: 'ops-queue', name: 'ops-queue', meta: { titleKey: 'nav.opsQueue' }, component: () => import('../views/OpsQueueView.vue') },
      { path: 'service-categories', name: 'service-categories', meta: { titleKey: 'nav.serviceCategories' }, component: () => import('../views/ServiceCategoriesView.vue') },
      { path: 'factories', name: 'factories', meta: { titleKey: 'nav.factories' }, component: () => import('../views/FactoriesView.vue') },
      { path: 'suppliers', name: 'suppliers', meta: { titleKey: 'nav.suppliers' }, component: () => import('../views/SuppliersView.vue') },
      { path: 'rfqs', name: 'rfqs', meta: { titleKey: 'nav.rfqs' }, component: () => import('../views/RfqsView.vue') },
      { path: 'quote-params', name: 'quote-params', meta: { titleKey: 'nav.quoteParams' }, component: () => import('../views/QuoteParamsView.vue') },
      { path: 'print3d-config', name: 'print3d-config', meta: { titleKey: 'nav.print3dConfig' }, component: () => import('../views/Print3dConfigView.vue') },
      { path: 'quote-tables', name: 'quote-tables', meta: { titleKey: 'nav.quoteTables' }, component: () => import('../views/QuoteTablesView.vue') },
      { path: 'dieline-templates', name: 'dieline-templates', meta: { titleKey: 'nav.dielineTemplates' }, component: () => import('../views/DielineTemplatesView.vue') },
      { path: 'points', name: 'points', meta: { titleKey: 'nav.points' }, component: () => import('../views/PointsView.vue') },
      { path: 'members', name: 'members', meta: { titleKey: 'nav.members' }, component: () => import('../views/MembersView.vue') },
      { path: 'projects', name: 'projects', meta: { titleKey: 'nav.projects' }, component: () => import('../views/ProjectsView.vue') },
      { path: 'contracts', name: 'contracts', meta: { titleKey: 'nav.contracts' }, component: () => import('../views/ContractsView.vue') },
      { path: 'payments', name: 'payments', meta: { titleKey: 'nav.payments' }, component: () => import('../views/PaymentsView.vue') },
      { path: 'production-orders', name: 'production-orders', meta: { titleKey: 'nav.productionOrders' }, component: () => import('../views/ProductionOrdersView.vue') },
      { path: 'chat-disputes', name: 'chat-disputes', meta: { titleKey: 'nav.chatDisputes' }, component: () => import('../views/ChatDisputesView.vue') },
      { path: 'categories', name: 'categories', meta: { titleKey: 'nav.categories' }, component: () => import('../views/CategoriesView.vue') },
      { path: 'products', name: 'products', meta: { titleKey: 'nav.products' }, component: () => import('../views/ProductsView.vue') },
      { path: 'orders', name: 'orders', meta: { titleKey: 'nav.orders' }, component: () => import('../views/OrdersView.vue') },
      { path: 'inquiries', name: 'inquiries', meta: { titleKey: 'nav.inquiries' }, component: () => import('../views/InquiriesView.vue') },
      { path: 'cases', name: 'cases', meta: { titleKey: 'nav.cases' }, component: () => import('../views/CasesView.vue') },
      { path: 'news', name: 'news', meta: { titleKey: 'nav.news' }, component: () => import('../views/NewsView.vue') },
      { path: 'blog/posts', name: 'blog-posts', meta: { titleKey: 'nav.blogPosts' }, component: () => import('../views/BlogPostsView.vue') },
      { path: 'blog/categories', name: 'blog-categories', meta: { titleKey: 'nav.blogCategories' }, component: () => import('../views/BlogCategoriesView.vue') },
      { path: 'blog/comments', name: 'blog-comments', meta: { titleKey: 'nav.blogComments' }, component: () => import('../views/BlogCommentsView.vue') },
      { path: 'faqs', name: 'faqs', meta: { titleKey: 'nav.faqs' }, component: () => import('../views/FaqsView.vue') },
      { path: 'downloads', name: 'downloads', meta: { titleKey: 'nav.downloads' }, component: () => import('../views/DownloadsView.vue') },
      { path: 'content-pages', name: 'content-pages', meta: { titleKey: 'nav.pages' }, component: () => import('../views/ContentPagesView.vue') },
      { path: 'navigation', name: 'navigation', meta: { titleKey: 'nav.navigation' }, component: () => import('../views/NavigationView.vue') },
      { path: 'admin-users', name: 'admin-users', meta: { titleKey: 'nav.admins' }, component: () => import('../views/AdminUsersView.vue') },
      { path: 'ops', redirect: { name: 'ops-runtime' } },
      { path: 'ops/runtime', name: 'ops-runtime', meta: { titleKey: 'nav.opsRuntime' }, component: () => import('../views/OpsRuntimeView.vue') },
      { path: 'ops/storage', name: 'ops-storage', meta: { titleKey: 'nav.opsStorage' }, component: () => import('../views/OpsStorageView.vue') },
      { path: 'ops/behavior', name: 'ops-behavior', meta: { titleKey: 'nav.opsBehavior' }, component: () => import('../views/OpsBehaviorView.vue') },
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
