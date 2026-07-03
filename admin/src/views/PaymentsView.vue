<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { confirmPayment, fetchPayments } from '../api'

const { t } = useI18n()
const items = ref([])

const load = async () => {
  const res = await fetchPayments()
  items.value = res.data.items || []
}
onMounted(load)

const onConfirm = async (row) => {
  await confirmPayment(row.id)
  ElMessage.success(t('common.success'))
  await load()
}
</script>

<template>
  <div>
    <h2>{{ t('nav.payments') }}</h2>
    <el-table :data="items">
      <el-table-column prop="payment_no" label="No" width="180" />
      <el-table-column prop="buyer_email" :label="t('common.email')" />
      <el-table-column prop="amount" :label="t('common.amount')" />
      <el-table-column prop="method" :label="t('common.quoteType')" width="120" />
      <el-table-column prop="status" :label="t('common.status')" width="120" />
      <el-table-column :label="t('common.proof')" width="110">
        <template #default="{ row }">
          <el-link v-if="row.proof_url" :href="row.proof_url" target="_blank" type="primary">{{ t('common.proof') }}</el-link>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="120">
        <template #default="{ row }">
          <el-button v-if="row.status !== 'confirmed'" size="small" type="primary" @click="onConfirm(row)">{{ t('common.confirm') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
