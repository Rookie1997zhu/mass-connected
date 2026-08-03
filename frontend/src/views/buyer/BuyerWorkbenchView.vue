<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchBuyerWorkbench } from '../../api'

const { t, te } = useI18n()
const loading = ref(true)
const error = ref('')
const data = ref(null)

const profile = computed(() => data.value?.profile || {})
const counts = computed(() => data.value?.counts || {})
const deadlines = computed(() => data.value?.upcoming_deadlines || [])
const notifications = computed(() => data.value?.recent_notifications || [])
const actionItems = computed(() => data.value?.action_items || [])
const unreadChats = computed(() => data.value?.unread_chats || [])
const fx = computed(() => data.value?.fx || null)
const fxRateText = computed(() => {
  const rate = Number(fx.value?.cny_to_krw)
  if (!Number.isFinite(rate) || rate <= 0) return ''
  return rate.toFixed(2)
})

const displayTitle = computed(() => {
  return (
    profile.value.company_name
    || profile.value.display_name
    || profile.value.email
    || t('buyerWorkbench.unnamed')
  )
})

const memberTypeLabel = computed(() => {
  const mt = profile.value.member_type
  if (!mt) return ''
  const key = `buyerWorkbench.memberType.${mt}`
  return te(key) ? t(key) : mt
})

const deadlineTo = (row) => {
  if (row.kind === 'project') return `/my/projects/${row.id}`
  return `/my/rfqs/${row.id}`
}

const deadlineKindLabel = (kind) => {
  if (kind === 'project') return t('buyerWorkbench.kindProject')
  return t('buyerWorkbench.kindRfq')
}

const notificationTitle = (row) => row.title || t('buyerWorkbench.notificationFallback')

const actionKindLabel = (kind) => {
  const key = `buyerWorkbench.actionKind.${kind}`
  return te(key) ? t(key) : kind
}

const openChat = (quoteRequestId) => {
  if (!quoteRequestId) return
  window.__openPlatformChat?.(quoteRequestId)
}

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchBuyerWorkbench()
    data.value = res.data || {}
  } catch (e) {
    error.value = e.message || t('buyerWorkbench.loadFailed')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <div class="wb">
      <header class="wb-header">
        <div>
          <h1 class="page-title">{{ t('buyerWorkbench.title') }}</h1>
          <p class="page-lead">{{ t('buyerWorkbench.desc') }}</p>
          <div v-if="fxRateText" class="fx-card" role="status">
            <p class="fx-label">{{ t('fx.cardLabel') }}</p>
            <p class="fx-rate">{{ t('fx.cnyKrw', { rate: fxRateText }) }}</p>
            <p class="fx-hint">{{ t('fx.referenceHint') }}</p>
          </div>
        </div>
      </header>

      <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
      <p v-else-if="error" class="page-message page-message--error">{{ error }}</p>

      <div v-else class="wb-layout">
        <aside class="wb-side">
          <section class="wb-card company-card">
            <p class="eyebrow">{{ t('buyerWorkbench.identity') }}</p>
            <h2 class="company-name">{{ displayTitle }}</h2>
            <p v-if="profile.display_name && profile.company_name" class="meta">
              {{ profile.display_name }}
            </p>
            <p v-if="profile.email" class="meta">{{ profile.email }}</p>
            <p v-if="memberTypeLabel" class="meta">{{ memberTypeLabel }}</p>
            <RouterLink to="/my" class="btn btn-sm btn-secondary">
              {{ t('buyerWorkbench.openMyPage') }}
            </RouterLink>
          </section>

          <section class="wb-card quick-card">
            <h3 class="card-title">{{ t('buyerWorkbench.quickLinks') }}</h3>
            <nav class="quick-links">
              <RouterLink to="/simple-quote" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('simpleQuote.title') }}</span>
              </RouterLink>
              <RouterLink to="/my/rfqs" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('nav.myRfqs') }}</span>
                <span v-if="counts.action_rfqs" class="quick-count">{{ counts.action_rfqs }}</span>
              </RouterLink>
              <RouterLink to="/my/production-orders" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('nav.productionOrders') }}</span>
              </RouterLink>
              <RouterLink to="/rfq/new" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('nav.detailedQuote') }}</span>
              </RouterLink>
              <RouterLink to="/packaging" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('packaging.title') }}</span>
              </RouterLink>
              <RouterLink to="/shop/cart" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('nav.cart') }}</span>
              </RouterLink>
            </nav>
          </section>
        </aside>

        <div class="wb-main">
          <section class="stat-grid">
            <RouterLink to="/my/rfqs" class="stat-card">
              <span class="stat-num">{{ counts.action_rfqs ?? 0 }}</span>
              <span class="stat-label">{{ t('buyerWorkbench.actionRfqs') }}</span>
            </RouterLink>
            <RouterLink to="/my?tab=payments" class="stat-card">
              <span class="stat-num">{{ counts.pending_payments ?? 0 }}</span>
              <span class="stat-label">{{ t('buyerWorkbench.pendingPayments') }}</span>
            </RouterLink>
            <RouterLink to="/my?tab=projects" class="stat-card">
              <span class="stat-num">{{ counts.active_projects ?? 0 }}</span>
              <span class="stat-label">{{ t('buyerWorkbench.activeProjects') }}</span>
            </RouterLink>
            <RouterLink to="/my?tab=notifications" class="stat-card">
              <span class="stat-num">{{ counts.unread_notifications ?? 0 }}</span>
              <span class="stat-label">{{ t('buyerWorkbench.unreadNotifications') }}</span>
            </RouterLink>
          </section>

          <section class="wb-card">
            <div class="card-head">
              <h3 class="card-title">{{ t('buyerWorkbench.actionItems') }}</h3>
            </div>
            <p v-if="!actionItems.length" class="empty-inline">{{ t('buyerWorkbench.noActionItems') }}</p>
            <ul v-else class="list">
              <li v-for="row in actionItems" :key="`${row.kind}-${row.id}`">
                <RouterLink :to="row.href || '/buyer'" class="list-row">
                  <div class="list-main">
                    <span class="kind">{{ actionKindLabel(row.kind) }}</span>
                    <span class="list-title">{{ row.title }}</span>
                    <span v-if="row.subtitle" class="list-sub">{{ row.subtitle }}</span>
                  </div>
                </RouterLink>
              </li>
            </ul>
          </section>

          <section class="wb-card">
            <div class="card-head">
              <h3 class="card-title">{{ t('buyerWorkbench.unreadChats') }}</h3>
            </div>
            <p v-if="!unreadChats.length" class="empty-inline">{{ t('buyerWorkbench.noUnreadChats') }}</p>
            <ul v-else class="list">
              <li v-for="row in unreadChats" :key="row.conversation_id">
                <button
                  type="button"
                  class="list-row list-row--btn"
                  :disabled="!row.quote_request_id"
                  @click="openChat(row.quote_request_id)"
                >
                  <div class="list-main">
                    <span class="list-title">{{ row.title }}</span>
                    <span v-if="row.preview" class="list-sub">{{ row.preview }}</span>
                  </div>
                  <span v-if="row.unread" class="quick-count">{{ row.unread > 99 ? '99+' : row.unread }}</span>
                </button>
              </li>
            </ul>
          </section>

          <section class="wb-card">
            <div class="card-head">
              <h3 class="card-title">{{ t('buyerWorkbench.upcomingDeadlines') }}</h3>
            </div>
            <p v-if="!deadlines.length" class="empty-inline">{{ t('buyerWorkbench.noDeadlines') }}</p>
            <ul v-else class="list">
              <li v-for="row in deadlines" :key="`${row.kind}-${row.id}`">
                <RouterLink :to="deadlineTo(row)" class="list-row">
                  <div class="list-main">
                    <span class="kind">{{ deadlineKindLabel(row.kind) }}</span>
                    <span class="list-title">{{ row.title }}</span>
                    <span v-if="row.subtitle" class="list-sub">{{ row.subtitle }}</span>
                  </div>
                  <time class="list-date">{{ row.deadline }}</time>
                </RouterLink>
              </li>
            </ul>
          </section>

          <section class="wb-card">
            <div class="card-head">
              <h3 class="card-title">{{ t('buyerWorkbench.recentNotifications') }}</h3>
              <RouterLink to="/my?tab=notifications" class="link-all">
                {{ t('buyerWorkbench.viewAll') }}
              </RouterLink>
            </div>
            <p v-if="!notifications.length" class="empty-inline">{{ t('buyerWorkbench.noNotifications') }}</p>
            <ul v-else class="list">
              <li v-for="row in notifications" :key="row.id">
                <RouterLink to="/my?tab=notifications" class="list-row" :class="{ unread: !row.is_read }">
                  <div class="list-main">
                    <span class="list-title">{{ notificationTitle(row) }}</span>
                  </div>
                  <time class="list-date">{{ (row.created_at || '').slice(0, 10) }}</time>
                </RouterLink>
              </li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.wb-header { margin-bottom: var(--space-md); }
.fx-card {
  margin: 0.85rem 0 0;
  max-width: 36rem;
  padding: 0.9rem 1.1rem;
  border: 1px solid var(--color-steel, #3a5a7a);
  border-left-width: 4px;
  border-radius: var(--radius-md);
  background: var(--color-steel-muted, #eef3f7);
  box-shadow: 0 1px 0 rgba(58, 90, 122, 0.08);
}
.fx-label {
  margin: 0 0 0.2rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-steel, #3a5a7a);
  opacity: 0.85;
}
.fx-rate {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.25;
  font-variant-numeric: tabular-nums;
  color: var(--color-text, #1a1a1a);
}
.fx-hint {
  margin: 0.35rem 0 0;
  font-size: 0.8125rem;
  line-height: 1.4;
  opacity: 0.65;
}
.wb-layout {
  display: grid;
  grid-template-columns: minmax(240px, 280px) 1fr;
  gap: var(--space-lg);
  align-items: start;
}
.wb-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  position: sticky;
  top: 1rem;
}
.wb-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  min-width: 0;
}
.wb-card {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}
.eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  opacity: 0.55;
}
.company-name {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  line-height: 1.3;
}
.meta {
  margin: 0 0 0.35rem;
  font-size: 0.875rem;
  opacity: 0.7;
}
.company-card .btn { margin-top: 0.75rem; }
.card-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.link-all {
  font-size: 0.875rem;
  color: var(--color-steel, #3a5a7a);
  text-decoration: none;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-md);
}
.stat-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  background: var(--color-surface, #fff);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s ease;
}
.stat-card:hover { border-color: var(--color-steel, #3a5a7a); }
.stat-num { font-size: 1.75rem; font-weight: 700; line-height: 1.1; }
.stat-label { font-size: 0.8125rem; opacity: 0.65; }
.quick-links {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.quick-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  text-decoration: none;
  text-align: left;
}
.quick-count {
  min-width: 1.25rem;
  height: 1.25rem;
  padding: 0 0.35rem;
  border-radius: 999px;
  background: var(--color-steel, #3a5a7a);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-variant-numeric: tabular-nums;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.list-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--color-border);
  text-decoration: none;
  color: inherit;
}
.list-row--btn {
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--color-border);
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
}
.list-row--btn:disabled {
  cursor: default;
  opacity: 0.7;
}
.list li:last-child .list-row { border-bottom: none; }
.list-row.unread .list-title { font-weight: 600; }
.list-main {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}
.kind {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  opacity: 0.5;
}
.list-title {
  font-size: 0.9375rem;
  word-break: break-word;
}
.list-sub {
  font-size: 0.8125rem;
  opacity: 0.6;
}
.list-date {
  flex-shrink: 0;
  font-size: 0.8125rem;
  opacity: 0.55;
  font-variant-numeric: tabular-nums;
}
.empty-inline {
  margin: 0;
  font-size: 0.875rem;
  opacity: 0.55;
}

@media (max-width: 960px) {
  .wb-layout { grid-template-columns: 1fr; }
  .wb-side { position: static; }
  .stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
  .stat-grid { grid-template-columns: 1fr; }
}
</style>
