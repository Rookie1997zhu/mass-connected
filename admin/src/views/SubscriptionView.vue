<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  confirmSubscriptionOrder,
  createSubscriptionPlan,
  fetchMembers,
  fetchSubscriptionLedgers,
  fetchSubscriptionOrders,
  fetchSubscriptionPlans,
  fetchSubscriptions,
  grantSubscription,
  updateSubscriptionPlan,
} from '../api'

const { t } = useI18n()
const tab = ref('plans')

const plans = ref([])
const subscriptions = ref([])
const orders = ref([])
const ledgers = ref([])
const members = ref([])

const planDialog = ref(false)
const editingPlanId = ref(null)
const planForm = ref({
  code: '',
  name: '',
  status: 'draft',
  billing_period: 'month',
  price_amount: null,
  currency: 'KRW',
  simple_quote_limit: 10,
  description: '',
})

const grantDialog = ref(false)
const grantForm = ref({
  user_id: null,
  plan_version_id: null,
  note: '',
})

const publishedOrAllPlans = computed(() => plans.value)

const emptyPlanForm = () => ({
  code: '',
  name: '',
  status: 'draft',
  billing_period: 'month',
  price_amount: null,
  currency: 'KRW',
  simple_quote_limit: 10,
  description: '',
})

const featuresFromForm = () => {
  const limit = Number(planForm.value.simple_quote_limit)
  const features = {}
  if (Number.isFinite(limit) && limit > 0) {
    features.simple_quote = limit
  }
  return features
}

const loadPlans = async () => {
  const res = await fetchSubscriptionPlans()
  plans.value = res.data.items || []
}

const loadSubscriptions = async () => {
  const res = await fetchSubscriptions({ page: 1, page_size: 50 })
  subscriptions.value = res.data.items || []
}

const loadOrders = async () => {
  const res = await fetchSubscriptionOrders({ page: 1, page_size: 50 })
  orders.value = res.data.items || []
}

const loadLedgers = async () => {
  const res = await fetchSubscriptionLedgers({ page: 1, page_size: 50 })
  ledgers.value = res.data.items || []
}

const loadMembers = async () => {
  const res = await fetchMembers({ page: 1, page_size: 100 })
  members.value = res.data.items || []
}

onMounted(async () => {
  await Promise.all([loadPlans(), loadSubscriptions(), loadOrders(), loadLedgers(), loadMembers()])
})

const openCreatePlan = () => {
  editingPlanId.value = null
  planForm.value = emptyPlanForm()
  planDialog.value = true
}

const openEditPlan = (row) => {
  editingPlanId.value = row.id
  planForm.value = {
    code: row.code || '',
    name: row.name || '',
    status: row.status || 'draft',
    billing_period: row.billing_period || 'month',
    price_amount: row.price_amount ?? null,
    currency: row.currency || 'KRW',
    simple_quote_limit: Number(row.features_json?.simple_quote) || 0,
    description: row.description || '',
  }
  planDialog.value = true
}

const submitPlan = async () => {
  if (!planForm.value.code || !planForm.value.name) {
    ElMessage.warning(t('subscription.planRequired'))
    return
  }
  const payload = {
    code: planForm.value.code,
    name: planForm.value.name,
    status: planForm.value.status,
    billing_period: planForm.value.billing_period,
    price_amount: planForm.value.price_amount === '' || planForm.value.price_amount == null
      ? null
      : Number(planForm.value.price_amount),
    currency: planForm.value.currency || 'KRW',
    features_json: featuresFromForm(),
    description: planForm.value.description || '',
  }
  if (editingPlanId.value) {
    await updateSubscriptionPlan(editingPlanId.value, payload)
  } else {
    await createSubscriptionPlan(payload)
  }
  ElMessage.success(t('common.success'))
  planDialog.value = false
  await loadPlans()
}

const openGrant = () => {
  grantForm.value = { user_id: null, plan_version_id: null, note: '' }
  grantDialog.value = true
}

const submitGrant = async () => {
  if (!grantForm.value.user_id || !grantForm.value.plan_version_id) {
    ElMessage.warning(t('subscription.grantRequired'))
    return
  }
  await grantSubscription({
    user_id: grantForm.value.user_id,
    plan_version_id: grantForm.value.plan_version_id,
    note: grantForm.value.note || '',
  })
  ElMessage.success(t('common.success'))
  grantDialog.value = false
  await Promise.all([loadSubscriptions(), loadLedgers()])
}

const onConfirmOrder = async (row) => {
  await confirmSubscriptionOrder(row.id)
  ElMessage.success(t('common.success'))
  await Promise.all([loadOrders(), loadSubscriptions()])
}

const featureSummary = (row) => {
  const f = row.features_json || {}
  return Object.entries(f)
    .map(([k, v]) => `${k}:${v}`)
    .join(', ') || '—'
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('nav.subscription') }}</h2>
      <div class="actions">
        <el-button v-if="tab === 'plans'" type="primary" @click="openCreatePlan">
          {{ t('subscription.createPlan') }}
        </el-button>
        <el-button v-if="tab === 'subscriptions'" type="primary" @click="openGrant">
          {{ t('subscription.manualGrant') }}
        </el-button>
      </div>
    </div>

    <el-tabs v-model="tab">
      <el-tab-pane :label="t('subscription.plans')" name="plans">
        <el-table :data="plans">
          <el-table-column prop="code" :label="t('subscription.planCode')" min-width="120" />
          <el-table-column prop="name" :label="t('subscription.planName')" min-width="140" />
          <el-table-column prop="status" :label="t('common.status')" width="110" />
          <el-table-column prop="billing_period" :label="t('subscription.billingPeriod')" width="100" />
          <el-table-column :label="t('subscription.price')" width="120">
            <template #default="{ row }">
              <span v-if="row.price_amount != null">{{ row.price_amount }} {{ row.currency }}</span>
              <span v-else class="muted">{{ t('subscription.pricePending') }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('subscription.features')" min-width="160">
            <template #default="{ row }">{{ featureSummary(row) }}</template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="100" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="openEditPlan(row)">{{ t('common.edit') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="t('subscription.subscriptions')" name="subscriptions">
        <el-table :data="subscriptions">
          <el-table-column prop="user_email" :label="t('common.email')" min-width="180" />
          <el-table-column :label="t('subscription.planName')" min-width="140">
            <template #default="{ row }">{{ row.plan?.name || '—' }}</template>
          </el-table-column>
          <el-table-column prop="status" :label="t('common.status')" width="110" />
          <el-table-column prop="source" :label="t('subscription.source')" width="120" />
          <el-table-column :label="t('subscription.period')" min-width="180">
            <template #default="{ row }">
              {{ (row.starts_at || '').slice(0, 10) }} → {{ (row.ends_at || '').slice(0, 10) || '—' }}
            </template>
          </el-table-column>
          <el-table-column :label="t('subscription.quota')" min-width="160">
            <template #default="{ row }">
              <span v-for="e in row.entitlements || []" :key="e.feature_code" class="quota-chip">
                {{ e.feature_code }} {{ e.remaining }}/{{ e.period_limit }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="t('subscription.orders')" name="orders">
        <el-table :data="orders">
          <el-table-column prop="order_no" :label="t('subscription.orderNo')" min-width="140" />
          <el-table-column prop="user_email" :label="t('common.email')" min-width="180" />
          <el-table-column :label="t('subscription.planName')" min-width="140">
            <template #default="{ row }">{{ row.plan?.name || '—' }}</template>
          </el-table-column>
          <el-table-column prop="status" :label="t('common.status')" width="140" />
          <el-table-column :label="t('subscription.price')" width="120">
            <template #default="{ row }">
              <span v-if="row.price_amount != null">{{ row.price_amount }} {{ row.currency }}</span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="120">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'pending_confirm'"
                size="small"
                type="primary"
                @click="onConfirmOrder(row)"
              >
                {{ t('common.confirm') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="t('subscription.ledgers')" name="ledgers">
        <el-table :data="ledgers">
          <el-table-column prop="ledger_no" :label="t('subscription.ledgerNo')" min-width="140" />
          <el-table-column prop="user_email" :label="t('common.email')" min-width="160" />
          <el-table-column prop="feature_code" :label="t('subscription.feature')" width="120" />
          <el-table-column prop="action" :label="t('subscription.action')" width="100" />
          <el-table-column prop="quantity" :label="t('subscription.quantity')" width="90" />
          <el-table-column prop="status" :label="t('common.status')" width="110" />
          <el-table-column prop="idempotency_key" :label="t('subscription.idempotency')" min-width="160" />
          <el-table-column :label="t('subscription.createdAt')" width="170">
            <template #default="{ row }">{{ (row.created_at || '').slice(0, 19) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="planDialog"
      :title="editingPlanId ? t('subscription.editPlan') : t('subscription.createPlan')"
      width="520px"
    >
      <el-form label-width="130px">
        <el-form-item :label="t('subscription.planCode')">
          <el-input v-model="planForm.code" :disabled="!!editingPlanId" />
        </el-form-item>
        <el-form-item :label="t('subscription.planName')">
          <el-input v-model="planForm.name" />
        </el-form-item>
        <el-form-item :label="t('common.status')">
          <el-select v-model="planForm.status" style="width: 100%">
            <el-option value="draft" :label="t('subscription.statusDraft')" />
            <el-option value="published" :label="t('subscription.statusPublished')" />
            <el-option value="archived" :label="t('subscription.statusArchived')" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('subscription.billingPeriod')">
          <el-select v-model="planForm.billing_period" style="width: 100%">
            <el-option value="month" label="month" />
            <el-option value="year" label="year" />
            <el-option value="none" label="none" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('subscription.price')">
          <el-input-number v-model="planForm.price_amount" :min="0" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item :label="t('subscription.currency')">
          <el-input v-model="planForm.currency" />
        </el-form-item>
        <el-form-item :label="t('subscription.simpleQuoteLimit')">
          <el-input-number v-model="planForm.simple_quote_limit" :min="0" />
        </el-form-item>
        <el-form-item :label="t('subscription.description')">
          <el-input v-model="planForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="planDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitPlan">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="grantDialog" :title="t('subscription.manualGrant')" width="480px">
      <el-form label-width="120px">
        <el-form-item :label="t('subscription.member')">
          <el-select v-model="grantForm.user_id" filterable style="width: 100%">
            <el-option
              v-for="m in members"
              :key="m.id"
              :value="m.id"
              :label="m.email || m.name || String(m.id)"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('subscription.planName')">
          <el-select v-model="grantForm.plan_version_id" filterable style="width: 100%">
            <el-option
              v-for="p in publishedOrAllPlans"
              :key="p.id"
              :value="p.id"
              :label="`${p.code} · ${p.name} (${p.status})`"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('subscription.note')">
          <el-input v-model="grantForm.note" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="grantDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitGrant">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}
.toolbar h2 {
  margin: 0;
}
.actions {
  display: flex;
  gap: 0.5rem;
}
.muted {
  color: #9ca3af;
}
.quota-chip {
  display: inline-block;
  margin-right: 0.5rem;
  font-size: 12px;
}
</style>
