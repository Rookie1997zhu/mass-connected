<script setup>
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()
const router = useRouter()

const logout = () => {
  auth.logout()
  router.push('/login')
}

const setLocale = (value) => {
  locale.value = value
  localStorage.setItem('admin_locale', value)
  document.title = t('app.title')
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="brand">{{ t('app.brand') }}</div>
      <el-menu router default-active="/">
        <el-menu-item index="/">{{ t('nav.dashboard') }}</el-menu-item>
        <el-menu-item index="/service-categories">{{ t('nav.serviceCategories') }}</el-menu-item>
        <el-menu-item index="/factories">{{ t('nav.factories') }}</el-menu-item>
        <el-menu-item index="/rfqs">{{ t('nav.rfqs') }}</el-menu-item>
        <el-menu-item index="/categories">{{ t('nav.categories') }}</el-menu-item>
        <el-menu-item index="/products">{{ t('nav.products') }}</el-menu-item>
        <el-menu-item index="/orders">{{ t('nav.orders') }}</el-menu-item>
        <el-menu-item index="/inquiries">{{ t('nav.inquiries') }}</el-menu-item>
        <el-menu-item index="/cases">{{ t('nav.cases') }}</el-menu-item>
        <el-menu-item index="/news">{{ t('nav.news') }}</el-menu-item>
        <el-menu-item index="/faqs">{{ t('nav.faqs') }}</el-menu-item>
        <el-menu-item index="/content-pages">{{ t('nav.pages') }}</el-menu-item>
        <el-menu-item index="/navigation">{{ t('nav.navigation') }}</el-menu-item>
        <el-menu-item index="/admin-users">{{ t('nav.admins') }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <el-select :model-value="locale" class="locale-select" @change="setLocale">
          <el-option label="한국어" value="ko" />
          <el-option label="中文" value="zh" />
          <el-option label="English" value="en" />
        </el-select>
        <div class="header-right">
          <span>{{ auth.user?.email }}</span>
          <el-button @click="logout">{{ t('common.logout') }}</el-button>
        </div>
      </el-header>
      <el-main><RouterView /></el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout { min-height: 100vh; }
.aside { background: #111827; color: #fff; }
.brand { padding: 1rem; font-weight: 700; }
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e5e7eb;
  gap: 1rem;
}
.header-right { display: flex; align-items: center; gap: 1rem; }
.locale-select { width: 120px; }
</style>
