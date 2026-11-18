<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import {
  createRecharge,
  deleteSupplierProfileAttachment,
  fetchFactoryProfile,
  fetchMemberDashboard,
  fetchMemberFiles,
  fetchMemberTodos,
  fetchMyContracts,
  fetchMyPayments,
  fetchMyProjects,
  fetchMyRfqs,
  fetchNotifications,
  fetchPointTransactions,
  fetchPointWallet,
  fetchRecharges,
  fetchSimpleQuotes,
  fetchSupplierNotifications,
  markAllNotificationsRead,
  markAllSupplierNotificationsRead,
  markNotificationRead,
  markSupplierNotificationRead,
  updateFactoryProfile,
  updateProfile,
  updateProfileMultipart,
  uploadPaymentProof,
  uploadSupplierProfileAttachment,
  toggleProjectTodo,
} from '../../api'
import DashboardSection from './sections/DashboardSection.vue'
import SimpleQuotesSection from './sections/SimpleQuotesSection.vue'
import DetailQuotesSection from './sections/DetailQuotesSection.vue'
import ProjectsSection from './sections/ProjectsSection.vue'
import ContractsSection from './sections/ContractsSection.vue'
import TodosSection from './sections/TodosSection.vue'
import FilesSection from './sections/FilesSection.vue'
import PaymentsSection from './sections/PaymentsSection.vue'
import PointsSection from './sections/PointsSection.vue'
import NotificationsSection from './sections/NotificationsSection.vue'
import ProfileSettingsSection from './sections/ProfileSettingsSection.vue'

const { t } = useI18n()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const tabs = computed(() => [
  { key: 'dashboard', label: t('mypage.dashboard') },
  { key: 'simple-quotes', label: t('mypage.simpleQuotes') },
  { key: 'detail-quotes', label: t('mypage.detailQuotes') },
  { key: 'projects', label: t('mypage.projects') },
  { key: 'todos', label: t('mypage.todos') },
  { key: 'files', label: t('mypage.files') },
  { key: 'contracts', label: t('mypage.contracts') },
  { key: 'payments', label: t('mypage.payments') },
  { key: 'points', label: t('mypage.points') },
  { key: 'notifications', label: t('mypage.notifications') },
  ...(auth.isEnterprise ? [{ key: 'profile', label: t('mypage.profile') }] : []),
  { key: 'settings', label: t('mypage.settings') },
])

const activeTab = ref(route.query.tab || 'dashboard')
const loading = ref(false)
const feedback = ref('')

const dashboard = ref(null)
const simpleQuotes = ref([])
const rfqs = ref([])
const projects = ref([])
const contracts = ref([])
const payments = ref([])
const wallet = ref(null)
const transactions = ref([])
const recharges = ref([])
const notifications = ref([])
const todos = ref([])
const files = ref([])
const rechargeAmount = ref(50000)
const rechargeProof = ref(null)
const profileForm = ref({
  name: '',
  phone: '',
  company_name: '',
  short_name: '',
  region: '',
  intro: '',
  contact_phone: '',
  country: '',
  city: '',
  established_year: '',
  employee_scale: '',
  factory_area_sqm: '',
  main_products: '',
  monthly_capacity: '',
  quality_certifications: '',
  equipment_summary: '',
  is_public: true,
})
const profileId = ref(null)
const profileStatus = ref('')
const profileAttachments = ref([])
const companyFile = ref(null)
const companyFileCategory = ref('company_profile')
const licenseFile = ref(null)
const profileError = ref('')

const loadTab = async (tab) => {
  loading.value = true
  feedback.value = ''
  try {
    if (tab === 'dashboard') {
      const res = await fetchMemberDashboard()
      dashboard.value = res.data
      profileForm.value = { name: res.data.profile?.name || '', phone: res.data.profile?.phone || '' }
    } else if (tab === 'simple-quotes') {
      const res = await fetchSimpleQuotes()
      simpleQuotes.value = res.data.items || []
    } else if (tab === 'detail-quotes') {
      const res = await fetchMyRfqs()
      rfqs.value = res.data.items || []
    } else if (tab === 'projects') {
      const res = await fetchMyProjects()
      projects.value = res.data.items || []
    } else if (tab === 'todos') {
      const res = await fetchMemberTodos()
      todos.value = res.data.items || []
    } else if (tab === 'files') {
      const res = await fetchMemberFiles()
      files.value = res.data.items || []
    } else if (tab === 'contracts') {
      const res = await fetchMyContracts()
      contracts.value = res.data.items || []
    } else if (tab === 'payments') {
      const res = await fetchMyPayments()
      payments.value = res.data.items || []
    } else if (tab === 'points') {
      const [w, txns, rech] = await Promise.all([
        fetchPointWallet(),
        fetchPointTransactions(),
        fetchRecharges(),
      ])
      wallet.value = w.data
      transactions.value = txns.data.items || []
      recharges.value = rech.data.items || []
    } else if (tab === 'notifications') {
      const fetcher = auth.user?.role === 'factory' ? fetchSupplierNotifications : fetchNotifications
      const res = await fetcher()
      notifications.value = res.data.items || []
    } else if (tab === 'settings') {
      profileForm.value = { name: auth.user?.name || '', phone: auth.user?.phone || '' }
    } else if (tab === 'profile') {
      let fp = auth.factoryProfile || {}
      if (auth.isSupplier) {
        try {
          const res = await fetchFactoryProfile()
          fp = res.data || fp
          auth.profile = fp
          auth.persist()
        } catch {
          /* keep cached profile */
        }
      }
      profileForm.value = {
        name: auth.user?.name || '',
        phone: auth.user?.phone || '',
        company_name: fp.company_name || '',
        short_name: fp.short_name || '',
        region: fp.region || '',
        intro: fp.intro || '',
        contact_phone: fp.contact_phone || '',
        country: fp.country || '',
        city: fp.city || '',
        established_year: fp.established_year || '',
        employee_scale: fp.employee_scale || '',
        factory_area_sqm: fp.factory_area_sqm || '',
        main_products: fp.main_products || '',
        monthly_capacity: fp.monthly_capacity || '',
        quality_certifications: fp.quality_certifications || '',
        equipment_summary: fp.equipment_summary || '',
        is_public: fp.is_public !== false,
      }
      profileId.value = fp.id || null
      profileStatus.value = fp.status || ''
      profileAttachments.value = fp.attachments || []
      profileError.value = ''
    }
  } finally {
    loading.value = false
  }
}

const switchTab = (tab) => {
  activeTab.value = tab
  router.replace({ query: { tab } })
}

watch(activeTab, (tab) => loadTab(tab))
onMounted(() => loadTab(activeTab.value))

const onUploadProof = async (payment, event) => {
  const file = event.target.files?.[0]
  if (!file) return
  const fd = new FormData()
  fd.append('proof', file)
  await uploadPaymentProof(payment.id, fd)
  feedback.value = t('mypage.proofUploaded')
  await loadTab('payments')
}

const onRecharge = async () => {
  const fd = new FormData()
  fd.append('amount_krw', String(rechargeAmount.value))
  if (rechargeProof.value) fd.append('proof', rechargeProof.value)
  await createRecharge(fd)
  feedback.value = t('mypage.rechargeSubmitted')
  rechargeProof.value = null
  await loadTab('points')
}

const onRechargeProof = (e) => {
  rechargeProof.value = e.target.files?.[0] || null
}

const onMarkRead = async (n) => {
  if (!n.is_read) {
    const markRead = auth.user?.role === 'factory' ? markSupplierNotificationRead : markNotificationRead
    await markRead(n.id)
    n.is_read = true
  }
}
const onMarkAllRead = async () => {
  const markAll = auth.user?.role === 'factory' ? markAllSupplierNotificationsRead : markAllNotificationsRead
  await markAll()
  await loadTab('notifications')
}

const onSaveProfile = async () => {
  profileError.value = ''
  if (activeTab.value === 'profile' && auth.isEnterprise) {
    if (!String(profileForm.value.company_name || '').trim()) {
      profileError.value = t('mypage.companyNameRequired')
      return
    }
    const phone = profileForm.value.phone || ''
    const payload = {
      company_name: profileForm.value.company_name.trim(),
      short_name: profileForm.value.short_name,
      region: '',
      country: profileForm.value.country,
      city: profileForm.value.city,
      intro: profileForm.value.intro,
      contact_phone: phone,
      established_year: profileForm.value.established_year || null,
      employee_scale: profileForm.value.employee_scale,
      factory_area_sqm: profileForm.value.factory_area_sqm || null,
      main_products: profileForm.value.main_products,
      monthly_capacity: profileForm.value.monthly_capacity,
      quality_certifications: profileForm.value.quality_certifications,
      equipment_summary: profileForm.value.equipment_summary,
      is_public: Boolean(profileForm.value.is_public),
    }
    if (auth.user?.role === 'factory') {
      const res = await updateFactoryProfile({
        ...payload,
        name: profileForm.value.name,
        phone,
      })
      auth.profile = res.data
      profileAttachments.value = res.data.attachments || []
      auth.persist()
    } else {
      const fd = new FormData()
      fd.append('name', profileForm.value.name || '')
      fd.append('phone', phone)
      Object.entries(payload).forEach(([k, v]) => fd.append(k, v ?? ''))
      if (licenseFile.value) fd.append('business_license', licenseFile.value)
      await updateProfileMultipart(fd)
    }
  } else {
    await updateProfile({ name: profileForm.value.name, phone: profileForm.value.phone })
  }
  auth.user = { ...auth.user, name: profileForm.value.name, phone: profileForm.value.phone }
  auth.persist()
  feedback.value = t('mypage.saved')
}

const onCompanyFile = (e) => {
  companyFile.value = e.target.files?.[0] || null
}

const onUploadCompanyAttachment = async () => {
  if (!companyFile.value) return
  const fd = new FormData()
  fd.append('file', companyFile.value)
  fd.append('category', companyFileCategory.value)
  fd.append('is_public', 'true')
  await uploadSupplierProfileAttachment(fd)
  companyFile.value = null
  feedback.value = t('mypage.companyAttachmentUploaded')
  await loadTab('profile')
}

const onRemoveCompanyAttachment = async (attId) => {
  await deleteSupplierProfileAttachment(attId)
  feedback.value = t('mypage.companyAttachmentRemoved')
  await loadTab('profile')
}

const onLicenseFile = (e) => {
  licenseFile.value = e.target.files?.[0] || null
}

const onToggleTodo = async (todo) => {
  await toggleProjectTodo(todo.project_id, todo.id)
  await loadTab('todos')
}

const onLogout = async () => {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="mypage container">
    <aside class="mypage-side">
      <h2 class="mypage-title">{{ t('mypage.title') }}</h2>
      <p class="mypage-user">{{ auth.user?.name || auth.user?.email }}</p>
      <nav class="mypage-nav">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="mypage-nav-item"
          :class="{ active: activeTab === tab.key }"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
        </button>
        <button type="button" class="mypage-nav-item logout" @click="onLogout">
          {{ t('mypage.logout') }}
        </button>
      </nav>
    </aside>

    <section class="mypage-content">
      <p v-if="feedback" class="page-message page-message--success">{{ feedback }}</p>
      <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>

      <DashboardSection v-else-if="activeTab === 'dashboard' && dashboard" :dashboard="dashboard" />

      <SimpleQuotesSection v-else-if="activeTab === 'simple-quotes'" :simple-quotes="simpleQuotes" />

      <DetailQuotesSection v-else-if="activeTab === 'detail-quotes'" :rfqs="rfqs" />

      <ProjectsSection v-else-if="activeTab === 'projects'" :projects="projects" />

      <ContractsSection v-else-if="activeTab === 'contracts'" :contracts="contracts" />

      <TodosSection v-else-if="activeTab === 'todos'" :todos="todos" @toggle-todo="onToggleTodo" />

      <FilesSection v-else-if="activeTab === 'files'" :files="files" />

      <PaymentsSection v-else-if="activeTab === 'payments'" :payments="payments" @upload-proof="onUploadProof" />

      <PointsSection
        v-else-if="activeTab === 'points'"
        v-model:recharge-amount="rechargeAmount"
        :wallet="wallet"
        :recharges="recharges"
        :transactions="transactions"
        @recharge-proof-change="onRechargeProof"
        @submit-recharge="onRecharge"
      />

      <NotificationsSection
        v-else-if="activeTab === 'notifications'"
        :notifications="notifications"
        @mark-read="onMarkRead"
        @mark-all-read="onMarkAllRead"
      />

      <ProfileSettingsSection
        v-else-if="activeTab === 'profile' || activeTab === 'settings'"
        v-model:profile-form="profileForm"
        v-model:company-file-category="companyFileCategory"
        :active-tab="activeTab"
        :profile-attachments="profileAttachments"
        :profile-error="profileError"
        :profile-id="profileId"
        :profile-status="profileStatus"
        @company-file-change="onCompanyFile"
        @upload-company-attachment="onUploadCompanyAttachment"
        @remove-company-attachment="onRemoveCompanyAttachment"
        @license-file-change="onLicenseFile"
        @save-profile="onSaveProfile"
      />
    </section>
  </div>
</template>

<style scoped lang="scss">
.mypage { display: grid; grid-template-columns: 220px 1fr; gap: var(--space-2xl); padding-block: var(--space-2xl); align-items: start; }
.mypage-side { position: sticky; top: calc(var(--header-height) + 1rem); }
.mypage-title { font-size: 1.25rem; margin: 0; }
.mypage-user { font-size: 0.8125rem; opacity: 0.65; margin: 0.25rem 0 var(--space-md); }
.mypage-nav { display: flex; flex-direction: column; gap: 2px; }
.mypage-nav-item { text-align: left; padding: 0.625rem 0.75rem; border: none; background: none; border-radius: var(--radius-sm); cursor: pointer; font-size: 0.9rem; color: var(--color-text); }
.mypage-nav-item:hover { background: var(--color-steel-muted); }
.mypage-nav-item.active { background: var(--color-steel-muted); color: var(--color-steel); font-weight: 600; }
.mypage-nav-item.logout { margin-top: var(--space-md); color: #b91c1c; }
@media (max-width: 768px) { .mypage { grid-template-columns: 1fr; } .mypage-side { position: static; } .mypage-nav { flex-direction: row; flex-wrap: wrap; } }
</style>
