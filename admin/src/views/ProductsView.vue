<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiLangInput from '../components/MultiLangInput.vue'
import { fetchCategories, fetchProducts, saveProduct, updateProduct } from '../api'
import { emptyI18n, normalizeI18n } from '../utils/i18nField'

const { t } = useI18n()
const items = ref([])
const categories = ref([])
const dialog = ref(false)
const editingId = ref(null)
const emptyForm = () => ({
  category: null,
  sku: '',
  name: emptyI18n(),
  description: emptyI18n(),
  price_amount: 0,
  stock: 0,
  is_active: true,
  is_shop_visible: true,
})
const form = ref(emptyForm())

const load = async () => {
  const [prodRes, catRes] = await Promise.all([fetchProducts(), fetchCategories()])
  items.value = prodRes.data.items || []
  categories.value = catRes.data.items || []
}
onMounted(load)

const openCreate = () => {
  editingId.value = null
  form.value = emptyForm()
  dialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = {
    category: row.category,
    sku: row.sku,
    name: normalizeI18n(row.name),
    description: normalizeI18n(row.description || {}),
    price_amount: row.price_amount,
    stock: row.stock,
    is_active: row.is_active,
    is_shop_visible: row.is_shop_visible,
  }
  dialog.value = true
}

const submit = async () => {
  if (editingId.value) await updateProduct(editingId.value, form.value)
  else await saveProduct(form.value)
  dialog.value = false
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('products.title') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="sku" :label="t('common.sku')" width="120" />
      <el-table-column :label="t('common.product')">
        <template #default="{ row }">{{ row.name_text || row.name?.ko }}</template>
      </el-table-column>
      <el-table-column prop="price_amount" :label="t('common.price')" />
      <el-table-column prop="stock" :label="t('common.stock')" width="90" />
      <el-table-column :label="t('common.actions')" width="100">
        <template #default="{ row }"><el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button></template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialog" :title="editingId ? t('products.editTitle') : t('products.createTitle')" width="640px">
      <el-form label-width="100px">
        <el-form-item :label="t('common.sku')"><el-input v-model="form.sku" /></el-form-item>
        <el-form-item :label="t('products.category')">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name?.ko || c.slug" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.name')"><MultiLangInput v-model="form.name" /></el-form-item>
        <el-form-item :label="t('common.summary')"><MultiLangInput v-model="form.description" type="textarea" /></el-form-item>
        <el-form-item :label="t('common.price')"><el-input-number v-model="form.price_amount" :min="0" /></el-form-item>
        <el-form-item :label="t('common.stock')"><el-input-number v-model="form.stock" :min="0" /></el-form-item>
        <el-form-item :label="t('common.active')"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">{{ t('common.cancel') }}</el-button><el-button type="primary" @click="submit">{{ t('common.save') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>.toolbar { display: flex; justify-content: space-between; margin-bottom: 1rem; }</style>
