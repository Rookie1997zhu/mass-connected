<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  blogCategoryCreate,
  blogCategoryDelete,
  blogCategoryList,
  blogCategoryUpdate,
} from '../api'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const editingId = ref(null)
const form = ref({ name: '', slug: '', sort_order: 0, is_active: true })

const load = async () => {
  const res = await blogCategoryList()
  items.value = res.data.items || []
}
onMounted(load)

const openCreate = () => {
  editingId.value = null
  form.value = { name: '', slug: '', sort_order: 0, is_active: true }
  dialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = {
    name: row.name,
    slug: row.slug,
    sort_order: row.sort_order,
    is_active: row.is_active,
  }
  dialog.value = true
}

const submit = async () => {
  try {
    if (editingId.value) await blogCategoryUpdate(editingId.value, form.value)
    else await blogCategoryCreate(form.value)
    dialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(error?.message || t('blog.saveFailed'))
  }
}

const remove = async (row) => {
  await ElMessageBox.confirm(t('common.deleteConfirm'), t('common.delete'), {
    type: 'warning',
    confirmButtonText: t('common.delete'),
    cancelButtonText: t('common.cancel'),
  })
  await blogCategoryDelete(row.id)
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('blog.categories') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="name" :label="t('blog.categoryName')" />
      <el-table-column prop="slug" :label="t('blog.slug')" />
      <el-table-column prop="sort_order" :label="t('blog.sortOrder')" width="100" />
      <el-table-column prop="is_active" :label="t('blog.active')" width="100" />
      <el-table-column :label="t('common.actions')" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button size="small" type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialog" :title="editingId ? t('blog.editCategory') : t('blog.createCategory')" width="480px">
      <el-form label-width="100px">
        <el-form-item :label="t('blog.categoryName')"><el-input v-model="form.name" /></el-form-item>
        <el-form-item :label="t('blog.slug')"><el-input v-model="form.slug" /></el-form-item>
        <el-form-item :label="t('blog.sortOrder')"><el-input-number v-model="form.sort_order" :min="0" /></el-form-item>
        <el-form-item :label="t('blog.active')"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
</style>
