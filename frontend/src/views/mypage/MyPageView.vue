<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
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
  signContract,
  updateFactoryProfile,
  updateProfile,
  updateProfileMultipart,
  uploadPaymentProof,
  uploadSupplierProfileAttachment,
  toggleProjectTodo,
} from '../../api'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'

const { t } = useI18n()
const { formatMoney } = useLocaleCurrency()
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
  payment_terms: '',
  established_year: '',
  employee_scale: '',
  factory_area_sqm: '',
  main_products: '',
  monthly_capacity: '',
  quality_certifications: '',
  equipment_summary: '',
})
const profileAttachments = ref([])
const companyFile = ref(null)
const companyFileCategory = ref('company_profile')
const licenseFile = ref(null)

const money = (v, c = 'KRW', quote = null) => {
  if (quote) {
    return formatMoney({
      amount: v,
      currency: quote.currency,
      totalKrw: quote.result?.total_krw,
      rmbToKrw: quote.result?.rmb_to_krw,
    })
  }
  return formatMoney({ amount: v, currency: c })
}
const quoteTypeLabel = (quoteType) => {
  if (quoteType === 'paper_box') return t('packaging.title')
  const key = quoteType === 'print3d' ? 'print3d' : quoteType
  return t(`simpleQuote.${key}`)
}
const quoteDetailLink = (quote) => {
  if (quote.quote_type === 'paper_box') {
    const code = quote.inputs?.box_code
    return code ? `/packaging/box?code=${encodeURIComponent(code)}` : '/packaging'
  }
  return `/simple-quote?id=${quote.id}`
}

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
        payment_terms: fp.payment_terms || '',
        established_year: fp.established_year || '',
        employee_scale: fp.employee_scale || '',
        factory_area_sqm: fp.factory_area_sqm || '',
        main_products: fp.main_products || '',
        monthly_capacity: fp.monthly_capacity || '',
        quality_certifications: fp.quality_certifications || '',
        equipment_summary: fp.equipment_summary || '',
      }
      profileAttachments.value = fp.attachments || []
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
  if (activeTab.value === 'profile' && auth.isEnterprise) {
    const payload = {
      company_name: profileForm.value.company_name,
      short_name: profileForm.value.short_name,
      region: profileForm.value.region,
      country: profileForm.value.country,
      city: profileForm.value.city,
      intro: profileForm.value.intro,
      contact_phone: profileForm.value.contact_phone,
      payment_terms: profileForm.value.payment_terms,
      established_year: profileForm.value.established_year || null,
      employee_scale: profileForm.value.employee_scale,
      factory_area_sqm: profileForm.value.factory_area_sqm || null,
      main_products: profileForm.value.main_products,
      monthly_capacity: profileForm.value.monthly_capacity,
      quality_certifications: profileForm.value.quality_certifications,
      equipment_summary: profileForm.value.equipment_summary,
    }
    if (auth.user?.role === 'factory') {
      const res = await updateFactoryProfile({
        ...payload,
        name: profileForm.value.name,
        phone: profileForm.value.phone,
      })
      auth.profile = res.data
      profileAttachments.value = res.data.attachments || []
      auth.persist()
    } else {
      const fd = new FormData()
      fd.append('name', profileForm.value.name || '')
      fd.append('phone', profileForm.value.phone || '')
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

const onSignContract = async (contract) => {
  await signContract(contract.id)
  feedback.value = t('mypage.contractSigned')
  await loadTab('contracts')
}

const onLogout = () => {
  auth.logout()
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

      <!-- Dashboard -->
      <div v-else-if="activeTab === 'dashboard' && dashboard" class="stat-grid">
        <div class="stat-card"><span class="stat-num">{{ dashboard.points_balance }}</span><span class="stat-label">{{ t('mypage.pointsBalance') }}</span></div>
        <div class="stat-card"><span class="stat-num">{{ dashboard.simple_quotes_count }}</span><span class="stat-label">{{ t('mypage.simpleQuotes') }}</span></div>
        <div class="stat-card"><span class="stat-num">{{ dashboard.rfqs_count }}</span><span class="stat-label">{{ t('mypage.detailQuotes') }}</span></div>
        <div class="stat-card"><span class="stat-num">{{ dashboard.projects_count }}</span><span class="stat-label">{{ t('mypage.projects') }}</span></div>
        <div class="stat-card"><span class="stat-num">{{ dashboard.contracts_count }}</span><span class="stat-label">{{ t('mypage.contracts') }}</span></div>
        <div class="stat-card"><span class="stat-num">{{ dashboard.pending_payments_count }}</span><span class="stat-label">{{ t('mypage.pendingPayments') }}</span></div>
        <div class="stat-card"><span class="stat-num">{{ dashboard.unread_notifications }}</span><span class="stat-label">{{ t('mypage.notifications') }}</span></div>
        <RouterLink to="/simple-quote" class="stat-card stat-card--cta">＋ {{ t('simpleQuote.title') }}</RouterLink>
        <RouterLink to="/my/nda" class="stat-card">{{ t('nda.title') }}</RouterLink>
      </div>

      <!-- Simple quotes -->
      <div v-else-if="activeTab === 'simple-quotes'">
        <RouterLink to="/simple-quote" class="btn btn-primary btn-sm mb">＋ {{ t('simpleQuote.title') }}</RouterLink>
        <RouterLink to="/packaging" class="btn btn-secondary btn-sm mb">＋ {{ t('packaging.title') }}</RouterLink>
        <p v-if="!simpleQuotes.length" class="page-empty">{{ t('mypage.empty') }}</p>
        <table v-else class="data-table">
          <thead><tr><th>No.</th><th>{{ t('simpleQuote.type') }}</th><th>{{ t('mypage.amount') }}</th><th>{{ t('mypage.status') }}</th><th></th></tr></thead>
          <tbody>
            <tr v-for="q in simpleQuotes" :key="q.id">
              <td>{{ q.quote_no }}</td>
              <td>{{ quoteTypeLabel(q.quote_type) }}</td>
              <td>{{ money(q.total_amount, q.currency, q) }}</td>
              <td>{{ q.status }}</td>
              <td><RouterLink :to="quoteDetailLink(q)" class="link">{{ t('demandHall.view') }}</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Detail quotes -->
      <div v-else-if="activeTab === 'detail-quotes'">
        <RouterLink to="/rfq/new" class="btn btn-primary btn-sm mb">＋ {{ t('rfq.createTitle') }}</RouterLink>
        <p v-if="!rfqs.length" class="page-empty">{{ t('mypage.empty') }}</p>
        <table v-else class="data-table">
          <thead><tr><th>No.</th><th>{{ t('rfq.stepProcess') }}</th><th>{{ t('mypage.status') }}</th><th></th></tr></thead>
          <tbody>
            <tr v-for="r in rfqs" :key="r.id">
              <td>{{ r.rfq_no }}</td>
              <td>{{ r.service_category_name }}</td>
              <td>{{ r.status }}</td>
              <td><RouterLink :to="`/my/rfqs/${r.id}`" class="link">{{ t('demandHall.view') }}</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Projects -->
      <div v-else-if="activeTab === 'projects'">
        <p v-if="!projects.length" class="page-empty">{{ t('mypage.empty') }}</p>
        <div v-else class="card-list">
          <div v-for="p in projects" :key="p.id" class="proj-card">
            <RouterLink :to="`/my/projects/${p.id}`" class="proj-card-main">
              <div class="proj-head"><strong>{{ p.project_no }}</strong><span>{{ p.status }}</span></div>
              <p class="proj-title">{{ p.title }}</p>
              <div class="progress-bar"><span :style="{ width: p.progress_percent + '%' }" /></div>
              <p class="proj-meta">
                {{ t('mypage.progress') }}: {{ p.progress_percent }}%
                <span v-if="p.current_stage"> · {{ t('workflow.currentStage') }}: {{ p.current_stage.name }}</span>
              </p>
            </RouterLink>
            <RouterLink
              v-if="p.rfq"
              :to="`/my/rfqs/${p.rfq}`"
              class="link deal-link"
            >
              {{ t('fulfillment.viewDeal') }}
            </RouterLink>
          </div>
        </div>
      </div>

      <!-- Contracts -->
      <div v-else-if="activeTab === 'contracts'">
        <p v-if="!contracts.length" class="page-empty">{{ t('mypage.empty') }}</p>
        <table v-else class="data-table">
          <thead><tr><th>No.</th><th>{{ t('mypage.amount') }}</th><th>{{ t('mypage.status') }}</th><th></th></tr></thead>
          <tbody>
            <tr v-for="c in contracts" :key="c.id">
              <td>{{ c.contract_no }}</td>
              <td>{{ money(c.amount, c.currency) }}</td>
              <td>{{ c.status }}</td>
              <td class="actions-cell">
                <RouterLink v-if="c.rfq" :to="`/my/rfqs/${c.rfq}`" class="link">{{ t('fulfillment.viewDeal') }}</RouterLink>
                <button
                  v-if="c.status === 'pending_sign'"
                  type="button"
                  class="btn btn-sm btn-primary"
                  @click="onSignContract(c)"
                >
                  {{ t('mypage.signContract') }}
                </button>
                <a v-if="c.pdf_url" :href="c.pdf_url" target="_blank" rel="noopener" class="link">{{ t('mypage.download') }}</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Todos -->
      <div v-else-if="activeTab === 'todos'">
        <p v-if="!todos.length" class="page-empty">{{ t('mypage.empty') }}</p>
        <ul v-else class="todo-list">
          <li v-for="td in todos" :key="td.id">
            <label>
              <input type="checkbox" :checked="td.is_done" @change="onToggleTodo(td)" />
              <span :class="{ done: td.is_done }">{{ td.title }}</span>
            </label>
            <span class="todo-meta">{{ td.project_no }} · {{ td.project_title }}</span>
          </li>
        </ul>
      </div>

      <!-- Files -->
      <div v-else-if="activeTab === 'files'">
        <p v-if="!files.length" class="page-empty">{{ t('mypage.empty') }}</p>
        <table v-else class="data-table">
          <thead><tr><th>{{ t('mypage.fileName') }}</th><th>{{ t('mypage.source') }}</th><th>{{ t('mypage.createdAt') }}</th><th></th></tr></thead>
          <tbody>
            <tr v-for="f in files" :key="`${f.source}-${f.id}`">
              <td>{{ f.file_name }}</td>
              <td>{{ f.source_no }}</td>
              <td>{{ (f.created_at || '').slice(0, 10) }}</td>
              <td><a :href="f.file_url" target="_blank" rel="noopener" class="link">{{ t('mypage.download') }}</a></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Payments -->
      <div v-else-if="activeTab === 'payments'">
        <p v-if="!payments.length" class="page-empty">{{ t('mypage.empty') }}</p>
        <table v-else class="data-table">
          <thead><tr><th>No.</th><th>{{ t('mypage.amount') }}</th><th>{{ t('mypage.status') }}</th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in payments" :key="p.id">
              <td>{{ p.payment_no }}</td>
              <td>{{ money(p.amount, p.currency) }}</td>
              <td>{{ p.status }}</td>
              <td class="actions-cell">
                <RouterLink v-if="p.rfq" :to="`/my/rfqs/${p.rfq}`" class="link">{{ t('fulfillment.viewDeal') }}</RouterLink>
                <label v-if="p.status !== 'confirmed'" class="upload-label">
                  {{ t('mypage.uploadProof') }}
                  <input type="file" hidden @change="(e) => onUploadProof(p, e)" />
                </label>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Points -->
      <div v-else-if="activeTab === 'points'">
        <div v-if="wallet" class="points-summary">
          <div><span class="stat-num">{{ wallet.balance }}</span><span class="stat-label">{{ t('mypage.balance') }}</span></div>
          <div><span class="stat-num">{{ wallet.total_earned }}</span><span class="stat-label">{{ t('mypage.totalEarned') }}</span></div>
          <div><span class="stat-num">{{ wallet.total_spent }}</span><span class="stat-label">{{ t('mypage.totalSpent') }}</span></div>
        </div>
        <div class="recharge-box">
          <label>{{ t('mypage.rechargeAmount') }}<input v-model.number="rechargeAmount" type="number" min="1000" step="1000" /></label>
          <label class="upload-label">{{ t('mypage.uploadProof') }}<input type="file" @change="onRechargeProof" /></label>
          <button type="button" class="btn btn-primary btn-sm" @click="onRecharge">{{ t('mypage.submitRecharge') }}</button>
        </div>
        <h3 class="section-sub">{{ t('mypage.rechargeHistory') }}</h3>
        <p v-if="!recharges.length" class="page-empty">{{ t('mypage.empty') }}</p>
        <table v-else class="data-table mb">
          <thead><tr><th>{{ t('mypage.createdAt') }}</th><th>No.</th><th>{{ t('mypage.amount') }}</th><th>{{ t('mypage.status') }}</th></tr></thead>
          <tbody>
            <tr v-for="r in recharges" :key="r.id">
              <td>{{ (r.created_at || '').slice(0, 10) }}</td>
              <td>{{ r.recharge_no }}</td>
              <td>{{ formatMoney({ amount: r.amount_krw, currency: 'KRW' }) }}</td>
              <td>{{ r.status }}</td>
            </tr>
          </tbody>
        </table>
        <h3 class="section-sub">{{ t('mypage.transactionHistory') }}</h3>
        <table class="data-table">
          <thead><tr><th>{{ t('mypage.createdAt') }}</th><th>{{ t('simpleQuote.type') }}</th><th>{{ t('mypage.amount') }}</th></tr></thead>
          <tbody>
            <tr v-for="tx in transactions" :key="tx.id">
              <td>{{ (tx.created_at || '').slice(0, 10) }}</td>
              <td>{{ tx.description || tx.type }}</td>
              <td :class="tx.amount < 0 ? 'neg' : 'pos'">{{ tx.amount > 0 ? '+' : '' }}{{ tx.amount }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Notifications -->
      <div v-else-if="activeTab === 'notifications'">
        <button type="button" class="btn btn-secondary btn-sm mb" @click="onMarkAllRead">{{ t('mypage.markAllRead') }}</button>
        <p v-if="!notifications.length" class="page-empty">{{ t('mypage.empty') }}</p>
        <ul v-else class="notif-list">
          <li v-for="n in notifications" :key="n.id" :class="{ unread: !n.is_read }" @click="onMarkRead(n)">
            <strong>{{ n.title }}</strong>
            <p>{{ n.content }}</p>
            <span class="notif-time">{{ (n.created_at || '').slice(0, 16).replace('T', ' ') }}</span>
          </li>
        </ul>
      </div>

      <!-- Profile / Settings -->
      <div v-else-if="activeTab === 'profile' || activeTab === 'settings'" class="form-box">
        <label>{{ t('account.name') }}<input v-model="profileForm.name" type="text" /></label>
        <label>{{ t('account.phone') }}<input v-model="profileForm.phone" type="text" /></label>
        <template v-if="activeTab === 'profile' && auth.isEnterprise">
          <label>{{ t('mypage.companyName') }}<input v-model="profileForm.company_name" type="text" /></label>
          <label>{{ t('mypage.shortName') }}<input v-model="profileForm.short_name" type="text" /></label>
          <label>{{ t('mypage.region') }}<input v-model="profileForm.region" type="text" /></label>
          <label>{{ t('mypage.country') }}<input v-model="profileForm.country" type="text" /></label>
          <label>{{ t('mypage.city') }}<input v-model="profileForm.city" type="text" /></label>
          <label>{{ t('mypage.intro') }}<textarea v-model="profileForm.intro" rows="3" /></label>
          <label>{{ t('mypage.contactPhone') }}<input v-model="profileForm.contact_phone" type="text" /></label>
          <label>{{ t('mypage.paymentTerms') }}<input v-model="profileForm.payment_terms" type="text" /></label>
          <label>{{ t('quoteDetail.establishedYear') }}<input v-model="profileForm.established_year" type="number" min="1900" /></label>
          <label>{{ t('quoteDetail.employeeScale') }}<input v-model="profileForm.employee_scale" type="text" /></label>
          <label>{{ t('quoteDetail.factoryArea') }}<input v-model="profileForm.factory_area_sqm" type="number" min="0" /></label>
          <label>{{ t('quoteDetail.mainProducts') }}<textarea v-model="profileForm.main_products" rows="2" /></label>
          <label>{{ t('quoteDetail.monthlyCapacity') }}<input v-model="profileForm.monthly_capacity" type="text" /></label>
          <label>{{ t('quoteDetail.certifications') }}<textarea v-model="profileForm.quality_certifications" rows="2" /></label>
          <label>{{ t('quoteDetail.equipment') }}<textarea v-model="profileForm.equipment_summary" rows="2" /></label>
          <p class="hint">{{ t('mypage.publicProfileHint') }}</p>
          <template v-if="auth.isSupplier">
            <div class="company-att-box">
              <h3>{{ t('mypage.publicAttachments') }}</h3>
              <ul v-if="profileAttachments.length" class="att-mini">
                <li v-for="a in profileAttachments" :key="a.id">
                  <span>{{ a.file_name }} · {{ a.category }} · {{ a.is_public ? t('mypage.public') : t('mypage.private') }}</span>
                  <button type="button" class="btn btn-secondary btn-sm" @click="onRemoveCompanyAttachment(a.id)">
                    {{ t('quoteRequest.removeAttachment') }}
                  </button>
                </li>
              </ul>
              <label>
                {{ t('mypage.attachmentCategory') }}
                <select v-model="companyFileCategory">
                  <option value="company_profile">{{ t('mypage.catCompanyProfile') }}</option>
                  <option value="certification">{{ t('mypage.catCertification') }}</option>
                  <option value="equipment">{{ t('mypage.catEquipment') }}</option>
                  <option value="case">{{ t('mypage.catCase') }}</option>
                </select>
              </label>
              <label>{{ t('mypage.uploadPublicAttachment') }}<input type="file" @change="onCompanyFile" /></label>
              <button type="button" class="btn btn-secondary btn-sm" @click="onUploadCompanyAttachment">
                {{ t('mypage.uploadPublicAttachment') }}
              </button>
            </div>
          </template>
          <label v-if="auth.user?.role !== 'factory'">{{ t('mypage.businessLicense') }}<input type="file" @change="onLicenseFile" /></label>
          <p v-if="auth.factoryProfile?.business_license_url" class="hint">
            <a :href="auth.factoryProfile.business_license_url" target="_blank" rel="noopener">{{ t('mypage.viewLicense') }}</a>
          </p>
        </template>
        <p v-else-if="auth.isEnterprise && auth.factoryProfile" class="hint">
          {{ auth.factoryProfile.company_name }} · {{ auth.factoryProfile.status }}
        </p>
        <button type="button" class="btn btn-primary btn-sm" @click="onSaveProfile">{{ t('mypage.save') }}</button>
      </div>
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
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--space-md); }
.stat-card { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-lg); display: flex; flex-direction: column; gap: 0.25rem; text-decoration: none; color: inherit; }
.stat-card--cta { align-items: center; justify-content: center; color: var(--color-steel); font-weight: 600; border-style: dashed; }
.stat-num { font-size: 1.75rem; font-weight: 700; }
.stat-label { font-size: 0.8125rem; opacity: 0.65; }
.data-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } th { font-size: 0.72rem; text-transform: uppercase; opacity: 0.6; } }
.link { color: var(--color-steel); cursor: pointer; }
.mb { margin-bottom: var(--space-md); }
.card-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-lg); }
.proj-card { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-lg); text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: 0.5rem; }
.proj-card-main { text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: 0.5rem; }
.deal-link { font-size: 0.85rem; }
.proj-head { display: flex; justify-content: space-between; font-size: 0.8rem; }
.proj-title { margin: 0; font-weight: 600; }
.progress-bar { height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; span { display: block; height: 100%; background: var(--color-steel); } }
.proj-meta { font-size: 0.8rem; opacity: 0.65; margin: 0; }
.points-summary { display: flex; gap: var(--space-2xl); margin-bottom: var(--space-lg); div { display: flex; flex-direction: column; } }
.recharge-box { display: flex; gap: var(--space-md); align-items: flex-end; margin-bottom: var(--space-xl); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.85rem; } input { padding: 0.5rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.neg { color: #b91c1c; } .pos { color: #15803d; }
.notif-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-sm); li { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-md); cursor: pointer; p { margin: 0.25rem 0; font-size: 0.875rem; opacity: 0.75; } } li.unread { border-left: 3px solid var(--color-steel); } }
.notif-time { font-size: 0.72rem; opacity: 0.55; }
.form-box { display: flex; flex-direction: column; gap: var(--space-md); max-width: 400px; label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } input { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } .hint { font-size: 0.8rem; opacity: 0.7; margin: 0; } }
.upload-label { color: var(--color-steel); cursor: pointer; font-size: 0.85rem; }
.todo-list { list-style: none; padding: 0; margin: 0; li { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid var(--color-border); label { display: flex; align-items: center; gap: 0.5rem; } .done { text-decoration: line-through; opacity: 0.5; } } }
.todo-meta { font-size: 0.75rem; opacity: 0.55; }
.form-box textarea { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); font: inherit; }
.company-att-box {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  h3 { margin: 0; font-size: 0.95rem; }
}
.att-mini {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  li { display: flex; justify-content: space-between; gap: 0.5rem; align-items: center; font-size: 0.85rem; }
}
@media (max-width: 768px) { .mypage { grid-template-columns: 1fr; } .mypage-side { position: static; } .mypage-nav { flex-direction: row; flex-wrap: wrap; } }
</style>
