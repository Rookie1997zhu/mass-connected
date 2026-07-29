<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchContracts } from '../api'
import { openAuthedFile } from '../utils/downloadAuthedFile'

const { t } = useI18n()
const items = ref([])

const load = async () => {
  const res = await fetchContracts()
  items.value = res.data.items || []
}
onMounted(load)

const onOpenPdf = async (row) => {
  try {
    await openAuthedFile(row.pdf_url)
  } catch {
    ElMessage.error(t('common.failed') || 'Failed')
  }
}
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
          <el-button
            v-if="row.pdf_url"
            link
            type="primary"
            @click="onOpenPdf(row)"
          >{{ t('common.download') }}</el-button>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
