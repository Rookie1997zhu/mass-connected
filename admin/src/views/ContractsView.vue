<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchContracts } from '../api'

const { t } = useI18n()
const items = ref([])

const load = async () => {
  const res = await fetchContracts()
  items.value = res.data.items || []
}
onMounted(load)
</script>

<template>
  <div>
    <h2>{{ t('nav.contracts') }}</h2>
    <el-table :data="items">
      <el-table-column prop="contract_no" label="No" width="180" />
      <el-table-column prop="buyer_email" :label="t('common.email')" />
      <el-table-column prop="amount" :label="t('common.amount')" />
      <el-table-column prop="status" :label="t('common.status')" width="130" />
      <el-table-column :label="t('common.download')" width="120">
        <template #default="{ row }">
          <el-link v-if="row.pdf_url" :href="row.pdf_url" target="_blank" type="primary">{{ t('common.download') }}</el-link>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
