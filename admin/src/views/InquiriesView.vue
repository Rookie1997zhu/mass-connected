<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchInquiries, updateInquiry } from '../api'

const { t } = useI18n()
const items = ref([])
const load = async () => {
  const res = await fetchInquiries()
  items.value = res.data.items || []
}
onMounted(load)

const setStatus = async (row, status) => {
  await updateInquiry(row.id, { status })
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
      <el-table-column :label="t('common.actions')">
        <template #default="{ row }">
          <el-button size="small" @click="setStatus(row, 'contacted')">{{ t('common.contacted') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
