<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { fetchAdminStats } from '../api'

const { t } = useI18n()
const router = useRouter()
const stats = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchAdminStats()
    stats.value = res.data
  } finally {
    loading.value = false
  }
})

const cards = [
  { key: 'rfqs_total', route: '/rfqs', labelKey: 'dashboard.rfqsTotal' },
  { key: 'rfqs_pending_review', route: '/rfqs', labelKey: 'dashboard.rfqsPending' },
  { key: 'projects_active', route: '/projects', labelKey: 'dashboard.projectsActive' },
  { key: 'payments_pending_confirm', route: '/payments', labelKey: 'dashboard.paymentsPending' },
  { key: 'inquiries_new', route: '/inquiries', labelKey: 'dashboard.inquiriesNew' },
  { key: 'members_total', route: '/members', labelKey: 'dashboard.membersTotal' },
  { key: 'suppliers_approved', route: '/suppliers', labelKey: 'dashboard.suppliersApproved' },
]
</script>

<template>
  <div>
    <h2>{{ t('dashboard.title') }}</h2>
    <p class="desc">{{ t('dashboard.desc') }}</p>
    <p v-if="loading" class="muted">{{ t('common.loading') || '...' }}</p>
    <div v-else class="stat-grid">
      <button
        v-for="c in cards"
        :key="c.key"
        type="button"
        class="stat-card"
        @click="router.push(c.route)"
      >
        <span class="stat-num">{{ stats?.[c.key] ?? 0 }}</span>
        <span class="stat-label">{{ t(c.labelKey) }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.desc { color: #6b7280; margin-bottom: 1.5rem; }
.muted { color: #9ca3af; }
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}
.stat-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 1.25rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.stat-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12);
}
.stat-num { font-size: 1.75rem; font-weight: 700; color: #111827; }
.stat-label { font-size: 0.85rem; color: #6b7280; margin-top: 0.35rem; }
</style>
