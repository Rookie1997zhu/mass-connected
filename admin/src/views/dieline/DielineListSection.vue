<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  categories: { type: Array, default: () => [] },
  items: { type: Array, default: () => [] },
})

defineEmits([
  'create-category',
  'edit-category',
  'delete-category',
  'create-template',
  'edit-template',
  'open-assets',
  'delete-template',
])

const { t } = useI18n()

const formatDims = (l, w, h) => `${l}×${w}×${h}`
</script>

<template>
  <div>
    <section class="section-block">
      <div class="toolbar">
        <h2>{{ t('dielineTemplates.categoryTitle') }}</h2>
        <el-button type="primary" @click="$emit('create-category')">{{ t('dielineTemplates.createCategory') }}</el-button>
      </div>
      <el-table :data="categories" size="small">
        <el-table-column prop="code" :label="t('dielineTemplates.categoryCode')" width="100" />
        <el-table-column :label="t('dielineTemplates.name')" min-width="140">
          <template #default="{ row }">{{ row.name_i18n?.zh || row.name_i18n?.en || row.code }}</template>
        </el-table-column>
        <el-table-column prop="sort_order" :label="t('dielineTemplates.sortOrder')" width="80" />
        <el-table-column :label="t('dielineTemplates.enabled')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? t('dielineTemplates.active') : t('dielineTemplates.inactive') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="$emit('edit-category', row)">{{ t('common.edit') }}</el-button>
            <el-button size="small" type="danger" @click="$emit('delete-category', row)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="section-block">
      <div class="toolbar">
        <h2>{{ t('dielineTemplates.title') }}</h2>
        <el-button type="primary" @click="$emit('create-template')">{{ t('common.create') }}</el-button>
      </div>
      <el-table :data="items">
        <el-table-column prop="code" :label="t('dielineTemplates.code')" width="90" />
        <el-table-column prop="category_code" :label="t('dielineTemplates.category')" width="90" />
        <el-table-column prop="engine_key" :label="t('dielineTemplates.engine')" width="140" />
        <el-table-column :label="t('dielineTemplates.name')" min-width="140">
          <template #default="{ row }">{{ row.name_i18n?.zh || row.name_i18n?.en || row.code }}</template>
        </el-table-column>
        <el-table-column :label="t('dielineTemplates.defaults')" min-width="280">
          <template #default="{ row }">
            <div class="dim-summary">
              <span>{{ t('dielineTemplates.dimManufacturing') }}: {{ formatDims(row.default_manufacturing_length_mm ?? row.default_length_mm, row.default_manufacturing_width_mm ?? row.default_width_mm, row.default_manufacturing_height_mm ?? row.default_height_mm) }}</span>
              <span>{{ t('dielineTemplates.dimInternal') }}: {{ formatDims(row.default_internal_length_mm, row.default_internal_width_mm, row.default_internal_height_mm) }}</span>
              <span>{{ t('dielineTemplates.dimExternal') }}: {{ formatDims(row.default_external_length_mm, row.default_external_width_mm, row.default_external_height_mm) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('dielineTemplates.thumbnail')" width="90">
          <template #default="{ row }">
            <img v-if="row.thumbnail_url" :src="row.thumbnail_url" alt="" class="thumb" />
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" :label="t('dielineTemplates.sortOrder')" width="80" />
        <el-table-column :label="t('dielineTemplates.enabled')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? t('dielineTemplates.active') : t('dielineTemplates.inactive') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('dielineTemplates.parametricAsset')" width="130">
          <template #default="{ row }">
            <el-tag :type="row.parametric_asset_status === 'mapped' ? 'success' : 'info'" size="small">
              {{ row.parametric_asset_status || 'none' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="240">
          <template #default="{ row }">
            <el-button size="small" @click="$emit('edit-template', row)">{{ t('common.edit') }}</el-button>
            <el-button size="small" @click="$emit('open-assets', row)">{{ t('dielineTemplates.assets') }}</el-button>
            <el-button size="small" type="danger" @click="$emit('delete-template', row)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.section-block {
  margin-bottom: 2rem;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}
.thumb {
  width: 48px;
  height: 36px;
  object-fit: contain;
  border-radius: 4px;
  background: #f5f5f5;
}
.dim-summary {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  font-size: 0.82rem;
  line-height: 1.35;
}
</style>
