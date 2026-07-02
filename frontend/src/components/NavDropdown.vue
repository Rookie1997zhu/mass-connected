<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

const isExternal = (path) => /^https?:\/\//i.test(path || '')

defineProps({
  label: { type: String, required: true },
  items: { type: Array, required: true },
})

const open = ref(false)
</script>

<template>
  <div class="nav-dropdown" @mouseenter="open = true" @mouseleave="open = false">
    <button type="button" class="nav-dropdown-trigger" :aria-expanded="open">
      {{ label }}
      <span class="nav-dropdown-caret">▾</span>
    </button>
    <div v-show="open" class="nav-dropdown-menu">
      <template v-for="item in items" :key="item.path || item.label">
        <a
          v-if="isExternal(item.path)"
          :href="item.path"
          class="nav-dropdown-item"
          :target="item.openInNewTab ? '_blank' : undefined"
          :rel="item.openInNewTab ? 'noopener noreferrer' : undefined"
          @click="open = false"
        >
          {{ item.label }}
        </a>
        <RouterLink
          v-else
          :to="item.path"
          class="nav-dropdown-item"
          :target="item.openInNewTab ? '_blank' : undefined"
          @click="open = false"
        >
          {{ item.label }}
        </RouterLink>
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.nav-dropdown {
  position: relative;
}

.nav-dropdown-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  white-space: nowrap;

  &:hover {
    color: var(--color-steel);
  }
}

.nav-dropdown-caret {
  font-size: 0.65rem;
  opacity: 0.7;
}

.nav-dropdown-menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  min-width: 11rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: 0.375rem;
  z-index: 200;

  // 填补触发按钮与菜单之间的空隙，避免鼠标移入时触发 mouseleave 导致菜单收起
  &::before {
    content: '';
    position: absolute;
    top: -0.5rem;
    left: 0;
    right: 0;
    height: 0.5rem;
  }
}

.nav-dropdown-item {
  display: block;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: var(--color-text);
  text-decoration: none;
  border-radius: var(--radius-sm);

  &:hover,
  &.router-link-active {
    background: var(--color-steel-muted);
    color: var(--color-steel);
  }
}
</style>
