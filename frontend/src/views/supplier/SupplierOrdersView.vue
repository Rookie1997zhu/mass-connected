<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { confirmProductionOrder, fetchSupplierProductionOrders, rejectProductionOrder } from '../../api'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'
import { resolveApiMessage } from '../../utils/apiErrors'

const { t } = useI18n()
const { formatMoney } = useLocaleCurrency()
const items = ref([])
const statusFilter = ref('')
const loading = ref(true)
const message = ref('')
const error = ref('')

const load = async () => {
  const params = statusFilter.value ? { status: statusFilter.value } : {}
  const res = await fetchSupplierProductionOrders(params)
  items.value = res.data.items || []
}

onMounted(async () => {
  try {
    await load()
  } finally {
    loading.value = false
  }
})

const onFilter = async () => {
  loading.value = true
  try {
    await load()
  } finally {
    loading.value = false
  }
}

const onConfirm = async (id) => {
  error.value = ''
  message.value = ''
  try {
    await confirmProductionOrder(id)
    message.value = t('productionOrder.confirmed')
    await load()
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'productionOrder.confirmFailed')
  }
}

const onReject = async (id) => {
  error.value = ''
  message.value = ''
  try {
    await rejectProductionOrder(id)
    message.value = t('productionOrder.rejected')
    await load()
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'productionOrder.rejectFailed')
  }
}
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('productionOrder.supplierTitle') }}</h1>

    <div class="filters">
      <select v-model="statusFilter" @change="onFilter">
        <option value="">{{ t('productionOrder.allStatus') }}</option>
        <option value="pending_confirm">{{ t('productionOrder.pendingConfirm') }}</option>
        <option value="confirmed">{{ t('productionOrder.confirmedStatus') }}</option>
        <option value="cancelled">{{ t('productionOrder.cancelled') }}</option>
      </select>
    </div>

    <p v-if="message" class="page-message page-message--success">{{ message }}</p>
    <p v-if="error" class="page-message page-message--error">{{ error }}</p>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('common.empty') }}</p>
    <table v-else class="order-table">
      <thead>
        <tr>
          <th>{{ t('productionOrder.orderNo') }}</th>
          <th>{{ t('demandHall.rfqNo') }}</th>
          <th>{{ t('rfq.price') }}</th>
          <th>{{ t('common.status') }}</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="o in items" :key="o.id">
          <td>{{ o.order_no }}</td>
          <td>{{ o.rfq_no }}</td>
          <td>{{ formatMoney({ amount: o.price_amount, currency: o.currency }) }}</td>
          <td>{{ o.status }}</td>
          <td class="actions">
            <RouterLink
              v-if="o.quote_request_id"
              class="link"
              :to="`/supplier/quote-requests/${o.quote_request_id}`"
            >
              {{ t('fulfillment.viewDeal') }}
            </RouterLink>
            <template v-if="o.status === 'pending_confirm'">
              <button type="button" class="btn btn-sm btn-primary" @click="onConfirm(o.id)">
                {{ t('productionOrder.confirm') }}
              </button>
              <button type="button" class="btn btn-sm btn-secondary" @click="onReject(o.id)">
                {{ t('productionOrder.reject') }}
              </button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </PageShell>
</template>

<style scoped lang="scss">
.filters { margin-bottom: var(--space-lg); select { padding: 0.5rem; border-radius: var(--radius-sm); border: 1px solid var(--color-border); } }
.order-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm); border-bottom: 1px solid var(--color-border); font-size: 0.9375rem; } }
.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
.link { color: var(--color-steel); font-size: 0.875rem; text-decoration: none; font-weight: 600; }
</style>
