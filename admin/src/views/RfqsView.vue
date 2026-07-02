<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { createRfqQuote, fetchRfq, fetchRfqs, updateRfqStatus } from '../api'

const { t } = useI18n()
const items = ref([])
const statusFilter = ref('')
const detailDialog = ref(false)
const detail = ref(null)

const RFQ_STATUSES = ['submitted', 'quoting', 'quoted', 'negotiating', 'won', 'closed']
const emptyQuote = () => ({ price_amount: null, currency: 'KRW', lead_time_days: 0, valid_until: null, note: '' })
const quoteForm = ref(emptyQuote())

const load = async () => {
  const params = statusFilter.value ? { status: statusFilter.value } : {}
  const res = await fetchRfqs(params)
  items.value = res.data.items || []
}
onMounted(load)

const openDetail = async (row) => {
  const res = await fetchRfq(row.id)
  detail.value = res.data
  quoteForm.value = emptyQuote()
  detailDialog.value = true
}

const changeStatus = async (status) => {
  const res = await updateRfqStatus(detail.value.id, status)
  detail.value = res.data
  await load()
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
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('rfqs.title') }}</h2>
      <el-select v-model="statusFilter" clearable :placeholder="t('rfqs.filterStatus')" style="width: 180px" @change="load">
        <el-option v-for="s in RFQ_STATUSES" :key="s" :label="s" :value="s" />
      </el-select>
    </div>
    <el-table :data="items">
      <el-table-column prop="rfq_no" label="RFQ No" width="180" />
      <el-table-column prop="service_category_name" :label="t('rfqs.category')" />
      <el-table-column prop="quantity" :label="t('rfqs.quantity')" width="90" />
      <el-table-column prop="quotes_count" :label="t('rfqs.quotes')" width="90" />
      <el-table-column prop="status" :label="t('common.status')" width="120" />
      <el-table-column :label="t('common.actions')" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openDetail(row)">{{ t('rfqs.detail') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="detailDialog" :title="t('rfqs.detail')" width="820px" destroy-on-close>
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="RFQ No">{{ detail.rfq_no }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.status')">
            <el-select :model-value="detail.status" style="width: 160px" @change="changeStatus">
              <el-option v-for="s in RFQ_STATUSES" :key="s" :label="s" :value="s" />
            </el-select>
          </el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.buyer')">{{ detail.buyer_name }} ({{ detail.buyer_email }})</el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.category')">{{ detail.service_category_name }}</el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.quantity')">{{ detail.quantity }}</el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.material')">{{ detail.material }}</el-descriptions-item>
          <el-descriptions-item label="Tolerance">{{ detail.tolerance }}</el-descriptions-item>
          <el-descriptions-item label="Finish">{{ detail.surface_finish }}</el-descriptions-item>
          <el-descriptions-item :label="t('rfqs.note')" :span="2">{{ detail.remark }}</el-descriptions-item>
        </el-descriptions>

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
          <el-table-column prop="supplier_type" :label="t('rfqs.supplierType')" width="100" />
          <el-table-column prop="price_amount" :label="t('rfqs.price')" />
          <el-table-column prop="currency" label="Currency" width="90" />
          <el-table-column prop="lead_time_days" :label="t('rfqs.leadTime')" />
          <el-table-column prop="valid_until" :label="t('rfqs.validUntil')" />
          <el-table-column prop="status" :label="t('common.status')" width="100" />
        </el-table>

        <h4>{{ t('rfqs.createQuote') }}</h4>
        <el-form :inline="true">
          <el-form-item :label="t('rfqs.price')">
            <el-input-number v-model="quoteForm.price_amount" :min="0" />
          </el-form-item>
          <el-form-item :label="t('rfqs.leadTime')">
            <el-input-number v-model="quoteForm.lead_time_days" :min="0" />
          </el-form-item>
          <el-form-item :label="t('rfqs.validUntil')">
            <el-date-picker v-model="quoteForm.valid_until" type="date" value-format="YYYY-MM-DD" />
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
