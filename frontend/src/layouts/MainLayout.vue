<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView } from 'vue-router'
import NavDropdown from '../components/NavDropdown.vue'
import ChatPanel from '../components/ChatPanel.vue'
import {
  fetchChatUnreadCount,
  fetchNavigation,
  fetchSupplierUnreadCount,
  fetchUnreadCount,
} from '../api'
import { useAuthStore } from '../stores/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()
const menuOpen = ref(false)
const apiNavGroups = ref(null)
const unreadCount = ref(0)
const chatUnread = ref(0)
const chatOpen = ref(false)
const chatQuoteRequestId = ref(null)

const openChat = (quoteRequestId = null) => {
  chatQuoteRequestId.value = quoteRequestId
  chatOpen.value = true
}

const closeChat = () => {
  chatOpen.value = false
  chatQuoteRequestId.value = null
}

defineExpose({ openChat })

const setLocale = (value) => {
  locale.value = value
  localStorage.setItem('locale', value)
}

const closeMenu = () => {
  menuOpen.value = false
}

const currentYear = new Date().getFullYear()

const pickI18n = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || field.zh || Object.values(field)[0] || ''
}

const isExternal = (path) => /^https?:\/\//i.test(path || '')

const fallbackNavGroups = computed(() => [
  {
    label: t('nav.manufacturingQuote'),
    items: [
      { path: '/rfq/new', label: t('nav.postRequest') },
      { path: '/demand-hall', label: t('nav.findDemands') },
      { path: '/partners', label: t('nav.partnersDirectory') },
    ],
  },
  {
    label: t('nav.shop'),
    items: [{ path: '/shop', label: t('nav.shopCategories') }],
  },
  {
    label: t('nav.about'),
    items: [
      { path: '/capabilities', label: t('nav.capabilities') },
      { path: '/oem-odm', label: t('nav.oemOdm') },
      { path: '/cases', label: t('nav.cases') },
      { path: '/news', label: t('nav.news') },
      { path: '/support/faq', label: t('nav.support') },
      { path: '/contact', label: t('nav.contact') },
    ],
  },
])

const mapApiGroups = (groups) =>
  groups
    .map((group) => ({
      label: pickI18n(group.label),
      items: (group.children || []).map((child) => ({
        path: child.path,
        label: pickI18n(child.label),
        openInNewTab: child.open_in_new_tab,
      })),
    }))
    .filter((group) => group.items.length > 0)

const navGroups = computed(() => {
  if (apiNavGroups.value?.length) return mapApiGroups(apiNavGroups.value)
  return fallbackNavGroups.value
})

const loadNavigation = async () => {
  try {
    const res = await fetchNavigation()
    const items = res.data?.items || []
    apiNavGroups.value = items.length ? items : null
  } catch {
    apiNavGroups.value = null
  }
}

const loadUnreadCount = async () => {
  if (!auth.isLoggedIn) {
    unreadCount.value = 0
    return
  }
  try {
    const fetcher = auth.user?.role === 'factory' ? fetchSupplierUnreadCount : fetchUnreadCount
    const res = await fetcher()
    unreadCount.value = res.data?.count ?? res.data?.unread ?? 0
  } catch {
    unreadCount.value = 0
  }
}

const loadChatUnread = async () => {
  if (!auth.isLoggedIn || !(auth.isBuyer || auth.isSupplier)) {
    chatUnread.value = 0
    return
  }
  try {
    const role = auth.isSupplier ? 'supplier' : 'member'
    const res = await fetchChatUnreadCount(role)
    chatUnread.value = res.data?.count ?? 0
  } catch {
    chatUnread.value = 0
  }
}

onMounted(() => {
  loadNavigation()
  loadUnreadCount()
  loadChatUnread()
})

// provide openChat for child pages via window event
if (typeof window !== 'undefined') {
  window.__openPlatformChat = openChat
}
</script>

<template>
  <div class="layout">
    <header class="header">
      <div class="header-inner container">
        <RouterLink to="/" class="logo" @click="closeMenu">
          <img src="/mass-connected-logo.png" alt="MASS CONNECTED" class="logo-img" />
        </RouterLink>

        <nav class="nav-desktop" aria-label="Main">
          <NavDropdown
            v-for="group in navGroups"
            :key="group.label"
            :label="group.label"
            :items="group.items"
          />
        </nav>

        <div class="header-actions">
          <select
            class="locale-select"
            :value="locale"
            aria-label="Language"
            @change="setLocale($event.target.value)"
          >
            <option value="ko">KO</option>
            <option value="zh">ZH</option>
            <option value="en">EN</option>
            <option value="ja">JA</option>
          </select>

          <template v-if="auth.isLoggedIn && auth.isBuyer">
            <RouterLink to="/simple-quote" class="btn btn-sm btn-secondary nav-auth">
              {{ t('simpleQuote.title') }}
            </RouterLink>
            <RouterLink to="/rfq/new" class="btn btn-sm btn-secondary nav-auth">
              {{ t('nav.detailedQuote') }}
            </RouterLink>
            <RouterLink to="/packaging" class="btn btn-sm btn-secondary nav-auth">
              {{ t('packaging.title') }}
            </RouterLink>
            <template v-if="auth.isSupplier">
              <RouterLink to="/supplier/quote-requests" class="btn btn-sm btn-secondary nav-auth">
                {{ t('quoteRequest.title') }}
              </RouterLink>
              <RouterLink to="/supplier/projects" class="btn btn-sm btn-secondary nav-auth">
                {{ t('nav.supplierProjects') }}
              </RouterLink>
              <RouterLink to="/supplier/orders" class="btn btn-sm btn-secondary nav-auth">
                {{ t('nav.supplierOrders') }}
              </RouterLink>
              <button type="button" class="btn btn-sm btn-secondary nav-auth nav-mypage" @click="openChat()">
                {{ t('chat.nav') }}
                <span v-if="chatUnread > 0" class="nav-badge">{{ chatUnread > 99 ? '99+' : chatUnread }}</span>
              </button>
              <RouterLink to="/my?tab=notifications" class="btn btn-sm btn-secondary nav-auth nav-mypage">
                {{ t('mypage.notifications') }}
                <span v-if="unreadCount > 0" class="nav-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
              </RouterLink>
            </template>
            <span v-else-if="auth.isFactoryPending" class="nav-pending">{{ t('nav.factoryPending') }}</span>
            <RouterLink to="/shop/cart" class="btn btn-sm btn-secondary nav-auth">
              {{ t('nav.cart') }}
            </RouterLink>
            <button
              v-if="!auth.isSupplier"
              type="button"
              class="btn btn-sm btn-secondary nav-auth nav-mypage"
              @click="openChat()"
            >
              {{ t('chat.nav') }}
              <span v-if="chatUnread > 0" class="nav-badge">{{ chatUnread > 99 ? '99+' : chatUnread }}</span>
            </button>
            <RouterLink to="/my" class="btn btn-sm btn-primary nav-auth nav-mypage">
              {{ t('mypage.title') }}
              <span v-if="unreadCount > 0" class="nav-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
            </RouterLink>
          </template>
          <template v-else>
            <RouterLink to="/login" class="btn btn-sm btn-secondary nav-auth">
              {{ t('nav.login') }}
            </RouterLink>
            <RouterLink to="/register" class="btn btn-sm btn-primary nav-auth">
              {{ t('nav.register') }}
            </RouterLink>
          </template>

          <button
            type="button"
            class="menu-toggle"
            :aria-expanded="menuOpen"
            :aria-label="menuOpen ? t('nav.close') : t('nav.menu')"
            @click="menuOpen = !menuOpen"
          >
            <span class="menu-bar" />
            <span class="menu-bar" />
            <span class="menu-bar" />
          </button>
        </div>
      </div>

      <div v-if="menuOpen" class="nav-mobile" @click="closeMenu">
        <nav class="nav-mobile-inner" @click.stop>
          <template v-for="group in navGroups" :key="group.label">
            <p class="nav-mobile-group">{{ group.label }}</p>
            <template v-for="item in group.items" :key="item.path">
              <RouterLink
                v-if="!isExternal(item.path)"
                :to="item.path"
                @click="closeMenu"
              >
                {{ item.label }}
              </RouterLink>
              <a
                v-else
                :href="item.path"
                :target="item.openInNewTab ? '_blank' : undefined"
                :rel="item.openInNewTab ? 'noopener noreferrer' : undefined"
                @click="closeMenu"
              >
                {{ item.label }}
              </a>
            </template>
          </template>
          <div class="nav-mobile-auth">
            <template v-if="auth.isLoggedIn && auth.isBuyer">
              <RouterLink to="/my" @click="closeMenu">{{ t('mypage.title') }}</RouterLink>
              <RouterLink to="/simple-quote" @click="closeMenu">{{ t('simpleQuote.title') }}</RouterLink>
              <RouterLink to="/rfq/new" @click="closeMenu">{{ t('nav.detailedQuote') }}</RouterLink>
              <RouterLink to="/packaging" @click="closeMenu">{{ t('packaging.title') }}</RouterLink>
              <RouterLink to="/demand-hall" @click="closeMenu">{{ t('nav.demandHall') }}</RouterLink>
              <template v-if="auth.isSupplier">
                <RouterLink to="/supplier/quote-requests" @click="closeMenu">{{ t('quoteRequest.title') }}</RouterLink>
                <RouterLink to="/supplier/projects" @click="closeMenu">{{ t('nav.supplierProjects') }}</RouterLink>
                <RouterLink to="/supplier/orders" @click="closeMenu">{{ t('nav.supplierOrders') }}</RouterLink>
              </template>
              <RouterLink to="/my/orders" @click="closeMenu">{{ t('nav.myOrders') }}</RouterLink>
              <RouterLink to="/shop/cart" @click="closeMenu">{{ t('nav.cart') }}</RouterLink>
            </template>
            <template v-else>
              <RouterLink to="/login" @click="closeMenu">{{ t('nav.login') }}</RouterLink>
              <RouterLink to="/register" @click="closeMenu">{{ t('nav.register') }}</RouterLink>
            </template>
          </div>
        </nav>
      </div>
    </header>

    <main class="main">
      <RouterView />
    </main>

    <footer class="footer">
      <div class="container footer-grid">
        <div class="footer-brand">
          <RouterLink to="/" class="footer-logo">
            <img src="/mass-connected-logo.png" alt="MASS CONNECTED" class="footer-logo-img" />
          </RouterLink>
          <p class="footer-tagline">{{ t('footer.tagline') }}</p>
        </div>
        <div class="footer-col">
          <h4>{{ t('nav.manufacturingQuote') }}</h4>
          <RouterLink to="/rfq/new">{{ t('nav.postRequest') }}</RouterLink>
          <RouterLink to="/demand-hall">{{ t('nav.findDemands') }}</RouterLink>
          <RouterLink to="/partners">{{ t('nav.partnersDirectory') }}</RouterLink>
        </div>
        <div class="footer-col">
          <h4>{{ t('nav.shop') }}</h4>
          <RouterLink to="/shop">{{ t('nav.shopCategories') }}</RouterLink>
          <RouterLink to="/cases">{{ t('footer.cases') }}</RouterLink>
          <RouterLink to="/news">{{ t('footer.news') }}</RouterLink>
        </div>
        <div class="footer-col">
          <h4>{{ t('footer.support') }}</h4>
          <RouterLink to="/support/faq">{{ t('footer.faq') }}</RouterLink>
          <RouterLink to="/contact">{{ t('footer.contact') }}</RouterLink>
          <RouterLink to="/about">{{ t('footer.about') }}</RouterLink>
        </div>
      </div>
      <div class="footer-bottom container">
        <p>{{ t('footer.copyright', { year: currentYear }) }}</p>
      </div>
    </footer>
    <ChatPanel
      :open="chatOpen"
      :quote-request-id="chatQuoteRequestId"
      @close="closeChat"
      @unread-change="(n) => (chatUnread = n)"
    />
  </div>
</template>

<style scoped lang="scss">
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  gap: var(--space-lg);
}

.logo {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  text-decoration: none;
}

.logo-img {
  height: 3rem;
  width: auto;
  display: block;
}

.nav-desktop {
  display: flex;
  align-items: center;
  gap: var(--space-xl);
  flex: 1;
  justify-content: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
}

.locale-select {
  font-size: 0.8125rem;
  font-weight: 500;
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
}

.menu-toggle {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 2.5rem;
  height: 2.5rem;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
}

.menu-bar {
  display: block;
  width: 18px;
  height: 2px;
  margin: 0 auto;
  background: var(--color-ink);
  border-radius: 1px;
}

.nav-mobile {
  display: none;
  position: fixed;
  inset: var(--header-height) 0 0;
  background: rgba(10, 14, 20, 0.4);
  z-index: 99;
}

.nav-mobile-inner {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  max-height: calc(100vh - var(--header-height));
  overflow-y: auto;

  a {
    padding: var(--space-md);
    font-size: 0.9375rem;
    font-weight: 500;
    color: var(--color-text-heading);
    text-decoration: none;
    border-radius: var(--radius-md);

    &:hover,
    &.router-link-active {
      background: var(--color-steel-muted);
      color: var(--color-steel);
    }
  }
}

.nav-mobile-group {
  margin: var(--space-sm) 0 0;
  padding: 0 var(--space-md);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.nav-mobile-auth {
  margin-top: var(--space-sm);
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.footer {
  background: var(--color-ink);
  color: rgba(255, 255, 255, 0.75);
  margin-top: auto;
}

.footer-grid {
  display: grid;
  grid-template-columns: 1.5fr repeat(3, 1fr);
  gap: var(--space-2xl);
  padding-block: var(--space-3xl);
}

.footer-logo {
  display: inline-block;
  text-decoration: none;
}

.footer-logo-img {
  height: 2.25rem;
  width: auto;
  display: block;
  filter: brightness(0) invert(1);
}

.footer-tagline {
  margin-top: var(--space-md);
  font-size: 0.875rem;
  line-height: 1.6;
  max-width: 16rem;
}

.footer-col {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);

  h4 {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: var(--space-sm);
  }

  a {
    font-size: 0.875rem;
    color: rgba(255, 255, 255, 0.75);
    text-decoration: none;
    transition: color var(--duration-fast) var(--ease-out);

    &:hover {
      color: #fff;
    }
  }
}

.footer-bottom {
  padding-block: var(--space-lg);
  border-top: 1px solid rgba(255, 255, 255, 0.1);

  p {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.45);
    margin: 0;
  }
}

.nav-mypage { position: relative; }
.nav-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.1rem;
  height: 1.1rem;
  padding: 0 0.25rem;
  margin-left: 0.35rem;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-size: 0.65rem;
  font-weight: 700;
  line-height: 1;
}

@media (max-width: 1024px) {
  .nav-desktop {
    display: none;
  }

  .nav-auth {
    display: none;
  }

  .menu-toggle {
    display: flex;
  }

  .nav-mobile {
    display: block;
  }

  .footer-grid {
    grid-template-columns: 1fr 1fr;
    gap: var(--space-xl);
  }

  .footer-brand {
    grid-column: 1 / -1;
  }
}

@media (max-width: 640px) {
  .footer-grid {
    grid-template-columns: 1fr;
  }
}
</style>
