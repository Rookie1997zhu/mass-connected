<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchSupplierDashboard } from '../../api'

const { t, te } = useI18n()
const loading = ref(true)
const error = ref('')
const data = ref(null)

const company = computed(() => data.value?.company || {})
const counts = computed(() => data.value?.counts || {})
const deadlines = computed(() => data.value?.upcoming_deadlines || [])
const notifications = computed(() => data.value?.recent_notifications || [])

const locationText = computed(() => {
  const parts = [company.value.city, company.value.country].filter(Boolean)
  return parts.join(' · ')
})

const companyTitle = computed(
  () => company.value.company_name || company.value.short_name || t('supplierWorkbench.unnamedCompany'),
)

const deadlineTo = (row) => {
  if (row.kind === 'project') return `/supplier/projects/${row.id}`
  return `/supplier/quote-requests/${row.id}`
}

const deadlineKindLabel = (kind) => {
  if (kind === 'project') return t('supplierWorkbench.kindProject')
  return t('supplierWorkbench.kindQuoteRequest')
}

const notificationTitle = (row) => row.title || t('supplierWorkbench.notificationFallback')

const trOr = (key, fallback) => (te(key) ? t(key) : fallback)

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchSupplierDashboard()
    data.value = res.data || {}
  } catch (e) {
    error.value = e.message || t('supplierWorkbench.loadFailed')
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
          <h1 class="page-title">{{ t('supplierWorkbench.title') }}</h1>
          <p class="page-lead">{{ t('supplierWorkbench.desc') }}</p>
        </div>
      </header>

      <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
      <p v-else-if="error" class="page-message page-message--error">{{ error }}</p>

      <div v-else class="wb-layout">
        <aside class="wb-side">
          <section class="wb-card company-card">
            <p class="eyebrow">{{ t('supplierWorkbench.company') }}</p>
            <h2 class="company-name">{{ companyTitle }}</h2>
            <p v-if="locationText" class="meta">{{ locationText }}</p>
            <p v-if="company.score != null" class="meta">
              {{ t('supplierWorkbench.score') }}: {{ company.score }}
            </p>
            <p v-if="company.status" class="meta status">
              {{ trOr(`supplierWorkbench.status.${company.status}`, company.status) }}
            </p>
            <RouterLink to="/my?tab=profile" class="btn btn-sm btn-secondary">
              {{ t('supplierWorkbench.editProfile') }}
            </RouterLink>
          </section>

          <section class="wb-card quick-card">
            <h3 class="card-title">{{ t('supplierWorkbench.quickLinks') }}</h3>
            <nav class="quick-links">
              <RouterLink to="/supplier/quote-requests" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('quoteRequest.title') }}</span>
                <span v-if="counts.pending_quote_requests" class="quick-count">{{ counts.pending_quote_requests }}</span>
              </RouterLink>
              <RouterLink to="/supplier/projects" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('nav.supplierProjects') }}</span>
                <span v-if="counts.active_projects" class="quick-count">{{ counts.active_projects }}</span>
              </RouterLink>
              <RouterLink to="/supplier/orders" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('nav.supplierOrders') }}</span>
                <span v-if="counts.pending_production_orders" class="quick-count">{{ counts.pending_production_orders }}</span>
              </RouterLink>
              <RouterLink to="/demand-hall" class="btn btn-sm btn-secondary quick-btn">
                <span>{{ t('nav.demandHall') }}</span>
              </RouterLink>
            </nav>
          </section>
        </aside>

        <div class="wb-main">
          <section class="stat-grid">
            <RouterLink to="/supplier/quote-requests" class="stat-card">
              <span class="stat-num">{{ counts.pending_quote_requests ?? 0 }}</span>
              <span class="stat-label">{{ t('supplierWorkbench.pendingQuotes') }}</span>
            </RouterLink>
            <RouterLink to="/supplier/orders" class="stat-card">
              <span class="stat-num">{{ counts.pending_production_orders ?? 0 }}</span>
              <span class="stat-label">{{ t('supplierWorkbench.pendingOrders') }}</span>
            </RouterLink>
            <RouterLink to="/supplier/projects" class="stat-card">
              <span class="stat-num">{{ counts.active_projects ?? 0 }}</span>
              <span class="stat-label">{{ t('supplierWorkbench.activeProjects') }}</span>
            </RouterLink>
            <RouterLink to="/my?tab=notifications" class="stat-card">
              <span class="stat-num">{{ counts.unread_notifications ?? 0 }}</span>
              <span class="stat-label">{{ t('supplierWorkbench.unreadNotifications') }}</span>
            </RouterLink>
          </section>

          <section class="wb-card">
            <div class="card-head">
              <h3 class="card-title">{{ t('supplierWorkbench.upcomingDeadlines') }}</h3>
            </div>
            <p v-if="!deadlines.length" class="empty-inline">{{ t('supplierWorkbench.noDeadlines') }}</p>
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
              <h3 class="card-title">{{ t('supplierWorkbench.recentNotifications') }}</h3>
              <RouterLink to="/my?tab=notifications" class="link-all">
                {{ t('supplierWorkbench.viewAll') }}
              </RouterLink>
            </div>
            <p v-if="!notifications.length" class="empty-inline">{{ t('supplierWorkbench.noNotifications') }}</p>
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
