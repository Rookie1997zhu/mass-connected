<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchOrders, updateOrder } from '../api'

const { t } = useI18n()
const items = ref([])
const statusFilter = ref('')

const load = async () => {
  const params = statusFilter.value ? { status: statusFilter.value } : {}
  const res = await fetchOrders(params)
  items.value = res.data.items || []
}

onMounted(load)

const changeStatus = async (row, status) => {
  await updateOrder(row.id, { status })
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('orders.title') }}</h2>
      <el-select v-model="statusFilter" clearable :placeholder="t('orders.filterStatus')" style="width: 180px" @change="load">
        <el-option label="pending" value="pending" />
        <el-option label="confirmed" value="confirmed" />
        <el-option label="cancelled" value="cancelled" />
      </el-select>
    </div>
    <el-table :data="items">
      <el-table-column prop="order_no" :label="t('common.orderNo')" width="180" />
      <el-table-column prop="member_email" :label="t('common.email')" />
      <el-table-column prop="total_amount" :label="t('common.amount')" />
      <el-table-column prop="status" :label="t('common.status')" width="140">
        <template #default="{ row }">
          <el-select :model-value="row.status" size="small" @change="(v) => changeStatus(row, v)">
            <el-option label="pending" value="pending" />
            <el-option label="awaiting_payment" value="awaiting_payment" />
            <el-option label="confirmed" value="confirmed" />
            <el-option label="cancelled" value="cancelled" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" :label="t('orders.date')" />
    </el-table>
  </div>
</template>

<style scoped>.toolbar { display: flex; justify-content: space-between; margin-bottom: 1rem; }</style>
