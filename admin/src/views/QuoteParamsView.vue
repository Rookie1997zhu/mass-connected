<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchQuoteParams, saveQuoteParam, updateQuoteParam } from '../api'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const emptyForm = () => ({ quote_type: 'injection', param_key: '', value: 0, label: '', unit: '', note: '' })
const form = ref(emptyForm())

const load = async () => {
  const res = await fetchQuoteParams()
  items.value = res.data.items || []
}
onMounted(load)

const openCreate = () => {
  form.value = emptyForm()
  dialog.value = true
}
const submit = async () => {
  await saveQuoteParam(form.value)
  ElMessage.success(t('common.success'))
  dialog.value = false
  await load()
}
const saveRow = async (row) => {
  await updateQuoteParam(row.id, { value: row.value })
  ElMessage.success(t('common.success'))
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('nav.quoteParams') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="quote_type" :label="t('common.quoteType')" width="120" />
      <el-table-column prop="param_key" :label="t('common.paramKey')" />
      <el-table-column prop="label" :label="t('common.summary')" />
      <el-table-column :label="t('common.value')" width="160">
        <template #default="{ row }"><el-input-number v-model="row.value" size="small" :controls="false" /></template>
      </el-table-column>
      <el-table-column prop="unit" label="Unit" width="90" />
      <el-table-column :label="t('common.actions')" width="100">
        <template #default="{ row }"><el-button size="small" type="primary" @click="saveRow(row)">{{ t('common.save') }}</el-button></template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="t('common.create')" width="480px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item :label="t('common.quoteType')">
          <el-select v-model="form.quote_type">
            <el-option label="injection" value="injection" />
            <el-option label="print3d" value="print3d" />
            <el-option label="pcba" value="pcba" />
            <el-option label="pcb" value="pcb" />
            <el-option label="software" value="software" />
            <el-option label="ic" value="ic" />
            <el-option label="paper_box" value="paper_box" />
            <el-option label="shipping" value="shipping" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.paramKey')"><el-input v-model="form.param_key" /></el-form-item>
        <el-form-item :label="t('common.summary')"><el-input v-model="form.label" /></el-form-item>
        <el-form-item :label="t('common.value')"><el-input-number v-model="form.value" :controls="false" /></el-form-item>
        <el-form-item label="Unit"><el-input v-model="form.unit" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
</style>
