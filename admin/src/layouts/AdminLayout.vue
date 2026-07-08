<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import {
  fetchAdminNotifications,
  fetchAdminUnreadCount,
  markAdminNotificationRead,
  markAllAdminNotificationsRead,
} from '../api'
import { useAuthStore } from '../stores/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()
const router = useRouter()

const unreadCount = ref(0)
const notifications = ref([])
const notifOpen = ref(false)
const notifLoading = ref(false)

const logout = () => {
  auth.logout()
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
      <el-menu router default-active="/">
        <el-menu-item index="/">{{ t('nav.dashboard') }}</el-menu-item>
        <el-menu-item index="/service-categories">{{ t('nav.serviceCategories') }}</el-menu-item>
        <el-menu-item index="/factories">{{ t('nav.factories') }}</el-menu-item>
        <el-menu-item index="/suppliers">{{ t('nav.suppliers') }}</el-menu-item>
        <el-menu-item index="/rfqs">{{ t('nav.rfqs') }}</el-menu-item>
        <el-menu-item index="/quote-params">{{ t('nav.quoteParams') }}</el-menu-item>
        <el-menu-item index="/quote-tables">{{ t('nav.quoteTables') }}</el-menu-item>
        <el-menu-item index="/dieline-templates">{{ t('nav.dielineTemplates') }}</el-menu-item>
        <el-menu-item index="/points">{{ t('nav.points') }}</el-menu-item>
        <el-menu-item index="/members">{{ t('nav.members') }}</el-menu-item>
        <el-menu-item index="/projects">{{ t('nav.projects') }}</el-menu-item>
        <el-menu-item index="/contracts">{{ t('nav.contracts') }}</el-menu-item>
        <el-menu-item index="/payments">{{ t('nav.payments') }}</el-menu-item>
        <el-menu-item index="/production-orders">{{ t('nav.productionOrders') }}</el-menu-item>
        <el-menu-item index="/categories">{{ t('nav.categories') }}</el-menu-item>
        <el-menu-item index="/products">{{ t('nav.products') }}</el-menu-item>
        <el-menu-item index="/orders">{{ t('nav.orders') }}</el-menu-item>
        <el-menu-item index="/inquiries">{{ t('nav.inquiries') }}</el-menu-item>
        <el-menu-item index="/cases">{{ t('nav.cases') }}</el-menu-item>
        <el-menu-item index="/news">{{ t('nav.news') }}</el-menu-item>
        <el-menu-item index="/faqs">{{ t('nav.faqs') }}</el-menu-item>
        <el-menu-item index="/downloads">{{ t('nav.downloads') }}</el-menu-item>
        <el-menu-item index="/content-pages">{{ t('nav.pages') }}</el-menu-item>
        <el-menu-item index="/navigation">{{ t('nav.navigation') }}</el-menu-item>
        <el-menu-item index="/admin-users">{{ t('nav.admins') }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <el-select :model-value="locale" class="locale-select" @change="setLocale">
          <el-option label="한국어" value="ko" />
          <el-option label="中文" value="zh" />
          <el-option label="English" value="en" />
        </el-select>
        <div class="header-right">
          <el-popover :visible="notifOpen" placement="bottom-end" :width="360" trigger="manual">
            <template #reference>
              <el-badge :value="unreadCount || undefined" :hidden="!unreadCount" class="notif-badge">
                <el-button circle @click="toggleNotifications">🔔</el-button>
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
.layout { min-height: 100vh; }
.aside { background: #111827; color: #fff; }
.brand { padding: 1rem; display: flex; align-items: center; }
.brand-logo { height: 2.75rem; width: auto; display: block; filter: brightness(0) invert(1); }
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e5e7eb;
  gap: 1rem;
}
.header-right { display: flex; align-items: center; gap: 1rem; }
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
