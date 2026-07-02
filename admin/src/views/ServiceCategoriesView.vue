<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiLangInput from '../components/MultiLangInput.vue'
import { fetchServiceCategories, saveServiceCategory, updateServiceCategory } from '../api'
import { emptyI18n, normalizeI18n } from '../utils/i18nField'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const editingId = ref(null)

const emptyForm = () => ({
  parent: null,
  name: emptyI18n(),
  slug: '',
  icon: '',
  sort_order: 0,
  is_active: true,
})
const form = ref(emptyForm())

const tree = computed(() => {
  const byId = {}
  items.value.forEach((it) => {
    byId[it.id] = { ...it, children: [] }
  })
  const roots = []
  items.value.forEach((it) => {
    if (it.parent && byId[it.parent]) byId[it.parent].children.push(byId[it.id])
    else roots.push(byId[it.id])
  })
  Object.values(byId).forEach((node) => {
    if (!node.children.length) delete node.children
  })
  return roots
})

const parentOptions = computed(() =>
  items.value.filter((it) => it.id !== editingId.value),
)

const load = async () => {
  const res = await fetchServiceCategories()
  items.value = res.data.items || []
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
    parent: row.parent,
    name: normalizeI18n(row.name),
    slug: row.slug,
    icon: row.icon,
    sort_order: row.sort_order,
    is_active: row.is_active,
  }
  dialog.value = true
}

const submit = async () => {
  if (editingId.value) await updateServiceCategory(editingId.value, form.value)
  else await saveServiceCategory(form.value)
  dialog.value = false
  await load()
}

const toggleActive = async (row) => {
  await updateServiceCategory(row.id, { is_active: !row.is_active })
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('serviceCategories.title') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="tree" row-key="id" :tree-props="{ children: 'children' }" default-expand-all>
      <el-table-column :label="t('common.name')">
        <template #default="{ row }">{{ row.name?.ko || row.name?.zh || row.name?.en }}</template>
      </el-table-column>
      <el-table-column prop="slug" :label="t('common.slug')" />
      <el-table-column prop="sort_order" :label="t('serviceCategories.sortOrder')" width="90" />
      <el-table-column :label="t('common.active')" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? t('common.active') : '—' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="220">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button
            size="small"
            :type="row.is_active ? 'warning' : 'success'"
            @click="toggleActive(row)"
          >
            {{ row.is_active ? t('serviceCategories.disable') : t('serviceCategories.enable') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialog"
      :title="editingId ? t('serviceCategories.editTitle') : t('serviceCategories.createTitle')"
      width="720px"
      destroy-on-close
    >
      <el-form label-width="110px">
        <el-form-item :label="t('serviceCategories.parent')">
          <el-select v-model="form.parent" clearable :placeholder="t('serviceCategories.none')">
            <el-option
              v-for="opt in parentOptions"
              :key="opt.id"
              :label="opt.name?.ko || opt.name?.zh || opt.name?.en"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.name')">
          <MultiLangInput v-model="form.name" />
        </el-form-item>
        <el-form-item :label="t('common.slug')"><el-input v-model="form.slug" /></el-form-item>
        <el-form-item label="Icon"><el-input v-model="form.icon" /></el-form-item>
        <el-form-item :label="t('serviceCategories.sortOrder')">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item :label="t('common.active')"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="submit">{{ t('common.save') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }</style>
