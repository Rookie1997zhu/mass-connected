<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchQuoteTables, saveQuoteTable, updateQuoteTable } from '../api'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const editDialog = ref(false)
const filterType = ref('')
const emptyForm = () => ({ quote_type: 'shipping', table_key: '', rows: [], is_active: true })
const form = ref(emptyForm())
const rowsJson = ref('[]')
const editing = ref(null)

const load = async () => {
  const res = await fetchQuoteTables(filterType.value ? { quote_type: filterType.value } : {})
  items.value = res.data.items || []
}
onMounted(load)

const openCreate = () => {
  form.value = emptyForm()
  rowsJson.value = '[]'
  dialog.value = true
}
const openEdit = (row) => {
  editing.value = { ...row }
  rowsJson.value = JSON.stringify(row.rows || [], null, 2)
  editDialog.value = true
}
const submit = async () => {
  let rows = []
  try {
    rows = JSON.parse(rowsJson.value || '[]')
  } catch {
    ElMessage.error('Invalid JSON')
    return
  }
  await saveQuoteTable({ ...form.value, rows })
  ElMessage.success(t('common.success'))
  dialog.value = false
  await load()
}
const submitEdit = async () => {
  let rows = []
  try {
    rows = JSON.parse(rowsJson.value || '[]')
  } catch {
    ElMessage.error('Invalid JSON')
    return
  }
  await updateQuoteTable(editing.value.id, { rows, is_active: editing.value.is_active })
  ElMessage.success(t('common.success'))
  editDialog.value = false
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('nav.quoteTables') }}</h2>
      <div class="toolbar-actions">
        <el-select v-model="filterType" clearable placeholder="quote_type" style="width:140px" @change="load">
          <el-option label="shipping" value="shipping" />
          <el-option label="pcba" value="pcba" />
          <el-option label="pcb" value="pcb" />
        </el-select>
        <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
      </div>
    </div>
    <el-table :data="items">
      <el-table-column prop="quote_type" :label="t('common.quoteType')" width="100" />
      <el-table-column prop="table_key" :label="t('common.tableKey')" width="180" />
      <el-table-column :label="t('common.rows')">
        <template #default="{ row }">{{ (row.rows || []).length }} rows</template>
      </el-table-column>
      <el-table-column :label="t('common.active')" width="80">
        <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? 'Y' : 'N' }}</el-tag></template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="100">
        <template #default="{ row }"><el-button size="small" type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button></template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="t('common.create')" width="640px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item :label="t('common.quoteType')">
          <el-select v-model="form.quote_type">
            <el-option label="shipping" value="shipping" />
            <el-option label="pcba" value="pcba" />
            <el-option label="pcb" value="pcb" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.tableKey')"><el-input v-model="form.table_key" /></el-form-item>
        <el-form-item :label="t('common.rows')"><el-input v-model="rowsJson" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialog" :title="t('common.edit')" width="640px" destroy-on-close>
      <el-form v-if="editing" label-width="120px">
        <el-form-item :label="t('common.tableKey')"><el-input :model-value="editing.table_key" disabled /></el-form-item>
        <el-form-item :label="t('common.active')"><el-switch v-model="editing.is_active" /></el-form-item>
        <el-form-item :label="t('common.rows')"><el-input v-model="rowsJson" type="textarea" :rows="12" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitEdit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.toolbar-actions { display: flex; gap: 0.75rem; align-items: center; }
</style>
