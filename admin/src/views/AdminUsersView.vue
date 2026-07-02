<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchAdminUsers, saveAdminUser } from '../api'

const { t } = useI18n()
const items = ref([])
const dialog = ref(false)
const form = ref({ email: '', password: '', name: '', role: 'operator' })

const load = async () => {
  const res = await fetchAdminUsers()
  items.value = res.data.items || []
}
onMounted(load)

const openCreate = () => {
  form.value = { email: '', password: '', name: '', role: 'operator' }
  dialog.value = true
}

const submit = async () => {
  await saveAdminUser(form.value)
  dialog.value = false
  await load()
}
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>{{ t('admins.title') }}</h2>
      <el-button type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="email" :label="t('common.email')" />
      <el-table-column prop="name" :label="t('common.name')" />
      <el-table-column prop="role" :label="t('common.role')" />
      <el-table-column prop="is_active" :label="t('common.active')" />
    </el-table>
    <el-dialog v-model="dialog" :title="t('admins.createTitle')">
      <el-form label-width="100px">
        <el-form-item :label="t('common.email')"><el-input v-model="form.email" /></el-form-item>
        <el-form-item :label="t('common.password')"><el-input v-model="form.password" type="password" /></el-form-item>
        <el-form-item :label="t('common.name')"><el-input v-model="form.name" /></el-form-item>
        <el-form-item :label="t('common.role')">
          <el-select v-model="form.role">
            <el-option :label="t('roles.operator')" value="operator" />
            <el-option :label="t('roles.sales')" value="sales" />
            <el-option :label="t('roles.superAdmin')" value="super_admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="submit">{{ t('common.save') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }</style>
