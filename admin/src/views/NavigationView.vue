<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiLangInput from '../components/MultiLangInput.vue'
import { deleteNavigationItem, fetchNavigation, saveNavigationItem, updateNavigationItem } from '../api'
import { emptyI18n, normalizeI18n } from '../utils/i18nField'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const editingId = ref(null)

const emptyForm = () => ({
  parent: null,
  label: emptyI18n(),
  path: '',
  sort_order: 0,
  is_active: true,
  open_in_new_tab: false,
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

const groupOptions = computed(() => items.value.filter((it) => !it.parent && it.id !== editingId.value))

const isChildForm = computed(() => Boolean(form.value.parent))

const load = async () => {
  const res = await fetchNavigation()
  items.value = res.data.items || []
}
onMounted(load)

const openCreate = (parentId = null) => {
  editingId.value = null
  form.value = { ...emptyForm(), parent: parentId }
  dialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = {
    parent: row.parent,
    label: normalizeI18n(row.label),
    path: row.path || '',
    sort_order: row.sort_order,
    is_active: row.is_active,
    open_in_new_tab: row.open_in_new_tab,
  }
  dialog.value = true
}

const submit = async () => {
  const payload = { ...form.value }
  if (!payload.parent) payload.path = ''
  if (editingId.value) await updateNavigationItem(editingId.value, payload)
  else await saveNavigationItem(payload)
  dialog.value = false
  await load()
}

const toggleActive = async (row) => {
  await updateNavigationItem(row.id, { is_active: !row.is_active })
  await load()
}

const remove = async (row) => {
  if (!window.confirm(t('common.deleteConfirm'))) return
  await deleteNavigationItem(row.id)
  await load()
}

const displayLabel = (row) => row.label?.ko || row.label?.zh || row.label?.en || '—'
</script>

<template>
  <div>
    <div class="toolbar">
      <div>
        <h2>{{ t('navigation.title') }}</h2>
        <p class="hint">{{ t('navigation.hint') }}</p>
      </div>
      <el-button type="primary" @click="openCreate(null)">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="tree" row-key="id" :tree-props="{ children: 'children' }" default-expand-all>
      <el-table-column :label="t('common.name')">
        <template #default="{ row }">{{ displayLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="path" :label="t('navigation.path')" min-width="180" />
      <el-table-column prop="sort_order" :label="t('navigation.sortOrder')" width="90" />
      <el-table-column :label="t('common.active')" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? t('common.active') : '—' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="320">
        <template #default="{ row }">
          <el-button v-if="!row.parent" size="small" @click="openCreate(row.id)">
            {{ t('navigation.addChild') }}
          </el-button>
          <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button
            size="small"
            :type="row.is_active ? 'warning' : 'success'"
            @click="toggleActive(row)"
          >
            {{ row.is_active ? t('navigation.disable') : t('navigation.enable') }}
          </el-button>
          <el-button size="small" type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialog"
      :title="editingId ? t('navigation.editTitle') : t('navigation.createTitle')"
      width="720px"
      destroy-on-close
    >
      <el-form label-width="120px">
        <el-form-item v-if="!editingId || form.parent" :label="t('navigation.parent')">
          <el-select v-model="form.parent" clearable :placeholder="t('navigation.none')">
            <el-option
              v-for="opt in groupOptions"
              :key="opt.id"
              :label="displayLabel(opt)"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.name')">
          <MultiLangInput v-model="form.label" />
        </el-form-item>
        <el-form-item v-if="isChildForm || form.parent" :label="t('navigation.path')">
          <el-input v-model="form.path" :placeholder="t('navigation.pathPlaceholder')" />
        </el-form-item>
        <el-form-item v-if="isChildForm || form.parent" :label="t('navigation.newTab')">
          <el-switch v-model="form.open_in_new_tab" />
        </el-form-item>
        <el-form-item :label="t('navigation.sortOrder')">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item :label="t('common.active')"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="submit">{{ t('common.save') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
}
.toolbar-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}
.hint {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: #6b7280;
}
</style>
