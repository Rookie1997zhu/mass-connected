<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchFefcoCatalog } from '../../api'
import { categoriesWithTemplates, resetFefcoCatalog, setFefcoCatalogFromApi } from '../../lib/packaging/fefcoCatalog'

const { t, locale } = useI18n()
const router = useRouter()

const fefcoCategories = ref([])
const catalogLoading = ref(false)
const catalogError = ref('')

const localeKey = computed(() => {
  const map = { 'zh-CN': 'zh', zh: 'zh', en: 'en', ko: 'ko', ja: 'ja' }
  return map[locale.value] || 'en'
})

const templateLabel = (tpl, field = 'name') => {
  if (!tpl) return ''
  const i18n = field === 'name' ? tpl.nameI18n : tpl.descI18n
  const key = field === 'name' ? tpl.nameKey : tpl.descKey
  return i18n?.[localeKey.value] || i18n?.zh || i18n?.en || (key ? t(`packaging.${key}`) : tpl.code)
}

const categoryLabel = (cat, field = 'name') => {
  if (!cat) return ''
  const i18n = field === 'name' ? cat.nameI18n : cat.descI18n
  const key = field === 'name' ? cat.nameKey : cat.descKey
  return i18n?.[localeKey.value] || i18n?.zh || i18n?.en || cat.code || (key ? t(`packaging.${key}`) : '')
}

const loadCatalog = async () => {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const res = await fetchFefcoCatalog()
    setFefcoCatalogFromApi(res.data || {})
    fefcoCategories.value = categoriesWithTemplates()
    if (!fefcoCategories.value.length) {
      catalogError.value = t('packaging.catalogEmpty')
    }
  } catch {
    resetFefcoCatalog()
    fefcoCategories.value = []
    catalogError.value = t('packaging.catalogLoadFailed')
  } finally {
    catalogLoading.value = false
  }
}

const openBox = (code) => {
  router.push({ name: 'packaging-box', query: { code } })
}

onMounted(() => {
  loadCatalog()
})
</script>

<template>
  <PageShell container-wide :title="t('packaging.title')" :subtitle="t('packaging.libraryPageDesc')">
    <div class="pkg-library-page">
      <header class="pkg-library-head">
        <h2>{{ t('packaging.libraryPageTitle') }}</h2>
        <p class="pkg-library-hint">{{ t('packaging.fefcoLibraryDesc') }}</p>
      </header>

      <p v-if="catalogLoading" class="pkg-lib-status">{{ t('packaging.catalogLoading') }}</p>
      <p v-else-if="catalogError" class="page-message page-message--error">{{ catalogError }}</p>

      <div v-else class="pkg-library-sections">
        <section v-for="cat in fefcoCategories" :key="cat.code" class="pkg-library-section card">
          <div class="pkg-library-section-head">
            <h3>{{ categoryLabel(cat) }}</h3>
            <p v-if="categoryLabel(cat, 'desc')" class="pkg-library-cat-desc">{{ categoryLabel(cat, 'desc') }}</p>
          </div>
          <div class="pkg-box-grid">
            <button
              v-for="tpl in cat.templates"
              :key="tpl.code"
              type="button"
              class="pkg-box-card"
              :class="{ disabled: !tpl.previewEnabled }"
              :title="templateLabel(tpl, 'desc')"
              @click="openBox(tpl.code)"
            >
              <img v-if="tpl.thumbnailUrl" :src="tpl.thumbnailUrl" class="pkg-box-thumb" alt="" />
              <span class="pkg-box-head">
                <span class="pkg-box-code">FEFCO {{ tpl.code }}</span>
                <span class="pkg-box-name">{{ templateLabel(tpl, 'name') }}</span>
              </span>
              <span class="pkg-box-desc">{{ templateLabel(tpl, 'desc') }}</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.card {
  padding: var(--space-xl);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.pkg-library-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.pkg-library-head {
  h2 {
    margin: 0 0 0.35rem;
    font-size: 1.25rem;
  }
}

.pkg-library-hint {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.pkg-lib-status {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.pkg-library-sections {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.pkg-library-section-head {
  margin-bottom: var(--space-md);

  h3 {
    margin: 0 0 0.25rem;
    font-size: 1rem;
    color: var(--color-primary, #2563eb);
  }
}

.pkg-library-cat-desc {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.pkg-box-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-md);
}

.pkg-box-card {
  text-align: left;
  padding: var(--space-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #fff;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);

  &:hover:not(.disabled) {
    border-color: var(--color-primary, #2563eb);
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.12);
  }

  &.disabled {
    opacity: 0.72;
    cursor: not-allowed;
  }
}

.pkg-box-thumb {
  width: 100%;
  height: 72px;
  object-fit: contain;
  border-radius: 4px;
  background: #f8fafc;
}

.pkg-box-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.pkg-box-code {
  flex-shrink: 0;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--color-primary, #2563eb);
  padding: 0.12rem 0.4rem;
  border-radius: 3px;
  background: rgba(37, 99, 235, 0.08);
}

.pkg-box-name {
  font-size: 0.95rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pkg-box-desc {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
