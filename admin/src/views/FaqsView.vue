<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { deleteFaq, fetchFaqs, saveFaq } from '../api'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const form = ref({ question: { ko: '', en: '' }, answer: { ko: '', en: '' }, sort_order: 0, is_active: true })

const load = async () => {
  const res = await fetchFaqs()
  items.value = res.data.items || []
}
onMounted(load)

const openCreate = () => {
  form.value = { question: { ko: '', en: '' }, answer: { ko: '', en: '' }, sort_order: 0, is_active: true }
  dialog.value = true
}

const submit = async () => {
  await saveFaq(form.value)
  dialog.value = false
  await load()
}

const remove = async (row) => {
  await deleteFaq(row.id)
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('faqs.title') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column :label="t('common.question')"><template #default="{ row }">{{ row.question?.ko }}</template></el-table-column>
      <el-table-column prop="is_active" :label="t('common.active')" />
      <el-table-column :label="t('common.actions')">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialog" :title="t('faqs.createTitle')">
      <el-form label-width="100px">
        <el-form-item :label="t('common.questionKo')"><el-input v-model="form.question.ko" type="textarea" /></el-form-item>
        <el-form-item :label="t('common.answerKo')"><el-input v-model="form.answer.ko" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="submit">{{ t('common.save') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }</style>
