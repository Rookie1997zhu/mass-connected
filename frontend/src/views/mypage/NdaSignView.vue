<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchNdaList, fetchNdaTemplate, signNda } from '../../api'

const { t } = useI18n()
const loading = ref(true)
const signing = ref(false)
const error = ref('')
const template = ref(null)
const renderedBody = ref('')
const companyName = ref('')
const agree = ref(false)
const records = ref([])

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const [tplRes, listRes] = await Promise.all([fetchNdaTemplate(), fetchNdaList()])
    template.value = tplRes.data.template
    renderedBody.value = tplRes.data.rendered_body || ''
    companyName.value = tplRes.data.company_name || ''
    records.value = listRes.data.items || []
  } catch (e) {
    error.value = e.message || t('nda.loadFailed')
  } finally {
    loading.value = false
  }
}

const onSign = async () => {
  error.value = ''
  signing.value = true
  try {
    await signNda({ company_name: companyName.value, agree: agree.value })
    agree.value = false
    await load()
  } catch (e) {
    error.value = e.message || t('nda.signFailed')
  } finally {
    signing.value = false
  }
}

onMounted(load)
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('nda.title') }}</h1>
    <p class="page-lead">{{ t('nda.desc') }}</p>

    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="page-message page-message--error">{{ error }}</p>

    <div v-else class="nda-layout">
      <section class="card nda-form">
        <h2>{{ t('nda.signTitle') }}</h2>
        <label>{{ t('nda.companyName') }}<input v-model="companyName" type="text" /></label>
        <pre class="nda-body">{{ renderedBody }}</pre>
        <label class="checkbox"><input v-model="agree" type="checkbox" /> {{ t('nda.agree') }}</label>
        <button type="button" class="btn btn-primary" :disabled="signing || !agree" @click="onSign">
          {{ signing ? t('nda.signing') : t('nda.sign') }}
        </button>
      </section>

      <section class="card">
        <h2>{{ t('nda.history') }}</h2>
        <p v-if="!records.length" class="page-empty">{{ t('nda.empty') }}</p>
        <ul v-else class="nda-list">
          <li v-for="r in records" :key="r.id">
            <span>{{ r.company_name }} · {{ r.template_version }}</span>
            <span>{{ r.signed_at?.slice(0, 10) }}</span>
            <a v-if="r.pdf_url" :href="r.pdf_url" target="_blank" rel="noopener">PDF</a>
          </li>
        </ul>
      </section>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.nda-layout { display: grid; grid-template-columns: 1.2fr 1fr; gap: var(--space-xl); align-items: start; }
.card { padding: var(--space-xl); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.nda-form { display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } label.checkbox { flex-direction: row; align-items: center; } input { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.nda-body { white-space: pre-wrap; font-size: 0.82rem; line-height: 1.5; max-height: 360px; overflow: auto; padding: var(--space-md); background: var(--color-surface-muted, #f8f9fa); border-radius: var(--radius-sm); }
.nda-list { list-style: none; padding: 0; margin: 0; li { display: flex; flex-wrap: wrap; gap: var(--space-md); justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); font-size: 0.875rem; } }
@media (max-width: 768px) { .nda-layout { grid-template-columns: 1fr; } }
</style>
