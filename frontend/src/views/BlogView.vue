<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { fetchBlogCategories, fetchBlogPosts, fetchBlogTags } from '../api'

const PAGE_SIZE = 12

const { locale, t } = useI18n()
const route = useRoute()
const router = useRouter()

const categories = ref([])
const tags = ref([])
const posts = ref([])
const featured = ref([])
const popular = ref([])
const pagination = ref({ page: 1, total_pages: 1, total: 0 })
const keyword = ref('')
const loading = ref(false)

const languages = [
  { value: '', label: 'blog.languageAll' },
  { value: 'ko', label: 'blog.langKo' },
  { value: 'zh', label: 'blog.langZh' },
  { value: 'en', label: 'blog.langEn' },
  { value: 'ja', label: 'blog.langJa' },
]

const hasFilters = computed(() => Boolean(
  route.query.q || route.query.category || route.query.tag || route.query.language,
))

const pageNumber = computed(() => Number(route.query.page || 1) || 1)

const featurePost = computed(() => {
  if (hasFilters.value || pageNumber.value !== 1) return null
  return featured.value[0] || null
})

const listPosts = computed(() => {
  const heroId = featurePost.value?.id
  if (!heroId) return posts.value
  return posts.value.filter((item) => item.id !== heroId)
})

const siteEmpty = computed(() => (
  !loading.value && !hasFilters.value && popular.value.length === 0
))

const showSide = computed(() => !loading.value && popular.value.length > 0)

const pageList = computed(() => {
  const total = Number(pagination.value.total_pages || 1)
  const current = Number(pagination.value.page || 1)
  const width = 5
  let start = Math.max(1, current - 2)
  let end = Math.min(total, start + width - 1)
  start = Math.max(1, end - width + 1)
  const pages = []
  for (let page = start; page <= end; page += 1) pages.push(page)
  return pages
})

const formatDate = (value) => {
  if (!value) return ''
  const map = { zh: 'zh-CN', ko: 'ko-KR', ja: 'ja-JP', en: 'en-US' }
  return new Date(value).toLocaleDateString(map[locale.value] || 'ko-KR')
}

const coverStyle = (item) => (
  item?.cover_image ? { backgroundImage: `url(${item.cover_image})` } : {}
)

const pushQuery = (patch) => {
  const next = { ...route.query, ...patch, page: patch.page ?? 1 }
  Object.keys(next).forEach((key) => {
    if (next[key] === '' || next[key] == null) delete next[key]
  })
  router.push({ name: 'blog', query: next })
}

const emptyState = computed(() => {
  if (loading.value || siteEmpty.value || posts.value.length) return null
  if (route.query.q) {
    return {
      title: t('blog.emptySearchTitle'),
      desc: t('blog.emptySearchDesc'),
    }
  }
  const language = String(route.query.language || '')
  const category = String(route.query.category || '')
  const tag = String(route.query.tag || '')
  const selected = [language, category, tag].filter(Boolean)
  if (selected.length === 1 && language) {
    const match = languages.find((item) => item.value === language)
    const name = t(match?.label || 'blog.languageAll')
    return {
      title: t('blog.emptyLanguageTitle', { name }),
      desc: t('blog.emptyLanguageDesc', { name }),
    }
  }
  if (selected.length === 1 && category) {
    const name = categories.value.find((item) => item.slug === category)?.name || category
    return {
      title: t('blog.emptyCategoryTitle', { name }),
      desc: t('blog.emptyCategoryDesc'),
    }
  }
  if (selected.length === 1 && tag) {
    return {
      title: t('blog.emptyTagTitle'),
      desc: t('blog.emptyTagDesc', { name: tag }),
    }
  }
  if (selected.length > 1) {
    return {
      title: t('blog.emptyFilterTitle'),
      desc: t('blog.emptyFilterDesc'),
    }
  }
  return null
})

const load = async () => {
  loading.value = true
  keyword.value = String(route.query.q || '')
  const params = {
    page: route.query.page || 1,
    page_size: PAGE_SIZE,
    category: route.query.category,
    tag: route.query.tag,
    q: route.query.q,
    language: route.query.language,
    ordering: 'latest',
  }
  try {
    const [listRes, catRes, tagRes, featureRes, popularRes] = await Promise.all([
      fetchBlogPosts(params),
      fetchBlogCategories(),
      fetchBlogTags(),
      fetchBlogPosts({ is_featured: true, page_size: 1, ordering: 'latest' }),
      fetchBlogPosts({ ordering: 'popular', page_size: 5 }),
    ])
    posts.value = listRes.data.items || []
    pagination.value = listRes.data.pagination || { page: 1, total_pages: 1, total: 0 }
    categories.value = catRes.data.items || []
    tags.value = tagRes.data.items || []
    featured.value = featureRes.data.items || []
    popular.value = popularRes.data.items || []
  } catch {
    posts.value = []
    featured.value = []
    popular.value = []
  } finally {
    loading.value = false
  }
}

watch(() => route.query, load, { immediate: true })

const search = () => pushQuery({ q: keyword.value.trim(), page: 1 })
const onLanguageChange = (event) => pushQuery({ language: event.target.value })
const onCategoryChange = (event) => pushQuery({ category: event.target.value })
</script>

<template>
  <PageShell container-wide>
    <header class="blog-head">
      <div>
        <p class="eyebrow">MASS CONNECTED</p>
        <h1>{{ t('blog.title') }}</h1>
        <p class="subtitle">{{ t('blog.subtitle') }}</p>
      </div>
      <form class="search" @submit.prevent="search">
        <input v-model="keyword" type="search" :placeholder="t('blog.searchPlaceholder')" />
        <button type="submit">{{ t('blog.search') }}</button>
      </form>
    </header>

    <div class="layout" :class="{ 'layout-solo': !showSide }">
      <aside class="rail">
        <p class="rail-label">{{ t('blog.categories') }}</p>
        <button type="button" class="cat" :class="{ active: !route.query.category }" @click="pushQuery({ category: '' })">
          {{ t('blog.allCategories') }}
        </button>
        <button
          v-for="item in categories"
          :key="item.id"
          type="button"
          class="cat"
          :class="{ active: route.query.category === item.slug }"
          @click="pushQuery({ category: item.slug })"
        >
          {{ item.name }}
        </button>
      </aside>

      <section class="main-col">
        <div class="mobile-filters">
          <label>
            <span>{{ t('blog.language') }}</span>
            <select :value="route.query.language || ''" @change="onLanguageChange">
              <option v-for="item in languages" :key="item.value || 'all'" :value="item.value">
                {{ t(item.label) }}
              </option>
            </select>
          </label>
          <label>
            <span>{{ t('blog.categories') }}</span>
            <select :value="route.query.category || ''" @change="onCategoryChange">
              <option value="">{{ t('blog.allCategories') }}</option>
              <option v-for="item in categories" :key="item.id" :value="item.slug">{{ item.name }}</option>
            </select>
          </label>
        </div>

        <div class="filters">
          <span class="filter-label">{{ t('blog.language') }}</span>
          <button
            v-for="item in languages"
            :key="item.value || 'all'"
            type="button"
            class="chip"
            :class="{ active: (route.query.language || '') === item.value }"
            @click="pushQuery({ language: item.value })"
          >
            {{ t(item.label) }}
          </button>
        </div>

        <div v-if="route.query.q && !loading && posts.length" class="search-result">
          <p class="kicker">{{ t('blog.searchResult') }}</p>
          <p>{{ t('blog.searchCount', { keyword: route.query.q, count: pagination.total || 0 }) }}</p>
        </div>

        <div v-if="loading" class="skeleton" aria-hidden="true">
          <div class="sk sk-hero" />
          <div class="sk sk-row" />
          <div class="sk sk-row" />
          <div class="sk sk-row" />
        </div>

        <div v-else-if="siteEmpty" class="empty">
          <svg class="empty-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
            <path d="M14 10h14l8 8v20a2 2 0 0 1-2 2H14a2 2 0 0 1-2-2V12a2 2 0 0 1 2-2Z" stroke="currentColor" stroke-width="1.6" />
            <path d="M28 10v8h8M18 26h12M18 32h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <h2>{{ t('blog.emptyTitle') }}</h2>
          <p>{{ t('blog.emptyDesc') }}</p>
        </div>

        <div v-else-if="emptyState" class="empty">
          <template v-if="route.query.q">
            <p class="kicker">{{ t('blog.searchResult') }}</p>
            <p class="search-keyword">“{{ route.query.q }}”</p>
          </template>
          <h2>{{ emptyState.title }}</h2>
          <p>{{ emptyState.desc }}</p>
        </div>

        <template v-else>
          <article v-if="featurePost" class="feature">
            <RouterLink :to="`/blog/${featurePost.id}`" class="feature-link">
              <div class="feature-cover">
                <span class="thumb-media" :style="coverStyle(featurePost)" />
                <span v-if="!featurePost.cover_image" class="thumb-fallback">{{ featurePost.title.slice(0, 1) }}</span>
              </div>
              <div class="feature-copy">
                <p v-if="featurePost.category" class="kicker">{{ featurePost.category.name }}</p>
                <h2>{{ featurePost.title }} <span class="arrow" aria-hidden="true">→</span></h2>
                <p v-if="featurePost.summary" class="summary">{{ featurePost.summary }}</p>
                <time v-if="featurePost.published_at">{{ formatDate(featurePost.published_at) }}</time>
              </div>
            </RouterLink>
          </article>

          <div v-if="listPosts.length" class="cards">
            <article v-for="item in listPosts" :key="item.id" class="card">
              <RouterLink :to="`/blog/${item.id}`" class="card-link">
                <div class="thumb">
                  <span class="thumb-media" :style="coverStyle(item)" />
                  <span v-if="!item.cover_image" class="thumb-fallback">{{ item.title.slice(0, 1) }}</span>
                </div>
                <div class="card-body">
                  <p class="meta">
                    <span v-if="item.category">{{ item.category.name }}</span>
                    <span v-if="item.is_pinned">{{ t('blog.pinned') }}</span>
                  </p>
                  <h3>{{ item.title }} <span class="arrow" aria-hidden="true">→</span></h3>
                  <p v-if="item.summary" class="summary">{{ item.summary }}</p>
                  <time v-if="item.published_at">{{ formatDate(item.published_at) }}</time>
                </div>
              </RouterLink>
            </article>
          </div>

          <nav v-if="pagination.total_pages > 1" class="pager" :aria-label="t('blog.title')">
            <button type="button" :disabled="pagination.page <= 1" @click="pushQuery({ page: pagination.page - 1 })">{{ t('blog.prev') }}</button>
            <button
              v-for="page in pageList"
              :key="page"
              type="button"
              class="page"
              :class="{ active: page === pagination.page }"
              :aria-current="page === pagination.page ? 'page' : undefined"
              @click="pushQuery({ page })"
            >
              {{ page }}
            </button>
            <button type="button" :disabled="pagination.page >= pagination.total_pages" @click="pushQuery({ page: pagination.page + 1 })">{{ t('blog.next') }}</button>
          </nav>
        </template>
      </section>

      <aside v-if="showSide" class="side">
        <h3>{{ t('blog.popular') }}</h3>
        <ol class="popular-list">
          <li v-for="(item, index) in popular" :key="item.id">
            <RouterLink :to="`/blog/${item.id}`">
              <span class="rank">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="popular-copy">
                <span class="popular-title">{{ item.title }}</span>
                <time v-if="item.published_at">{{ formatDate(item.published_at) }}</time>
              </span>
            </RouterLink>
          </li>
        </ol>
        <h3>{{ t('blog.tags') }}</h3>
        <div class="tag-cloud">
          <button
            v-for="item in tags"
            :key="item.name"
            type="button"
            class="tag"
            :class="{ active: route.query.tag === item.name }"
            @click="pushQuery({ tag: route.query.tag === item.name ? '' : item.name })"
          >
            # {{ item.name }}
          </button>
        </div>
      </aside>
    </div>
  </PageShell>
</template>

<style scoped lang="scss">
.blog-head {
  display: flex;
  justify-content: space-between;
  gap: var(--space-lg);
  align-items: flex-end;
  margin-bottom: var(--space-xl);
  h1 { font-size: clamp(1.75rem, 3vw, 2.25rem); margin: 0; }
}
.eyebrow {
  margin: 0 0 0.25rem;
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  color: var(--color-steel);
}
.subtitle {
  margin: 0.4rem 0 0;
  max-width: 36rem;
  color: var(--color-text);
}
.search {
  display: flex;
  width: min(100%, 340px);
  input {
    flex: 1;
    height: 40px;
    border: 1px solid var(--color-border);
    border-right: 0;
    border-radius: var(--radius-sm) 0 0 var(--radius-sm);
    padding: 0 0.75rem;
    background: var(--color-surface);
  }
  button {
    height: 40px;
    border: 0;
    background: var(--color-steel);
    color: #fff;
    padding: 0 1rem;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    cursor: pointer;
  }
}
.layout {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr) 240px;
  gap: var(--space-lg);
  align-items: start;
}
.layout-solo {
  grid-template-columns: 180px minmax(0, 1fr);
}
.rail, .side {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0.75rem;
}
.rail-label, .filter-label {
  margin: 0.2rem 0.6rem 0.35rem;
  font-size: 0.75rem;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
}
.cat, .chip, .tag {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  padding: 0.45rem 0.6rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text);
}
.cat.active, .chip.active { background: var(--color-steel-muted); color: var(--color-steel); font-weight: 600; }
.filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: var(--space-md);
}
.chip { width: auto; border: 1px solid var(--color-border); background: var(--color-surface); }
.mobile-filters { display: none; }
.search-result { margin-bottom: var(--space-md); }
.search-result p { margin: 0.15rem 0; }
.search-keyword { margin: 0.25rem 0 0.5rem; color: var(--color-text-heading); }
.kicker { color: var(--color-steel); font-size: 0.75rem; letter-spacing: 0.08em; margin: 0; }
.feature { margin-bottom: var(--space-lg); }
.feature-link, .card-link {
  display: block;
  text-decoration: none;
  color: inherit;
}
.feature-cover, .thumb {
  position: relative;
  overflow: hidden;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  aspect-ratio: 16 / 9;
}
.thumb-media {
  position: absolute;
  inset: 0;
  background: var(--color-steel-muted) center/cover no-repeat;
  transition: transform 0.3s ease;
}
.thumb-fallback {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  height: 100%;
  color: var(--color-steel);
  font-size: 2rem;
  font-weight: 700;
}
.feature-copy { padding-top: var(--space-md); }
.feature-copy h2, .card h3 {
  margin: 0.35rem 0;
  font-size: 1.35rem;
}
.card h3 { font-size: 1.05rem; }
.arrow {
  display: inline-block;
  transition: transform 0.25s ease;
}
.summary {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--color-text);
  margin: 0.25rem 0;
}
.feature-copy time, .card time, .popular-copy time {
  color: var(--color-text-muted);
  font-size: 0.8125rem;
}
.cards { display: flex; flex-direction: column; gap: var(--space-md); }
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: transform 0.25s ease;
}
.card-link {
  display: grid;
  grid-template-columns: minmax(160px, 240px) 1fr;
  gap: var(--space-md);
  align-items: center;
  padding: 0.75rem;
}
.card-body { min-width: 0; }
.meta { margin: 0; color: var(--color-steel); font-size: 0.75rem; letter-spacing: 0.04em; }
.meta span + span::before { content: ' · '; color: var(--color-text-muted); }
.card:hover { transform: translateY(-2px); }
.card:hover .thumb-media, .feature-link:hover .thumb-media { transform: scale(1.03); }
.card:hover .arrow, .feature-link:hover .arrow { transform: translate(3px, -3px); }
.pager {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-top: var(--space-lg);
  button {
    min-width: 2.25rem;
    min-height: 2.25rem;
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    border-radius: var(--radius-sm);
    padding: 0.25rem 0.7rem;
    cursor: pointer;
  }
  button.active {
    background: var(--color-steel);
    border-color: var(--color-steel);
    color: #fff;
  }
  button:disabled { opacity: 0.4; cursor: default; }
}
.side h3 { font-size: 0.95rem; margin: 0.25rem 0.4rem 0.75rem; }
.popular-list { list-style: none; margin: 0 0 var(--space-lg); padding: 0; }
.popular-list li + li { border-top: 1px solid var(--color-border); }
.popular-list a {
  display: flex;
  gap: 0.75rem;
  padding: 0.7rem 0.35rem;
  text-decoration: none;
  color: inherit;
}
.rank {
  font-variant-numeric: tabular-nums;
  color: var(--color-steel);
  font-weight: 600;
  font-size: 0.8125rem;
}
.popular-copy { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
.popular-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tag-cloud { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.tag {
  width: auto;
  background: var(--color-bg);
  color: var(--color-steel);
  border: 1px solid var(--color-border);
  font-size: 0.8125rem;
}
.tag:hover, .tag.active {
  background: var(--color-steel);
  color: #fff;
}
.empty {
  padding: var(--space-3xl) var(--space-md);
  text-align: center;
  color: var(--color-text);
  h2 { margin: 0.5rem 0; color: var(--color-text-heading); font-size: 1.25rem; }
  p { margin: 0; }
}
.empty-icon {
  width: 48px;
  height: 48px;
  color: var(--color-steel);
}
.skeleton { display: flex; flex-direction: column; gap: var(--space-md); }
.sk {
  background: linear-gradient(90deg, var(--color-bg), #eef1f4, var(--color-bg));
  background-size: 200% 100%;
  border-radius: var(--radius-md);
  animation: shimmer 1.2s ease infinite;
}
.sk-hero { aspect-ratio: 16 / 9; }
.sk-row { height: 96px; }
@keyframes shimmer {
  from { background-position: 100% 0; }
  to { background-position: -100% 0; }
}
@media (prefers-reduced-motion: reduce) {
  .card, .thumb-media, .arrow, .sk { transition: none; animation: none; }
  .card:hover, .card:hover .thumb-media, .feature-link:hover .thumb-media,
  .card:hover .arrow, .feature-link:hover .arrow { transform: none; }
}
@media (max-width: 768px) {
  .blog-head { flex-direction: column; align-items: stretch; }
  .layout, .layout-solo { display: flex; flex-direction: column; }
  .rail, .filters { display: none; }
  .mobile-filters {
    display: grid;
    gap: 0.75rem;
    margin-bottom: var(--space-md);
    label { display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.8125rem; color: var(--color-text-muted); }
    select {
      min-height: 44px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      background: var(--color-surface);
      padding: 0 0.75rem;
    }
  }
  .card-link { grid-template-columns: 112px 1fr; }
  .side { order: 2; }
}
</style>
