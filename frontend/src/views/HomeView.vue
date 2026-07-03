<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchServiceCategories, fetchNews, fetchCases } from '../api'

const { t, locale } = useI18n()

const processes = ref([])
const news = ref([])
const cases = ref([])
const loading = ref(true)

const pickI18n = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || Object.values(field)[0] || ''
}

const heroMetrics = computed(() => [
  { label: t('home.hero.metricFactories'), value: t('home.hero.metricFactoriesValue') },
  { label: t('home.hero.metricProcesses'), value: t('home.hero.metricProcessesValue') },
  { label: t('home.hero.metricQuotes'), value: t('home.hero.metricQuotesValue') },
  { label: t('home.hero.metricMarkets'), value: t('home.hero.metricMarketsValue') },
])

const howItWorksItems = computed(() => [
  {
    title: t('home.howItWorks.step1Title'),
    desc: t('home.howItWorks.step1Desc'),
  },
  {
    title: t('home.howItWorks.step2Title'),
    desc: t('home.howItWorks.step2Desc'),
  },
  {
    title: t('home.howItWorks.step3Title'),
    desc: t('home.howItWorks.step3Desc'),
  },
])

const roleCards = computed(() => [
  {
    title: t('home.roles.buyerTitle'),
    desc: t('home.roles.buyerDesc'),
    cta: t('home.roles.buyerCta'),
    link: '/rfq/new',
    primary: true,
  },
  {
    title: t('home.roles.factoryTitle'),
    desc: t('home.roles.factoryDesc'),
    cta: t('home.roles.factoryCta'),
    link: '/partners',
    primary: false,
  },
])

onMounted(async () => {
  try {
    const [p, n, c] = await Promise.all([
      fetchServiceCategories(),
      fetchNews({ page_size: 3 }),
      fetchCases({ page_size: 3 }),
    ])
    processes.value = (p.data.items || []).slice(0, 8)
    news.value = n.data.items || []
    cases.value = c.data.items || []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="home">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-inner container">
        <div class="hero-content">
          <span class="section-eyebrow hero-eyebrow">{{ t('home.hero.eyebrow') }}</span>
          <h1 class="hero-title">{{ t('home.hero.title') }}</h1>
          <p class="hero-subtitle">{{ t('home.hero.subtitle') }}</p>
          <div class="hero-actions">
            <RouterLink to="/rfq/new" class="btn btn-primary">{{ t('home.hero.ctaRfq') }}</RouterLink>
            <RouterLink to="/partners" class="btn btn-secondary">{{ t('home.hero.ctaPartner') }}</RouterLink>
          </div>
        </div>
        <div class="hero-visual" aria-hidden="true">
          <div class="blueprint-panel">
            <svg class="blueprint-svg" viewBox="0 0 400 320" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="40" y="40" width="320" height="240" stroke="rgba(45,90,138,0.4)" stroke-width="1" />
              <line x1="40" y1="120" x2="360" y2="120" stroke="rgba(45,90,138,0.25)" stroke-width="1" />
              <line x1="40" y1="200" x2="360" y2="200" stroke="rgba(45,90,138,0.25)" stroke-width="1" />
              <line x1="160" y1="40" x2="160" y2="280" stroke="rgba(45,90,138,0.25)" stroke-width="1" />
              <line x1="280" y1="40" x2="280" y2="280" stroke="rgba(45,90,138,0.25)" stroke-width="1" />
              <circle cx="100" cy="80" r="24" stroke="rgba(45,90,138,0.5)" stroke-width="1.5" />
              <rect x="180" y="140" width="80" height="48" stroke="rgba(45,90,138,0.5)" stroke-width="1.5" />
              <path d="M300 220 L340 260 L300 260 Z" stroke="rgba(45,90,138,0.4)" stroke-width="1" fill="rgba(30,58,95,0.15)" />
              <text x="48" y="56" fill="rgba(45,90,138,0.6)" font-size="10" font-family="monospace">MASS CONNECTED</text>
              <text x="48" y="308" fill="rgba(45,90,138,0.4)" font-size="9" font-family="monospace">MARKETPLACE</text>
            </svg>
            <div class="blueprint-corner blueprint-corner--tl" />
            <div class="blueprint-corner blueprint-corner--br" />
          </div>
        </div>
      </div>
      <div class="hero-metrics">
        <div class="container metrics-grid">
          <div v-for="(item, idx) in heroMetrics" :key="idx" class="metric-item">
            <span class="metric-value">{{ item.value }}</span>
            <span class="metric-label">{{ item.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Company Intro -->
    <section class="section section-intro">
      <div class="container intro-grid">
        <div class="intro-content">
          <span class="section-eyebrow">{{ t('home.intro.eyebrow') }}</span>
          <h2>{{ t('home.intro.title') }}</h2>
          <p class="section-desc">{{ t('home.intro.desc') }}</p>
          <RouterLink to="/about" class="btn btn-ghost">{{ t('home.intro.linkAbout') }} →</RouterLink>
        </div>
        <div class="intro-visual blueprint-bg">
          <div class="intro-visual-inner">
            <div class="intro-block" />
            <div class="intro-block intro-block--sm" />
            <div class="intro-block intro-block--accent" />
          </div>
        </div>
      </div>
    </section>

    <template v-if="loading">
      <p class="state-message container">{{ t('common.loading') }}</p>
    </template>

    <template v-else>
      <!-- Manufacturing Processes -->
      <section class="section section-surface">
        <div class="container">
          <div class="section-header section-header--row">
            <div>
              <span class="section-eyebrow">{{ t('home.processes.eyebrow') }}</span>
              <h2>{{ t('home.processes.title') }}</h2>
            </div>
            <RouterLink to="/rfq/new" class="btn btn-ghost">{{ t('home.processes.viewAll') }} →</RouterLink>
          </div>
          <div v-if="processes.length" class="grid-4">
            <RouterLink
              v-for="item in processes"
              :key="item.id"
              :to="`/rfq/new?category=${item.slug}`"
              class="process-tile"
            >
              <span class="process-tile-name">{{ pickI18n(item.name) }}</span>
              <span class="process-tile-cta">{{ t('home.processes.quote') }} →</span>
            </RouterLink>
          </div>
          <p v-else class="state-message">{{ t('home.processes.empty') }}</p>
        </div>
      </section>

      <!-- How It Works -->
      <section class="section">
        <div class="container">
          <div class="section-header">
            <span class="section-eyebrow">{{ t('home.howItWorks.eyebrow') }}</span>
            <h2>{{ t('home.howItWorks.title') }}</h2>
          </div>
          <div class="grid-3">
            <article v-for="(item, idx) in howItWorksItems" :key="idx" class="cap-card">
              <span class="step-badge">{{ String(idx + 1).padStart(2, '0') }}</span>
              <h3>{{ item.title }}</h3>
              <p>{{ item.desc }}</p>
            </article>
          </div>
        </div>
      </section>

      <!-- Roles -->
      <section class="section section-dark">
        <div class="container">
          <div class="section-header">
            <span class="section-eyebrow services-eyebrow">{{ t('home.roles.eyebrow') }}</span>
            <h2>{{ t('home.roles.title') }}</h2>
          </div>
          <div class="grid-2 roles-grid">
            <article v-for="role in roleCards" :key="role.link" class="role-card">
              <h3>{{ role.title }}</h3>
              <p>{{ role.desc }}</p>
              <RouterLink :to="role.link" :class="['btn', role.primary ? 'btn-primary' : 'btn-secondary', 'role-cta']">
                {{ role.cta }}
              </RouterLink>
            </article>
          </div>
        </div>
      </section>

      <!-- Cases -->
      <section class="section section-surface">
        <div class="container">
          <div class="section-header section-header--row">
            <div>
              <span class="section-eyebrow">{{ t('home.cases.eyebrow') }}</span>
              <h2>{{ t('home.cases.title') }}</h2>
            </div>
            <RouterLink to="/cases" class="btn btn-ghost">{{ t('home.cases.viewAll') }} →</RouterLink>
          </div>
          <div v-if="cases.length" class="grid-3">
            <article v-for="item in cases" :key="item.id" class="card">
              <RouterLink :to="`/cases/${item.id}`" class="card-link">
                <div class="card-thumb">
                  <span class="card-thumb-label">CASE</span>
                </div>
                <div class="card-body">
                  <h3 class="card-title">{{ pickI18n(item.title) }}</h3>
                  <p v-if="item.summary" class="card-meta card-summary">{{ pickI18n(item.summary) }}</p>
                </div>
              </RouterLink>
            </article>
          </div>
          <p v-else class="state-message">{{ t('home.cases.empty') }}</p>
        </div>
      </section>

      <!-- News -->
      <section class="section">
        <div class="container">
          <div class="section-header section-header--row">
            <div>
              <span class="section-eyebrow">{{ t('home.news.eyebrow') }}</span>
              <h2>{{ t('home.news.title') }}</h2>
            </div>
            <RouterLink to="/news" class="btn btn-ghost">{{ t('home.news.viewAll') }} →</RouterLink>
          </div>
          <div v-if="news.length" class="grid-3">
            <article v-for="item in news" :key="item.id" class="card news-card">
              <RouterLink :to="`/news/${item.id}`" class="card-link">
                <div class="card-body">
                  <time v-if="item.published_at" class="card-meta news-date">
                    {{ item.published_at.slice(0, 10) }}
                  </time>
                  <h3 class="card-title">{{ pickI18n(item.title) }}</h3>
                  <p v-if="item.summary" class="card-meta card-summary">{{ pickI18n(item.summary) }}</p>
                </div>
              </RouterLink>
            </article>
          </div>
          <p v-else class="state-message">{{ t('home.news.empty') }}</p>
        </div>
      </section>
    </template>

    <!-- CTA Banner -->
    <section class="section section-cta">
      <div class="container cta-inner">
        <div class="cta-content">
          <h2>{{ t('home.cta.title') }}</h2>
          <p>{{ t('home.cta.desc') }}</p>
        </div>
        <div class="cta-actions">
          <RouterLink to="/rfq/new" class="btn btn-primary">{{ t('home.cta.rfq') }}</RouterLink>
          <RouterLink to="/shop" class="btn btn-secondary cta-btn-light">{{ t('home.cta.shop') }}</RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.home {
  overflow-x: hidden;
}

/* Hero */
.hero {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.hero-inner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3xl);
  align-items: center;
  padding-block: var(--space-4xl) var(--space-3xl);
}

.hero-eyebrow {
  animation: fadeUp 0.6s var(--ease-out) both;
}

.hero-title {
  white-space: pre-line;
  margin-top: var(--space-md);
  animation: fadeUp 0.6s var(--ease-out) 0.08s both;
}

.hero-subtitle {
  margin-top: var(--space-lg);
  font-size: 1.0625rem;
  line-height: 1.75;
  color: var(--color-text);
  max-width: 28rem;
  animation: fadeUp 0.6s var(--ease-out) 0.16s both;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
  margin-top: var(--space-xl);
  animation: fadeUp 0.6s var(--ease-out) 0.24s both;
}

.hero-visual {
  animation: fadeUp 0.7s var(--ease-out) 0.2s both;
}

.blueprint-panel {
  position: relative;
  aspect-ratio: 5 / 4;
  background: var(--color-ink-soft);
  border: 1px solid rgba(45, 90, 138, 0.3);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background-image:
    linear-gradient(rgba(45, 90, 138, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(45, 90, 138, 0.12) 1px, transparent 1px);
  background-size: 20px 20px;
}

.blueprint-svg {
  width: 100%;
  height: 100%;
  padding: var(--space-md);
}

.blueprint-corner {
  position: absolute;
  width: 16px;
  height: 16px;
  border-color: rgba(45, 90, 138, 0.6);
  border-style: solid;
  border-width: 0;

  &--tl {
    top: 12px;
    left: 12px;
    border-top-width: 2px;
    border-left-width: 2px;
  }

  &--br {
    bottom: 12px;
    right: 12px;
    border-bottom-width: 2px;
    border-right-width: 2px;
  }
}

.hero-metrics {
  background: var(--color-ink);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-lg);
  padding-block: var(--space-xl);
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding-inline: var(--space-md);
  border-left: 1px solid rgba(255, 255, 255, 0.1);

  &:first-child {
    border-left: none;
    padding-left: 0;
  }
}

.metric-value {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #fff;
  font-variant-numeric: tabular-nums;
}

.metric-label {
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.45);
}

/* Intro */
.intro-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3xl);
  align-items: center;
}

.intro-visual {
  border-radius: var(--radius-lg);
  min-height: 280px;
  padding: var(--space-xl);
}

.intro-visual-inner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: var(--space-md);
  height: 100%;
}

.intro-block {
  background: rgba(45, 90, 138, 0.2);
  border: 1px solid rgba(45, 90, 138, 0.35);
  border-radius: var(--radius-md);
  min-height: 100px;

  &--sm {
    min-height: 60px;
  }

  &--accent {
    grid-column: 1 / -1;
    background: rgba(30, 58, 95, 0.35);
    min-height: 80px;
  }
}

/* Sections */
.section-surface {
  background: var(--color-surface);
  border-block: 1px solid var(--color-border);
}

.section-dark {
  background: var(--color-ink-soft);
  color: rgba(255, 255, 255, 0.85);

  h2 {
    color: #fff;
  }

  .section-desc,
  .services-desc {
    color: rgba(255, 255, 255, 0.65);
  }
}

.services-eyebrow {
  color: rgba(45, 90, 138, 0.9);
  filter: brightness(1.4);
}

.services-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3xl);
  align-items: center;
}

.services-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.services-steps li {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-lg);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
}

.step-num {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: rgba(45, 90, 138, 0.9);
  filter: brightness(1.3);
  flex-shrink: 0;
}

.step-text {
  font-size: 1rem;
  font-weight: 500;
  color: #fff;
}

/* Capability cards */
.cap-card {
  padding: var(--space-xl);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: border-color var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out);

  h3 {
    font-size: 1.0625rem;
    margin-bottom: var(--space-sm);
  }

  p {
    font-size: 0.9375rem;
    color: var(--color-text);
    line-height: 1.6;
    margin-bottom: var(--space-lg);
  }

  &:hover {
    border-color: var(--color-steel);
    box-shadow: var(--shadow-md);
  }
}

.cap-index {
  width: 32px;
  height: 3px;
  background: var(--color-steel);
  margin-bottom: var(--space-lg);
  border-radius: 1px;
}

.step-badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-steel);
  margin-bottom: var(--space-md);
}

.roles-grid {
  margin-top: var(--space-xl);
}

.role-card {
  padding: var(--space-2xl);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-lg);

  h3 {
    font-size: 1.25rem;
    color: #fff;
    margin-bottom: var(--space-md);
  }

  p {
    font-size: 0.9375rem;
    line-height: 1.7;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: var(--space-xl);
  }
}

.role-cta {
  display: inline-flex;
}

.role-card .btn-secondary {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.25);
  color: #fff;

  &:hover {
    background: rgba(255, 255, 255, 0.14);
    border-color: rgba(255, 255, 255, 0.4);
    color: #fff;
  }
}

.cap-link {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-steel);
  text-decoration: none;

  &:hover {
    color: var(--color-steel-light);
  }
}

.process-tile {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--space-lg);
  min-height: 120px;
  padding: var(--space-xl);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-decoration: none;
  transition: border-color var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out);

  &:hover {
    border-color: var(--color-steel);
    box-shadow: var(--shadow-md);
  }
}

.process-tile-name {
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--color-text-heading);
}

.process-tile-cta {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-steel);
}

.card-summary {
  margin-top: var(--space-xs);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-card .card-body {
  padding-block: var(--space-xl);
}

.news-date {
  display: block;
  margin-bottom: var(--space-sm);
}

/* CTA */
.section-cta {
  padding-block: var(--space-3xl);
  background: linear-gradient(135deg, var(--color-steel) 0%, var(--color-ink-soft) 100%);
}

.cta-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2xl);
  flex-wrap: wrap;
}

.cta-content {
  h2 {
    color: #fff;
    margin-bottom: var(--space-md);
  }

  p {
    color: rgba(255, 255, 255, 0.75);
    font-size: 1.0625rem;
    max-width: 32rem;
  }
}

.cta-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
}

.cta-btn-light {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.35);
  color: #fff;

  &:hover {
    background: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.5);
    color: #fff;
  }
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1024px) {
  .hero-inner,
  .intro-grid,
  .services-grid {
    grid-template-columns: 1fr;
    gap: var(--space-2xl);
  }

  .hero-visual {
    order: -1;
    max-width: 480px;
  }

  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .metric-item:nth-child(3) {
    border-left: none;
    padding-left: 0;
  }
}

@media (max-width: 640px) {
  .hero-inner {
    padding-block: var(--space-3xl) var(--space-2xl);
  }

  .metrics-grid {
    grid-template-columns: 1fr;
    gap: var(--space-md);
  }

  .metric-item {
    border-left: none;
    padding-left: 0;
    padding-block: var(--space-sm);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);

    &:last-child {
      border-bottom: none;
    }
  }

  .cta-inner {
    flex-direction: column;
    align-items: flex-start;
  }

  .cta-actions {
    width: 100%;

    .btn {
      flex: 1;
      min-width: 140px;
    }
  }
}
</style>
