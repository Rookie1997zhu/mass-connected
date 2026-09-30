<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchOpsBehavior } from '../api'
import AdminPageHeader from '../components/AdminPageHeader.vue'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const isSuperAdmin = computed(() => auth.user?.role === 'super_admin')
const behavior = ref(null)
const errorText = ref('')
const loading = ref(false)
const days = ref(7)

const loadBehavior = async () => {
  loading.value = true
  errorText.value = ''
  try {
    const res = await fetchOpsBehavior({ days: days.value })
    behavior.value = res.data
  } catch (error) {
    errorText.value = error?.message || t('ops.loadFailed')
  } finally {
    loading.value = false
  }
}

const onDays = (value) => {
  days.value = Number(value)
  loadBehavior()
}

onMounted(() => {
  if (isSuperAdmin.value) loadBehavior()
})
</script>

<template>
  <div v-if="!isSuperAdmin" class="forbidden">{{ t('ops.forbidden') }}</div>
  <div v-else>
    <AdminPageHeader :title="t('nav.opsBehavior')" :note="t('ops.behaviorNote')">
      <el-radio-group :model-value="days" @change="onDays">
        <el-radio-button :label="7">{{ t('ops.days7') }}</el-radio-button>
        <el-radio-button :label="30">{{ t('ops.days30') }}</el-radio-button>
      </el-radio-group>
    </AdminPageHeader>
    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <p v-else-if="errorText" class="error">{{ errorText }}</p>
    <template v-else-if="behavior">
      <div class="stat-grid">
        <div class="stat-card">
          <span class="stat-num">{{ behavior.totals.new_members }}</span>
          <span class="stat-label">{{ t('ops.newMembers') }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ behavior.totals.rfqs }}</span>
          <span class="stat-label">{{ t('ops.rfqs') }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ behavior.totals.orders }}</span>
          <span class="stat-label">{{ t('ops.orders') }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ behavior.totals.inquiries }}</span>
          <span class="stat-label">{{ t('ops.inquiries') }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ behavior.totals.members_logged_in }}</span>
          <span class="stat-label">{{ t('ops.loggedIn') }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ behavior.totals.blog_views }}</span>
          <span class="stat-label">{{ t('ops.blogViews') }}</span>
          <span class="stat-sub">{{ t('ops.blogViewsNote') }}</span>
        </div>
      </div>
      <div class="panel">
        <el-table :data="behavior.daily" size="small">
          <el-table-column prop="date" :label="t('ops.date')" width="140" />
          <el-table-column prop="new_members" :label="t('ops.newMembers')" />
          <el-table-column prop="rfqs" :label="t('ops.rfqs')" />
          <el-table-column prop="orders" :label="t('ops.orders')" />
          <el-table-column prop="inquiries" :label="t('ops.inquiries')" />
        </el-table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.muted { color: #6b7280; }
.error, .forbidden { color: #b91c1c; }
.forbidden { padding: 1rem 0; }
</style>
