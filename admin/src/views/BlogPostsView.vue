<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import RichTextEditor from '../components/RichTextEditor.vue'
import {
  blogCategoryList,
  blogPostCreate,
  blogPostDelete,
  blogPostList,
  blogPostUpdate,
  uploadAdminMedia,
} from '../api'

const { t } = useI18n()
const items = ref([])
const categories = ref([])
const dialog = ref(false)
const saving = ref(false)
const editingId = ref(null)
const tagText = ref('')

const emptyForm = () => ({
  title: '',
  summary: '',
  content: '',
  cover_image: '',
  category: null,
  language: 'ko',
  status: 'published',
  is_pinned: false,
  is_featured: false,
})

const form = ref(emptyForm())

const load = async () => {
  const [posts, cats] = await Promise.all([blogPostList(), blogCategoryList()])
  items.value = posts.data.items || []
  categories.value = cats.data.items || []
}
onMounted(load)

const categoryName = (id) => categories.value.find((item) => item.id === id)?.name || '—'

const openCreate = () => {
  editingId.value = null
  form.value = emptyForm()
  tagText.value = ''
  dialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = {
    title: row.title || '',
    summary: row.summary || '',
    content: row.content || '',
    cover_image: row.cover_image || '',
    category: row.category,
    language: row.language || 'ko',
    status: row.status || 'draft',
    is_pinned: Boolean(row.is_pinned),
    is_featured: Boolean(row.is_featured),
  }
  tagText.value = Array.isArray(row.tags) ? row.tags.join(', ') : ''
  dialog.value = true
}

const uploadCover = async (option) => {
  const formData = new FormData()
  formData.append('file', option.file)
  try {
    const res = await uploadAdminMedia(formData)
    form.value.cover_image = res.data?.url || ''
    option.onSuccess(res)
  } catch (error) {
    option.onError(error)
    ElMessage.error(error?.message || t('blog.uploadFailed'))
  }
}

const submit = async () => {
  if (!form.value.title.trim()) {
    ElMessage.warning(t('blog.titleRequired'))
    return
  }
  const payload = {
    ...form.value,
    category: form.value.category || null,
    tags: tagText.value.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
  }
  saving.value = true
  try {
    if (editingId.value) await blogPostUpdate(editingId.value, payload)
    else await blogPostCreate(payload)
    dialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(error?.message || t('blog.saveFailed'))
  } finally {
    saving.value = false
  }
}

const remove = async (row) => {
  await ElMessageBox.confirm(t('common.deleteConfirm'), t('common.delete'), {
    type: 'warning',
    confirmButtonText: t('common.delete'),
    cancelButtonText: t('common.cancel'),
  })
  await blogPostDelete(row.id)
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('blog.title') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" :label="t('common.title')" min-width="180" />
      <el-table-column :label="t('blog.category')" width="120">
        <template #default="{ row }">{{ categoryName(row.category) }}</template>
      </el-table-column>
      <el-table-column prop="language" :label="t('blog.language')" width="80" />
      <el-table-column :label="t('blog.status')" width="100">
        <template #default="{ row }">{{ row.status === 'published' ? t('blog.published') : t('blog.draft') }}</template>
      </el-table-column>
      <el-table-column prop="view_count" :label="t('blog.views')" width="80" />
      <el-table-column :label="t('common.actions')" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button size="small" type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialog"
      :title="editingId ? t('blog.editTitle') : t('blog.createTitle')"
      width="860px"
      destroy-on-close
    >
      <el-form label-width="100px">
        <el-form-item :label="t('common.title')">
          <el-input v-model="form.title" maxlength="200" />
        </el-form-item>
        <el-form-item :label="t('blog.category')">
          <el-select v-model="form.category" clearable style="width: 100%">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('blog.language')">
          <el-select v-model="form.language" style="width: 160px">
            <el-option label="한국어" value="ko" />
            <el-option label="中文" value="zh" />
            <el-option label="English" value="en" />
            <el-option label="日本語" value="ja" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('blog.tags')">
          <el-input v-model="tagText" :placeholder="t('blog.tagsHint')" />
        </el-form-item>
        <el-form-item :label="t('blog.cover')">
          <el-input v-model="form.cover_image" />
          <el-upload :show-file-list="false" accept="image/*" :http-request="uploadCover">
            <el-button style="margin-top: 8px">{{ t('blog.uploadCover') }}</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item :label="t('common.summary')">
          <el-input v-model="form.summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item :label="t('common.content')">
          <RichTextEditor v-model="form.content" />
        </el-form-item>
        <el-form-item :label="t('blog.status')">
          <el-radio-group v-model="form.status">
            <el-radio value="published">{{ t('blog.published') }}</el-radio>
            <el-radio value="draft">{{ t('blog.draft') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="t('blog.pinned')">
          <el-switch v-model="form.is_pinned" />
        </el-form-item>
        <el-form-item :label="t('blog.featured')">
          <el-switch v-model="form.is_featured" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" :loading="saving" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
</style>
