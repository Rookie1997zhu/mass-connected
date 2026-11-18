<script setup>
import { Bell } from '@element-plus/icons-vue'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterView, useRoute, useRouter } from 'vue-router'
import {
  fetchAdminNotifications,
  fetchAdminUnreadCount,
  markAdminNotificationRead,
  markAllAdminNotificationsRead,
} from '../api'
import { useAuthStore } from '../stores/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const isSuperAdmin = computed(() => auth.user?.role === 'super_admin')

const initialOpeneds = computed(() => {
  const path = route.path
  const opened = ['daily']
  if (['/members', '/factories', '/suppliers'].includes(path)) opened.push('partners')
  if ([
    '/service-categories',
    '/quote-params',
    '/print3d-config',
    '/quote-tables',
    '/dieline-templates',
    '/points',
  ].includes(path)) opened.push('quote')
  if (['/categories', '/products', '/orders'].includes(path)) opened.push('shop')
  if (
    ['/cases', '/news', '/faqs', '/downloads', '/content-pages', '/navigation'].includes(path)
    || path.startsWith('/blog')
  ) opened.push('content')
  if (path.startsWith('/blog')) opened.push('blog')
  if (path === '/admin-users' || path.startsWith('/ops')) opened.push('system')
  return opened
})

const pageTitle = computed(() => {
  const key = route.meta.titleKey
  return key ? t(key) : ''
})

const unreadCount = ref(0)
const notifications = ref([])
const notifOpen = ref(false)
const notifLoading = ref(false)

const logout = async () => {
  await auth.logout()
  router.push('/login')
}

const setLocale = (value) => {
  locale.value = value
  localStorage.setItem('admin_locale', value)
  document.title = t('app.title')
}

const loadUnreadCount = async () => {
  try {
    const res = await fetchAdminUnreadCount()
    unreadCount.value = res.data?.count ?? 0
  } catch {
    unreadCount.value = 0
  }
}

const loadNotifications = async () => {
  notifLoading.value = true
  try {
    const res = await fetchAdminNotifications({ page_size: 10 })
    notifications.value = res.data.items || []
  } catch {
    notifications.value = []
  } finally {
    notifLoading.value = false
  }
}

const toggleNotifications = async () => {
  notifOpen.value = !notifOpen.value
  if (notifOpen.value) await loadNotifications()
}

const onMarkRead = async (n) => {
  if (!n.is_read) {
    await markAdminNotificationRead(n.id)
    n.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }
}

const onMarkAllRead = async () => {
  await markAllAdminNotificationsRead()
  unreadCount.value = 0
  await loadNotifications()
}

onMounted(loadUnreadCount)
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="brand">
        <img src="/mass-connected-logo.png" alt="MASS CONNECTED" class="brand-logo" />
      </div>
      <el-menu
        router
        class="side-menu"
        background-color="#111827"
        text-color="#d1d5db"
        active-text-color="#ffffff"
        :default-active="route.path"
        :default-openeds="initialOpeneds"
      >
        <el-sub-menu index="daily">
          <template #title>{{ t('nav.groups.daily') }}</template>
          <el-menu-item index="/">{{ t('nav.dashboard') }}</el-menu-item>
          <el-menu-item index="/ops-queue">{{ t('nav.opsQueue') }}</el-menu-item>
          <el-menu-item index="/rfqs">{{ t('nav.rfqs') }}</el-menu-item>
          <el-menu-item index="/inquiries">{{ t('nav.inquiries') }}</el-menu-item>
          <el-menu-item index="/projects">{{ t('nav.projects') }}</el-menu-item>
          <el-menu-item index="/contracts">{{ t('nav.contracts') }}</el-menu-item>
          <el-menu-item index="/payments">{{ t('nav.payments') }}</el-menu-item>
          <el-menu-item index="/production-orders">{{ t('nav.productionOrders') }}</el-menu-item>
          <el-menu-item index="/chat-disputes">{{ t('nav.chatDisputes') }}</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="partners">
          <template #title>{{ t('nav.groups.partners') }}</template>
          <el-menu-item index="/members">{{ t('nav.members') }}</el-menu-item>
          <el-menu-item index="/factories">{{ t('nav.factories') }}</el-menu-item>
          <el-menu-item index="/suppliers">{{ t('nav.suppliers') }}</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="quote">
          <template #title>{{ t('nav.groups.quote') }}</template>
          <el-menu-item index="/service-categories">{{ t('nav.serviceCategories') }}</el-menu-item>
          <el-menu-item index="/quote-params">{{ t('nav.quoteParams') }}</el-menu-item>
          <el-menu-item index="/print3d-config">{{ t('nav.print3dConfig') }}</el-menu-item>
          <el-menu-item index="/quote-tables">{{ t('nav.quoteTables') }}</el-menu-item>
          <el-menu-item index="/dieline-templates">{{ t('nav.dielineTemplates') }}</el-menu-item>
          <el-menu-item index="/points">{{ t('nav.points') }}</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="shop">
          <template #title>{{ t('nav.groups.shop') }}</template>
          <el-menu-item index="/categories">{{ t('nav.categories') }}</el-menu-item>
          <el-menu-item index="/products">{{ t('nav.products') }}</el-menu-item>
          <el-menu-item index="/orders">{{ t('nav.orders') }}</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="content">
          <template #title>{{ t('nav.groups.content') }}</template>
          <el-menu-item index="/cases">{{ t('nav.cases') }}</el-menu-item>
          <el-menu-item index="/news">{{ t('nav.news') }}</el-menu-item>
          <el-sub-menu index="blog">
            <template #title>{{ t('nav.blog') }}</template>
            <el-menu-item index="/blog/posts">{{ t('nav.blogPosts') }}</el-menu-item>
            <el-menu-item index="/blog/categories">{{ t('nav.blogCategories') }}</el-menu-item>
            <el-menu-item index="/blog/comments">{{ t('nav.blogComments') }}</el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/faqs">{{ t('nav.faqs') }}</el-menu-item>
          <el-menu-item index="/downloads">{{ t('nav.downloads') }}</el-menu-item>
          <el-menu-item index="/content-pages">{{ t('nav.pages') }}</el-menu-item>
          <el-menu-item index="/navigation">{{ t('nav.navigation') }}</el-menu-item>
        </el-sub-menu>
        <el-sub-menu v-if="isSuperAdmin" index="system">
          <template #title>{{ t('nav.groups.system') }}</template>
          <el-menu-item index="/admin-users">{{ t('nav.admins') }}</el-menu-item>
          <el-menu-item index="/ops/runtime">{{ t('nav.opsRuntime') }}</el-menu-item>
          <el-menu-item index="/ops/storage">{{ t('nav.opsStorage') }}</el-menu-item>
          <el-menu-item index="/ops/behavior">{{ t('nav.opsBehavior') }}</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    <el-container class="content">
      <el-header class="header">
        <h1 class="page-title">{{ pageTitle }}</h1>
        <div class="header-right">
          <el-select :model-value="locale" class="locale-select" @change="setLocale">
            <el-option label="한국어" value="ko" />
            <el-option label="中文" value="zh" />
            <el-option label="English" value="en" />
          </el-select>
          <el-popover :visible="notifOpen" placement="bottom-end" :width="360" trigger="manual">
            <template #reference>
              <el-badge :value="unreadCount || undefined" :hidden="!unreadCount" class="notif-badge">
                <el-button circle :aria-label="t('notifications.title')" @click="toggleNotifications">
                  <el-icon><Bell /></el-icon>
                </el-button>
              </el-badge>
            </template>
            <div class="notif-panel">
              <div class="notif-head">
                <strong>{{ t('notifications.title') }}</strong>
                <el-button link type="primary" @click="onMarkAllRead">{{ t('notifications.markAllRead') }}</el-button>
              </div>
              <div v-if="notifLoading" class="notif-empty">{{ t('common.loading') }}</div>
              <div v-else-if="!notifications.length" class="notif-empty">{{ t('notifications.empty') }}</div>
              <ul v-else class="notif-list">
                <li
                  v-for="n in notifications"
                  :key="n.id"
                  :class="{ unread: !n.is_read }"
                  @click="onMarkRead(n)"
                >
                  <strong>{{ n.title }}</strong>
                  <p>{{ n.content }}</p>
                  <small>{{ (n.created_at || '').slice(0, 16).replace('T', ' ') }}</small>
                </li>
              </ul>
            </div>
          </el-popover>
          <span>{{ auth.user?.email }}</span>
          <el-button @click="logout">{{ t('common.logout') }}</el-button>
        </div>
      </el-header>
      <el-main><RouterView /></el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  width: 100%;
  min-height: 100vh;
  font-size: 14px;
  color: #111827;
  background: #f3f4f6;
}
.aside {
  background: #111827;
  color: #fff;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.side-menu {
  flex: 1;
  overflow-y: auto;
  border-right: none;
  --el-menu-bg-color: #111827;
  --el-menu-text-color: #d1d5db;
  --el-menu-active-color: #ffffff;
  --el-menu-hover-bg-color: #1f2937;
  --el-menu-hover-text-color: #ffffff;
}
.side-menu :deep(.el-sub-menu__title) {
  font-size: 12px;
  letter-spacing: 0.04em;
  color: #9ca3af;
}
.side-menu :deep(.el-menu-item.is-active) {
  background-color: #1f2937;
  box-shadow: inset 3px 0 0 #7dd3fc;
}
.brand { padding: 1rem 1rem 0.5rem; display: flex; align-items: center; }
.brand-logo { height: 2.25rem; width: auto; display: block; filter: brightness(0) invert(1); }
.content { background: #f3f4f6; min-width: 0; }
.content :deep(.el-main) {
  background: #f3f4f6;
  font-size: 14px;
  color: #111827;
}
.content :deep(.el-main h1),
.content :deep(.el-main h2) {
  font-size: 1.25rem;
  line-height: 1.3;
  letter-spacing: 0;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.5rem;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  gap: 1rem;
}
.page-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: 0;
  color: #111827;
}
.header-right { display: flex; align-items: center; gap: 0.75rem; color: #4b5563; }
.locale-select { width: 120px; }
.notif-badge { margin-right: 0.25rem; }
.notif-panel { max-height: 360px; overflow: auto; }
.notif-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.notif-empty { color: #6b7280; font-size: 0.875rem; padding: 0.5rem 0; }
.notif-list { list-style: none; margin: 0; padding: 0; }
.notif-list li { padding: 0.5rem 0; border-bottom: 1px solid #f3f4f6; cursor: pointer; }
.notif-list li.unread { background: #f9fafb; }
.notif-list p { margin: 0.25rem 0; font-size: 0.875rem; color: #4b5563; }
.notif-list small { color: #9ca3af; font-size: 0.75rem; }
</style>

<style>
.layout .stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}
.layout .stat-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 1.25rem;
  border: none;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(17, 24, 39, 0.06);
  text-align: left;
}
.layout button.stat-card {
  cursor: pointer;
  font: inherit;
  color: inherit;
}
.layout button.stat-card:hover {
  box-shadow: 0 4px 12px rgba(17, 24, 39, 0.08);
}
.layout .stat-num { font-size: 1.75rem; font-weight: 700; color: #111827; }
.layout .stat-label { font-size: 0.85rem; color: #6b7280; margin-top: 0.35rem; }
.layout .stat-sub { font-size: 0.75rem; color: #9ca3af; margin-top: 0.25rem; }
.layout .panel {
  margin-top: 1rem;
  padding: 0.25rem 0.75rem 0.75rem;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(17, 24, 39, 0.06);
}
</style>
