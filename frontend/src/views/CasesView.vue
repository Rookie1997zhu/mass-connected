<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Swiper from 'swiper'
import 'swiper/css'
import PageShell from '../components/PageShell.vue'
import { fetchCases } from '../api'

const { locale, t } = useI18n()
const items = ref([])
const casesSwiperEl = ref(null)
let casesSwiper = null
let mobileQuery = null

const pick = (field) => {
  if (!field || typeof field !== 'object') return field || ''
  return field[locale.value] || field.ko || field.en || ''
}

const destroyCasesSwiper = () => {
  casesSwiper?.destroy(true, true)
  casesSwiper = null
}

const syncCasesSwiper = async () => {
  await nextTick()
  destroyCasesSwiper()
  if (!mobileQuery?.matches || !casesSwiperEl.value) return
  casesSwiper = new Swiper(casesSwiperEl.value, {
    slidesPerView: 1.15,
    spaceBetween: 16,
    grabCursor: true,
    allowTouchMove: true,
  })
}

onMounted(async () => {
  mobileQuery = window.matchMedia('(max-width: 768px)')
  mobileQuery.addEventListener('change', syncCasesSwiper)
  try {
    const res = await fetchCases()
    items.value = res.data.items || []
  } catch {
    items.value = []
  }
  await syncCasesSwiper()
})

onUnmounted(() => {
  mobileQuery?.removeEventListener('change', syncCasesSwiper)
  destroyCasesSwiper()
})
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('nav.cases') }}</h1>
    <p v-if="!items.length" class="page-empty">{{ $t('common.empty') }}</p>
    <template v-else>
      <div class="grid-3 cases-desktop">
        <article v-for="item in items" :key="item.id" class="card">
          <RouterLink :to="`/cases/${item.id}`" class="card-link">
            <div class="card-thumb"><span class="card-thumb-label">CASE</span></div>
            <div class="card-body">
              <h3 class="card-title">{{ pick(item.title) }}</h3>
            </div>
          </RouterLink>
        </article>
      </div>
      <div ref="casesSwiperEl" class="swiper cases-mobile">
        <div class="swiper-wrapper">
          <article v-for="item in items" :key="`slide-${item.id}`" class="swiper-slide">
            <div class="card">
              <RouterLink :to="`/cases/${item.id}`" class="card-link">
                <div class="card-thumb"><span class="card-thumb-label">CASE</span></div>
                <div class="card-body">
                  <h3 class="card-title">{{ pick(item.title) }}</h3>
                </div>
              </RouterLink>
            </div>
          </article>
        </div>
      </div>
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.cases-mobile {
  display: none;
}

.cases-mobile .card {
  height: 100%;
}

@media (max-width: 768px) {
  .cases-desktop {
    display: none;
  }

  .cases-mobile {
    display: block;
  }
}
</style>
