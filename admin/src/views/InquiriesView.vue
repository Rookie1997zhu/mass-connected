<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchInquiries, fetchInquiry, updateInquiry } from '../api'

const { t } = useI18n()
const items = ref([])
const detailDialog = ref(false)
const detail = ref(null)

const load = async () => {
  const res = await fetchInquiries()
  items.value = res.data.items || []
}
onMounted(load)

const openDetail = async (row) => {
  const res = await fetchInquiry(row.id)
  detail.value = res.data
  detailDialog.value = true
}

const setStatus = async (status) => {
  await updateInquiry(detail.value.id, { status })
  const res = await fetchInquiry(detail.value.id)
  detail.value = res.data
  await load()
}
</script>

<template>
  <div>
    <h2>{{ t('inquiries.title') }}</h2>
    <el-table :data="items">
      <el-table-column prop="name" :label="t('common.name')" />
      <el-table-column prop="email" :label="t('common.email')" />
      <el-table-column prop="product_interest" :label="t('common.product')" />
      <el-table-column prop="status" :label="t('common.status')" />
      <el-table-column :label="t('common.actions')" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openDetail(row)">{{ t('inquiries.detail') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="detailDialog" :title="t('inquiries.detail')" width="560px" destroy-on-close>
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item :label="t('common.name')">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.email')">{{ detail.email }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.phone')">{{ detail.phone || '—' }}</el-descriptions-item>
          <el-descriptions-item :label="t('inquiries.company')">{{ detail.company || '—' }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.product')">{{ detail.product_interest || '—' }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.status')">{{ detail.status }}</el-descriptions-item>
          <el-descriptions-item :label="t('inquiries.message')">{{ detail.message || '—' }}</el-descriptions-item>
          <el-descriptions-item :label="t('inquiries.source')">{{ detail.source || '—' }}</el-descriptions-item>
          <el-descriptions-item :label="t('inquiries.createdAt')">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>
        <div class="actions">
          <el-button @click="setStatus('contacted')">{{ t('common.contacted') }}</el-button>
          <el-button @click="setStatus('quoted')">{{ t('inquiries.markQuoted') }}</el-button>
          <el-button @click="setStatus('closed')">{{ t('inquiries.markClosed') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.actions { margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
</style>
