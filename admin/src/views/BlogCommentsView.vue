<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { blogCommentDelete, blogCommentList, blogCommentUpdate } from '../api'

const { t } = useI18n()
const items = ref([])

const load = async () => {
  const res = await blogCommentList()
  items.value = res.data.items || []
}
onMounted(load)

const toggleHidden = async (row) => {
  await blogCommentUpdate(row.id, { is_hidden: row.is_hidden })
}

const remove = async (row) => {
  await ElMessageBox.confirm(t('common.deleteConfirm'), t('common.delete'), {
    type: 'warning',
    confirmButtonText: t('common.delete'),
    cancelButtonText: t('common.cancel'),
  })
  await blogCommentDelete(row.id)
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('blog.comments') }}</h2>
    </div>
    <el-table :data="items">
      <el-table-column prop="post_title" :label="t('blog.post')" min-width="140" />
      <el-table-column prop="author_name" :label="t('blog.author')" width="120" />
      <el-table-column prop="content" :label="t('blog.comment')" min-width="220" />
      <el-table-column :label="t('blog.hidden')" width="100">
        <template #default="{ row }">
          <el-switch v-model="row.is_hidden" @change="toggleHidden(row)" />
        </template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="100">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
</style>
