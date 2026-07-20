<template>
  <div class="project-activity-grid">
    <div class="project-activity-grid__main">
      <slot name="main" />
    </div>
    <aside class="project-activity-grid__side">
      <slot name="side" />
    </aside>
  </div>
</template>

<style scoped lang="scss">
.project-activity-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-lg);
  margin-top: var(--space-xl);
}

.project-activity-grid__side {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

@media (min-width: 960px) {
  .project-activity-grid {
    grid-template-columns: minmax(0, 1.45fr) minmax(280px, 1fr);
    align-items: start;
  }

  .project-activity-grid__side {
    position: sticky;
    top: calc(var(--header-height) + 1rem);
    max-height: calc(100dvh - var(--header-height) - 2rem);
    overflow-y: auto;
  }
}
</style>
