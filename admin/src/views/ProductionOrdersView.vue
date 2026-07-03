<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchProductionOrders, updateProductionOrder } from '../api'

const { t } = useI18n()
const items = ref([])
const statusFilter = ref('')

const load = async () => {
  const params = statusFilter.value ? { status: statusFilter.value } : {}
  const res = await fetchProductionOrders(params)
  items.value = res.data.items || []
}

onMounted(load)

const setStatus = async (row, status) => {
  await updateProductionOrder(row.id, { status })
  ElMessage.success(t('common.save'))
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('productionOrders.title') }}</h2>
      <el-select v-model="statusFilter" clearable :placeholder="t('productionOrders.filterStatus')" style="width: 180px" @change="load">
        <el-option label="pending_confirm" value="pending_confirm" />
        <el-option label="confirmed" value="confirmed" />
        <el-option label="in_production" value="in_production" />
        <el-option label="completed" value="completed" />
        <el-option label="cancelled" value="cancelled" />
      </el-select>
    </div>
    <el-table :data="items">
      <el-table-column prop="order_no" :label="t('productionOrders.orderNo')" width="160" />
      <el-table-column prop="rfq_no" :label="t('productionOrders.rfqNo')" width="140" />
      <el-table-column prop="buyer_email" :label="t('productionOrders.buyer')" />
      <el-table-column prop="supplier_name" :label="t('productionOrders.supplier')" />
      <el-table-column prop="price_amount" :label="t('productionOrders.amount')" width="120" />
      <el-table-column prop="status" :label="t('common.status')" width="140" />
      <el-table-column :label="t('common.actions')" width="260">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending_confirm'" size="small" type="success" @click="setStatus(row, 'confirmed')">
            {{ t('productionOrders.markConfirmed') }}
          </el-button>
          <el-button v-if="row.status === 'confirmed'" size="small" @click="setStatus(row, 'in_production')">
            {{ t('productionOrders.markInProduction') }}
          </el-button>
          <el-button v-if="row.status === 'in_production'" size="small" type="primary" @click="setStatus(row, 'completed')">
            {{ t('productionOrders.markCompleted') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
</style>
