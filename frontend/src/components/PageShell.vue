<script setup>
defineProps({
  centered: { type: Boolean, default: false },
  wide: { type: Boolean, default: false },
})
</script>

<template>
  <section class="page" :class="{ 'page--centered': centered }">
    <div
      class="container"
      :class="{ 'page-card': centered, 'page-card--wide': centered && wide }"
    >
      <slot />
    </div>
  </section>
</template>

<style scoped lang="scss">
.page {
  flex: 1;
  padding-block: var(--space-3xl);
}

.page--centered {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100dvh - var(--header-height) - 220px);
  padding-block: var(--space-2xl);
}

.page-card {
  width: 100%;
  max-width: 420px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2xl);
  box-shadow: var(--shadow-md);
}

.page-card--wide {
  max-width: 560px;
}
</style>
