<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  assignRfqSuppliers,
  cancelQuoteRequest,
  createRfqQuote,
  fetchRfq,
  fetchRfqQuoteRequests,
  fetchRfqs,
  fetchSuppliers,
  reviseQuoteRequest,
  updateRfqQuote,
  updateRfqStatus,
} from '../api'

const { t } = useI18n()
const items = ref([])
const statusFilter = ref('')
const detailDialog = ref(false)
const detail = ref(null)
const suppliers = ref([])
const quoteRequests = ref([])

const RFQ_STATUSES = [
  'submitted',
  'pending_review',
  'assigned',
  'quoting',
  'quoted',
  'comparing',
  'customer_confirming',
  'negotiating',
  'won',
  'closed',
]
const emptyQuote = () => ({
  price_amount: null,
  currency: 'KRW',
  lead_time_days: 0,
  valid_until: null,
  note: '',
  plan_label: '',
  is_customer_visible: false,
  unit_price: null,
  mold_fee: null,
  sample_fee: null,
  moq: null,
  payment_terms: '',
})
const quoteForm = ref(emptyQuote())

const assignForm = ref({ supplier_ids: [], deadline: null, admin_note: '', is_urgent: false, tag_filter: '' })
const tagOptions = ref([])

const loadSuppliers = async (tag) => {
  const params = tag ? { tag } : {}
  const res = await fetchSuppliers(params)
  suppliers.value = res.data.items || []
  const tags = new Set()
  for (const s of suppliers.value) {
    for (const t of s.tags || []) tags.add(t.tag_name)
  }
  tagOptions.value = [...tags].sort()
}

const onTagFilterChange = async () => {
  await loadSuppliers(assignForm.value.tag_filter || undefined)
  assignForm.value.supplier_ids = assignForm.value.supplier_ids.filter((id) =>
    suppliers.value.some((s) => s.id === id),
  )
}

const load = async () => {
  const params = statusFilter.value ? { status: statusFilter.value } : {}
  const res = await fetchRfqs(params)
  items.value = res.data.items || []
}
onMounted(async () => {
  await load()
  try {
    await loadSuppliers()
  } catch { /* suppliers optional */ }
})

const openDetail = async (row) => {
  const res = await fetchRfq(row.id)
  detail.value = res.data
  quoteForm.value = emptyQuote()
  assignForm.value = { supplier_ids: [], deadline: null, admin_note: '', is_urgent: false, tag_filter: '' }
  await loadSuppliers()
  try {
    const qr = await fetchRfqQuoteRequests(row.id)
    quoteRequests.value = qr.data.items || []
  } catch {
    quoteRequests.value = []
  }
  detailDialog.value = true
}

const changeStatus = async (status) => {
  const res = await updateRfqStatus(detail.value.id, { status })
  detail.value = res.data
  await load()
}

const saveMarkup = async () => {
  const res = await updateRfqStatus(detail.value.id, { markup_percent: detail.value.markup_percent })
  detail.value = res.data
  ElMessage.success(t('common.success'))
}

const submitQuote = async () => {
  if (!quoteForm.value.price_amount) {
    ElMessage.warning(t('rfqs.price'))
    return
  }
  await createRfqQuote(detail.value.id, quoteForm.value)
  const res = await fetchRfq(detail.value.id)
  detail.value = res.data
  quoteForm.value = emptyQuote()
  await load()
}

const saveQuote = async (row) => {
  await updateRfqQuote(row.id, { plan_label: row.plan_label, is_customer_visible: row.is_customer_visible })
  ElMessage.success(t('common.success'))
}

const onReviseQuoteRequest = async (qr) => {
  await reviseQuoteRequest(qr.id)
  ElMessage.success(t('rfqs.reviseSent'))
  const res = await fetchRfqQuoteRequests(detail.value.id)
  quoteRequests.value = res.data.items || []
}

const onCancelQuoteRequest = async (qr) => {
  await cancelQuoteRequest(qr.id)
  ElMessage.success(t('rfqs.assignCancelled'))
  const res = await fetchRfqQuoteRequests(detail.value.id)
  quoteRequests.value = res.data.items || []
}

const submitAssign = async () => {
  if (!assignForm.value.supplier_ids.length) {
    ElMessage.warning(t('common.assignSuppliers'))
    return
  }
  await assignRfqSuppliers(detail.value.id, assignForm.value)
  const res = await fetchRfq(detail.value.id)
  detail.value = res.data
  const qr = await fetchRfqQuoteRequests(detail.value.id)
  quoteRequests.value = qr.data.items || []
  ElMessage.success(t('common.success'))
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('rfqs.title') }}</h2>
      <el-select v-model="statusFilter" clearable :placeholder="t('rfqs.filterStatus')" style="width: 200px" @change="load">
        <el-option v-for="s in RFQ_STATUSES" :key="s" :label="s" :value="s" />
      </el-select>
    </div>
    <el-table :data="items">
      <el-table-column prop="rfq_no" label="RFQ No" width="180" />
      <el-table-column prop="service_category_name" :label="t('rfqs.category')" />
      <el-table-column prop="quantity" :label="t('rfqs.quantity')" width="90" />
      <el-table-column prop="quotes_count" :label="t('rfqs.quotes')" width="90" />
      <el-table-column prop="status" :label="t('common.status')" width="150" />
      <el-table-column :label="t('common.actions')" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openDetail(row)">{{ t('rfqs.detail') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="detailDialog" :title="t('rfqs.detail')" width="860px" destroy-on-close>
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="RFQ No">{{ detail.rfq_no }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.status')">
            <el-select :model-value="detail.status" style="width: 180px" @change="changeStatus">
              <el-option v-for="s in RFQ_STATUSES" :key="s" :label="s" :value="s" />
            </el-select>
          </el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.buyer')">{{ detail.buyer_name }} ({{ detail.buyer_email }})</el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.category')">{{ detail.service_category_name }}</el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.quantity')">{{ detail.quantity }}</el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.material')">{{ detail.material }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.markup')">
            <el-input-number v-model="detail.markup_percent" :min="0" size="small" />
            <el-button size="small" type="primary" style="margin-left: 8px" @click="saveMarkup">{{ t('common.save') }}</el-button>
          </el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.note')" :span="2">{{ detail.remark }}</el-descriptions-item>
        </el-descriptions>

        <h4>{{ t('common.assignSuppliers') }}</h4>
        <el-form :inline="true">
          <el-form-item :label="t('suppliers.tagFilter')">
            <el-select v-model="assignForm.tag_filter" clearable style="width: 160px" @change="onTagFilterChange">
              <el-option v-for="tag in tagOptions" :key="tag" :label="tag" :value="tag" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('nav.suppliers')">
            <el-select v-model="assignForm.supplier_ids" multiple style="width: 280px">
              <el-option v-for="s in suppliers" :key="s.id" :label="s.company_name || s.email" :value="s.id" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('common.deadline')">
            <el-date-picker v-model="assignForm.deadline" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item :label="t('common.adminNote')">
            <el-input v-model="assignForm.admin_note" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="submitAssign">{{ t('common.assign') }}</el-button>
          </el-form-item>
        </el-form>

        <h4>{{ t('rfqs.quoteRequests') }}</h4>
        <p v-if="!quoteRequests.length" class="muted">—</p>
        <el-table v-else :data="quoteRequests" size="small">
          <el-table-column prop="supplier_name" :label="t('rfqs.supplier')" />
          <el-table-column prop="status" :label="t('common.status')" width="120" />
          <el-table-column prop="deadline" :label="t('common.deadline')" width="120" />
          <el-table-column prop="is_urgent" :label="t('rfqs.urgent')" width="80">
            <template #default="{ row }">{{ row.is_urgent ? '✓' : '—' }}</template>
          </el-table-column>
          <el-table-column prop="admin_note" :label="t('common.adminNote')" />
          <el-table-column :label="t('common.actions')" width="180">
            <template #default="{ row }">
              <el-button v-if="row.status === 'quoted'" size="small" @click="onReviseQuoteRequest(row)">
                {{ t('rfqs.revise') }}
              </el-button>
              <el-button
                v-if="row.status === 'assigned' || row.status === 'viewed'"
                size="small"
                type="danger"
                @click="onCancelQuoteRequest(row)"
              >
                {{ t('rfqs.cancelAssign') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <h4>{{ t('rfqs.attachments') }}</h4>
        <p v-if="!detail.attachments?.length" class="muted">—</p>
        <ul v-else class="att-list">
          <li v-for="a in detail.attachments" :key="a.id">
            <a :href="a.url" target="_blank" rel="noopener">{{ a.file_name }}</a>
            <span class="muted"> ({{ Math.round(a.size / 1024) }} KB)</span>
          </li>
        </ul>

        <h4>{{ t('rfqs.quotes') }}</h4>
        <el-table :data="detail.quotes" size="small">
          <el-table-column prop="supplier_name" :label="t('rfqs.supplier')" />
          <el-table-column prop="price_amount" :label="t('rfqs.price')" />
          <el-table-column prop="currency" label="Currency" width="90" />
          <el-table-column prop="lead_time_days" :label="t('rfqs.leadTime')" width="90" />
          <el-table-column prop="unit_price" :label="t('rfqs.unitPrice')" width="90" />
          <el-table-column prop="mold_fee" :label="t('rfqs.moldFee')" width="90" />
          <el-table-column prop="moq" :label="t('rfqs.moq')" width="70" />
          <el-table-column :label="t('common.planLabel')" width="120">
            <template #default="{ row }"><el-input v-model="row.plan_label" size="small" /></template>
          </el-table-column>
          <el-table-column :label="t('common.customerVisible')" width="110">
            <template #default="{ row }"><el-switch v-model="row.is_customer_visible" /></template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="90">
            <template #default="{ row }"><el-button size="small" type="primary" @click="saveQuote(row)">{{ t('common.save') }}</el-button></template>
          </el-table-column>
        </el-table>

        <h4>{{ t('rfqs.createQuote') }}</h4>
        <el-form :inline="true" class="quote-form">
          <el-form-item :label="t('rfqs.price')">
            <el-input-number v-model="quoteForm.price_amount" :min="0" />
          </el-form-item>
          <el-form-item :label="t('rfqs.unitPrice')">
            <el-input-number v-model="quoteForm.unit_price" :min="0" />
          </el-form-item>
          <el-form-item :label="t('rfqs.moldFee')">
            <el-input-number v-model="quoteForm.mold_fee" :min="0" />
          </el-form-item>
          <el-form-item :label="t('rfqs.sampleFee')">
            <el-input-number v-model="quoteForm.sample_fee" :min="0" />
          </el-form-item>
          <el-form-item :label="t('rfqs.moq')">
            <el-input-number v-model="quoteForm.moq" :min="1" />
          </el-form-item>
          <el-form-item :label="t('rfqs.paymentTerms')">
            <el-input v-model="quoteForm.payment_terms" style="width: 120px" />
          </el-form-item>
          <el-form-item :label="t('rfqs.leadTime')">
            <el-input-number v-model="quoteForm.lead_time_days" :min="0" />
          </el-form-item>
          <el-form-item :label="t('common.planLabel')">
            <el-input v-model="quoteForm.plan_label" style="width: 100px" />
          </el-form-item>
          <el-form-item :label="t('common.customerVisible')">
            <el-switch v-model="quoteForm.is_customer_visible" />
          </el-form-item>
          <el-form-item :label="t('rfqs.note')">
            <el-input v-model="quoteForm.note" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="submitQuote">{{ t('rfqs.createQuote') }}</el-button>
          </el-form-item>
        </el-form>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.att-list { padding-left: 1.2rem; }
.muted { color: #909399; }
h4 { margin: 1rem 0 0.5rem; }
</style>
