<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { createProjectTodo, fetchProject, fetchProjects, updateProject } from '../api'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const detail = ref(null)
const todoForm = ref({ title: '', assignee_type: 'customer', due_date: null })

const load = async () => {
  const res = await fetchProjects()
  items.value = res.data.items || []
}
onMounted(load)

const openDetail = async (row) => {
  const res = await fetchProject(row.id)
  detail.value = res.data
  todoForm.value = { title: '', assignee_type: 'customer', due_date: null }
  dialog.value = true
}

const saveProgress = async () => {
  await updateProject(detail.value.id, {
    status: detail.value.status,
    progress_percent: detail.value.progress_percent,
  })
  ElMessage.success(t('common.success'))
  dialog.value = false
  await load()
}

const addTodo = async () => {
  if (!todoForm.value.title.trim()) {
    ElMessage.warning(t('projects.todoTitleRequired'))
    return
  }
  await createProjectTodo(detail.value.id, todoForm.value)
  const res = await fetchProject(detail.value.id)
  detail.value = res.data
  todoForm.value = { title: '', assignee_type: 'customer', due_date: null }
  ElMessage.success(t('common.success'))
}
</script>

<template>
  <div>
    <h2>{{ t('nav.projects') }}</h2>
    <el-table :data="items" @row-click="openDetail">
      <el-table-column prop="project_no" label="No" width="180" />
      <el-table-column prop="title" :label="t('common.title')" />
      <el-table-column prop="buyer_email" :label="t('common.email')" />
      <el-table-column prop="status" :label="t('common.status')" width="130" />
      <el-table-column :label="t('common.progress')" width="180">
        <template #default="{ row }"><el-progress :percentage="row.progress || 0" /></template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="detail?.title" width="620px" destroy-on-close>
      <template v-if="detail">
        <el-form label-width="120px">
          <el-form-item :label="t('common.status')">
            <el-select v-model="detail.status">
              <el-option label="pending" value="pending" />
              <el-option label="in_progress" value="in_progress" />
              <el-option label="paused" value="paused" />
              <el-option label="completed" value="completed" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('common.progress')">
            <el-input-number v-model="detail.progress_percent" :min="0" :max="100" />
          </el-form-item>
        </el-form>
        <h4>{{ t('common.progress') }}</h4>
        <el-timeline>
          <el-timeline-item v-for="s in (detail.stages || [])" :key="s.id" :type="s.status === 'completed' ? 'success' : 'primary'">
            {{ s.name }} - {{ s.status }}
          </el-timeline-item>
        </el-timeline>

        <h4>{{ t('projects.todos') }}</h4>
        <ul v-if="detail.todos?.length" class="todo-list">
          <li v-for="td in detail.todos" :key="td.id">
            {{ td.title }} <span class="muted">({{ td.assignee_type }})</span>
          </li>
        </ul>
        <p v-else class="muted">—</p>
        <el-form :inline="true" class="todo-form">
          <el-form-item :label="t('projects.todoTitle')">
            <el-input v-model="todoForm.title" style="width: 200px" />
          </el-form-item>
          <el-form-item :label="t('projects.assignee')">
            <el-select v-model="todoForm.assignee_type" style="width: 120px">
              <el-option value="customer" label="customer" />
              <el-option value="supplier" label="supplier" />
              <el-option value="admin" label="admin" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="addTodo">{{ t('common.create') }}</el-button>
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveProgress">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
h4 { margin: 1rem 0 0.5rem; }
.muted { color: #909399; font-size: 0.85rem; }
.todo-list { padding-left: 1.2rem; margin: 0 0 0.75rem; }
.todo-form { margin-top: 0.5rem; }
</style>
