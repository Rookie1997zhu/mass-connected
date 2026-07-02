<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchFactories, updateFactory } from '../api'

const { t } = useI18n()
const items = ref([])
const statusFilter = ref('')

const load = async () => {
  const params = statusFilter.value ? { status: statusFilter.value } : {}
  const res = await fetchFactories(params)
  items.value = res.data.items || []
}

onMounted(load)

const setStatus = async (row, status) => {
  await updateFactory(row.id, { status })
  ElMessage.success(t('common.save'))
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('factories.title') }}</h2>
      <el-select v-model="statusFilter" clearable :placeholder="t('factories.filterStatus')" style="width: 180px" @change="load">
        <el-option label="pending" value="pending" />
        <el-option label="approved" value="approved" />
        <el-option label="rejected" value="rejected" />
      </el-select>
    </div>
    <el-table :data="items">
      <el-table-column prop="company_name" :label="t('factories.company')" />
      <el-table-column prop="email" :label="t('common.email')" />
      <el-table-column prop="name" :label="t('common.name')" />
      <el-table-column prop="region" :label="t('factories.region')" />
      <el-table-column prop="status" :label="t('common.status')" width="110" />
      <el-table-column :label="t('common.actions')" width="220">
        <template #default="{ row }">
          <el-button v-if="row.status !== 'approved'" size="small" type="success" @click="setStatus(row, 'approved')">
            {{ t('factories.approve') }}
          </el-button>
          <el-button v-if="row.status !== 'rejected'" size="small" type="warning" @click="setStatus(row, 'rejected')">
            {{ t('factories.reject') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
</style>
