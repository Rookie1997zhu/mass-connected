<script setup>
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../../stores/auth'
import { downloadAuthedFile } from '../../../utils/downloadAuthedFile'

defineProps({
  activeTab: { type: String, required: true },
  profileAttachments: { type: Array, default: () => [] },
  profileError: { type: String, default: '' },
})

const profileForm = defineModel('profileForm', { type: Object, required: true })
const companyFileCategory = defineModel('companyFileCategory', { type: String, default: 'company_profile' })

defineEmits([
  'company-file-change',
  'upload-company-attachment',
  'remove-company-attachment',
  'license-file-change',
  'save-profile',
])

const { t } = useI18n()
const auth = useAuthStore()

const employeeScaleOptions = [
  { value: '', labelKey: 'mypage.employeeScaleEmpty' },
  { value: '<20', labelKey: 'mypage.employeeScaleLt20' },
  { value: '20-50', labelKey: 'mypage.employeeScale20to50' },
  { value: '50-100', labelKey: 'mypage.employeeScale50to100' },
  { value: '100-300', labelKey: 'mypage.employeeScale100to300' },
  { value: '300+', labelKey: 'mypage.employeeScale300plus' },
]
</script>

<template>
  <div class="form-box">
    <template v-if="activeTab === 'settings'">
      <label>{{ t('mypage.contactPersonName') }}<input v-model="profileForm.name" type="text" /></label>
      <label>{{ t('account.phone') }}<input v-model="profileForm.phone" type="text" /></label>
    </template>
    <template v-else-if="activeTab === 'profile' && auth.isEnterprise">
      <h3 class="form-section-title">{{ t('mypage.profileSectionBasic') }}</h3>
      <p class="hint">{{ t('mypage.profileSectionBasicHint') }}</p>
      <label>
        {{ t('mypage.companyName') }}
        <span class="req">*</span>
        <input v-model="profileForm.company_name" type="text" required />
      </label>
      <label>{{ t('mypage.shortName') }}<input v-model="profileForm.short_name" type="text" /></label>
      <label>{{ t('mypage.country') }}<input v-model="profileForm.country" type="text" /></label>
      <label>{{ t('mypage.city') }}<input v-model="profileForm.city" type="text" /></label>
      <label>
        {{ t('mypage.intro') }}
        <textarea
          v-model="profileForm.intro"
          rows="3"
          :placeholder="t('mypage.introPlaceholder')"
        />
      </label>
      <label>
        {{ t('quoteDetail.mainProducts') }}
        <span class="hint-inline">{{ t('mypage.recommended') }}</span>
        <textarea
          v-model="profileForm.main_products"
          rows="2"
          :placeholder="t('mypage.mainProductsPlaceholder')"
        />
      </label>

      <h3 class="form-section-title">{{ t('mypage.profileSectionCapability') }}</h3>
      <p class="hint">{{ t('mypage.profileSectionCapabilityHint') }}</p>
      <label>
        {{ t('quoteDetail.establishedYear') }}
        <input v-model="profileForm.established_year" type="number" min="1900" />
      </label>
      <label>
        {{ t('quoteDetail.employeeScale') }}
        <select v-model="profileForm.employee_scale">
          <option v-for="opt in employeeScaleOptions" :key="opt.value || 'empty'" :value="opt.value">
            {{ t(opt.labelKey) }}
          </option>
        </select>
      </label>
      <label>
        {{ t('quoteDetail.factoryArea') }}
        <span class="hint-inline">{{ t('mypage.factoryAreaHint') }}</span>
        <input v-model="profileForm.factory_area_sqm" type="number" min="0" />
      </label>
      <label>
        {{ t('quoteDetail.monthlyCapacity') }}
        <span class="hint-inline">{{ t('mypage.monthlyCapacityHint') }}</span>
        <input v-model="profileForm.monthly_capacity" type="text" />
      </label>
      <label>
        {{ t('quoteDetail.certifications') }}
        <span class="hint-inline">{{ t('mypage.certEquipmentHint') }}</span>
        <textarea v-model="profileForm.quality_certifications" rows="2" />
      </label>
      <label>
        {{ t('quoteDetail.equipment') }}
        <span class="hint-inline">{{ t('mypage.certEquipmentHint') }}</span>
        <textarea v-model="profileForm.equipment_summary" rows="2" />
      </label>

      <p class="hint">{{ t('mypage.publicProfileHint') }}</p>
      <template v-if="auth.isSupplier">
        <h3 class="form-section-title">{{ t('mypage.profileSectionAttachments') }}</h3>
        <p class="hint">{{ t('mypage.profileSectionAttachmentsHint') }}</p>
        <div class="company-att-box">
          <h3>{{ t('mypage.publicAttachments') }}</h3>
          <ul v-if="profileAttachments.length" class="att-mini">
            <li v-for="a in profileAttachments" :key="a.id">
              <span>{{ a.file_name }} · {{ a.category }} · {{ a.is_public ? t('mypage.public') : t('mypage.private') }}</span>
              <button type="button" class="btn btn-secondary btn-sm" @click="$emit('remove-company-attachment', a.id)">
                {{ t('quoteRequest.removeAttachment') }}
              </button>
            </li>
          </ul>
          <label>
            {{ t('mypage.attachmentCategory') }}
            <select v-model="companyFileCategory">
              <option value="company_profile">{{ t('mypage.catCompanyProfile') }}</option>
              <option value="certification">{{ t('mypage.catCertification') }}</option>
              <option value="equipment">{{ t('mypage.catEquipment') }}</option>
              <option value="case">{{ t('mypage.catCase') }}</option>
            </select>
          </label>
          <label>{{ t('mypage.uploadPublicAttachment') }}<input type="file" @change="$emit('company-file-change', $event)" /></label>
          <button type="button" class="btn btn-secondary btn-sm" @click="$emit('upload-company-attachment')">
            {{ t('mypage.uploadPublicAttachment') }}
          </button>
        </div>
      </template>
      <label v-if="auth.user?.role !== 'factory'">{{ t('mypage.businessLicense') }}<input type="file" @change="$emit('license-file-change', $event)" /></label>
      <p v-if="auth.factoryProfile?.business_license_url" class="hint">
        <button
          type="button"
          class="link"
          @click="downloadAuthedFile(auth.factoryProfile.business_license_url, 'license')"
        >
          {{ t('mypage.viewLicense') }}
        </button>
      </p>
    </template>
    <p v-else-if="auth.isEnterprise && auth.factoryProfile" class="hint">
      {{ auth.factoryProfile.company_name }} · {{ auth.factoryProfile.status }}
    </p>
    <p v-if="profileError" class="page-message page-message--error">{{ profileError }}</p>
    <button type="button" class="btn btn-primary btn-sm" @click="$emit('save-profile')">{{ t('mypage.save') }}</button>
  </div>
</template>

<style scoped lang="scss">
.link { color: var(--color-steel); cursor: pointer; }
.form-box {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  max-width: 480px;
  label {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    font-size: 0.875rem;
  }
  input, select {
    padding: 0.625rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    font: inherit;
  }
  .hint { font-size: 0.8rem; opacity: 0.7; margin: 0; }
}
.form-section-title { margin: var(--space-md) 0 0; font-size: 1rem; font-weight: 600; }
.form-section-title:first-child { margin-top: 0; }
.req { color: #b91c1c; margin-left: 0.15rem; }
.hint-inline { font-size: 0.72rem; opacity: 0.55; font-weight: 400; margin-left: 0.35rem; }
.form-box textarea { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); font: inherit; }
.company-att-box {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  h3 { margin: 0; font-size: 0.95rem; }
}
.att-mini {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  li { display: flex; justify-content: space-between; gap: 0.5rem; align-items: center; font-size: 0.85rem; }
}
</style>
