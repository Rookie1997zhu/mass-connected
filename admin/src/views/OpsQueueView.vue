<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { fetchAdminOpsQueue } from '../api'

const { t } = useI18n()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const data = ref(null)
const activeTab = ref('disputes')

const counts = computed(() => data.value?.counts || {})

const tabs = [
  { id: 'disputes', countKey: 'disputes_open', labelKey: 'opsQueue.tabDisputes' },
  { id: 'payments', countKey: 'payments_pending_confirm', labelKey: 'opsQueue.tabPayments' },
  { id: 'orders', countKey: 'orders_pending_confirm', labelKey: 'opsQueue.tabOrders' },
  { id: 'project_issues', countKey: 'project_issues_open', labelKey: 'opsQueue.tabIssues' },
]

const rows = computed(() => {
  const d = data.value
  if (!d) return []
  if (activeTab.value === 'disputes') return d.disputes || []
  if (activeTab.value === 'payments') return d.payments || []
  if (activeTab.value === 'orders') return d.orders || []
  return d.project_issues || []
})

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchAdminOpsQueue()
    data.value = res.data || {}
  } catch (e) {
    error.value = e?.response?.data?.message || t('opsQueue.loadFailed')
  } finally {
    loading.value = false
  }
}

const openRow = (row) => {
  if (row?.href) router.push(row.href)
}

onMounted(load)
</script>

<template>
  <div>
    <h2>{{ t('opsQueue.title') }}</h2>
    <p class="desc">{{ t('opsQueue.desc') }}</p>

    <p v-if="loading" class="muted">{{ t('common.loading') || '...' }}</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <template v-else>
      <div class="count-row">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          class="count-chip"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <span class="count-num">{{ counts[tab.countKey] ?? 0 }}</span>
          <span>{{ t(tab.labelKey) }}</span>
        </button>
      </div>

      <el-table :data="rows" stripe empty-text="—">
        <template v-if="activeTab === 'disputes'">
          <el-table-column prop="quote_request_no" :label="t('opsQueue.colRequest')" min-width="140" />
          <el-table-column prop="buyer_email" :label="t('opsQueue.colBuyer')" min-width="160" />
          <el-table-column prop="supplier_email" :label="t('opsQueue.colSupplier')" min-width="160" />
          <el-table-column prop="dispute_reason" :label="t('opsQueue.colReason')" min-width="180" show-overflow-tooltip />
          <el-table-column prop="disputed_at" :label="t('opsQueue.colTime')" width="180" />
        </template>
        <template v-else-if="activeTab === 'payments'">
          <el-table-column prop="payment_no" :label="t('opsQueue.colPayment')" min-width="140" />
          <el-table-column prop="amount" :label="t('opsQueue.colAmount')" width="120" />
          <el-table-column prop="currency" :label="t('opsQueue.colCurrency')" width="90" />
          <el-table-column prop="buyer_email" :label="t('opsQueue.colBuyer')" min-width="160" />
          <el-table-column prop="created_at" :label="t('opsQueue.colTime')" width="180" />
        </template>
        <template v-else-if="activeTab === 'orders'">
          <el-table-column prop="order_no" :label="t('opsQueue.colOrder')" min-width="140" />
          <el-table-column prop="rfq_no" :label="t('opsQueue.colRfq')" min-width="120" />
          <el-table-column prop="buyer_email" :label="t('opsQueue.colBuyer')" min-width="160" />
          <el-table-column prop="supplier_email" :label="t('opsQueue.colSupplier')" min-width="160" />
          <el-table-column prop="created_at" :label="t('opsQueue.colTime')" width="180" />
        </template>
        <template v-else>
          <el-table-column prop="project_no" :label="t('opsQueue.colProject')" min-width="120" />
          <el-table-column prop="title" :label="t('opsQueue.colIssue')" min-width="180" />
          <el-table-column prop="severity" :label="t('opsQueue.colSeverity')" width="100" />
          <el-table-column prop="created_at" :label="t('opsQueue.colTime')" width="180" />
        </template>
        <el-table-column :label="t('common.actions') || '操作'" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openRow(row)">{{ t('opsQueue.open') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </div>
</template>

<style scoped>
.desc { color: #6b7280; margin-bottom: 1rem; }
.muted { color: #9ca3af; }
.error { color: #b91c1c; }
.count-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
.count-chip {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  padding: 0.75rem 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  min-width: 9rem;
}
.count-chip.active {
  border-color: #111827;
  background: #f9fafb;
}
.count-num {
  font-size: 1.35rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
</style>
