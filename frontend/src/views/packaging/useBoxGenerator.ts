import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import DOMPurify from 'dompurify'
import { convertSimpleQuote, createSimpleQuote, fetchFefcoCatalog } from '../../api'
import {
  buildPreview,
  buildQuoteInputs,
  computeDimViewBox,
  computeGeometry,
  fromMm,
  getDimAnnotations,
  PARAMETRIC_ASSET_REQUIRED,
  renderPreviewLinesSvg,
} from '../../lib/packaging/boxEngine'
import {
  categoriesWithTemplates,
  defaultDimsForTemplate,
  getBoxTemplate,
  getEngineKey,
  resetFefcoCatalog,
  setFefcoCatalogFromApi,
} from '../../lib/packaging/fefcoCatalog'

/**
 * 纸箱生成器页面的状态与业务逻辑（目录加载、几何计算、报价提交）。
 * 预览面板自身的缩放/平移/导出交互见 BoxPreviewPanel.vue。
 */
export function useBoxGenerator() {
  const { t, locale } = useI18n()
  const router = useRouter()
  const route = useRoute()

  const catalogLoading = ref(false)
  const catalogError = ref('')
  const catalogReady = ref(false)

  const productName = ref('')
  const unit = ref('mm')
  const dimensionType = ref('internal')
  const boardType = ref('E')
  const boxCode = ref('')
  const length = ref('')
  const width = ref('')
  const height = ref('')
  const thickness = ref('')
  const quantity = ref('')
  const printColors = ref('')

  const error = ref('')
  const previewError = ref('')
  const result = ref(null)
  const submitting = ref(false)

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

  let suppressDimTypeWatch = false

  const applyTemplateDefaults = (tpl, dimType = dimensionType.value) => {
    if (!tpl) return
    const effectiveDimType = dimType || tpl.defaultDimensionType || 'internal'
    const dims = defaultDimsForTemplate(tpl, effectiveDimType)
    if (!dims?.lengthMm || !dims?.widthMm || !dims?.heightMm) return
    length.value = dims.lengthMm
    width.value = dims.widthMm
    height.value = dims.heightMm
    thickness.value = tpl.defaultThicknessMm ?? ''
    unit.value = 'mm'
  }

  const roundDimForUnit = (mmValue) => {
    const decimals = unit.value === 'in' ? 4 : 1
    return Number(fromMm(mmValue, unit.value).toFixed(decimals))
  }

  const syncDimsForDimensionType = (newType, oldType) => {
    if (!boxCode.value || !oldType || newType === oldType || !hasBoxDims.value) return
    const tpl = getBoxTemplate(boxCode.value)
    if (!tpl?.previewEnabled) return
    try {
      const geo = computeGeometry({
        boxCode: boxCode.value,
        length: Number(length.value),
        width: Number(width.value),
        height: Number(height.value),
        thickness: Number(thickness.value),
        unit: unit.value,
        dimensionType: oldType,
        boardType: boardType.value,
        quantity: Math.max(1, Number(quantity.value) || 1),
        printColors: Math.max(0, Number(printColors.value) || 0),
      })
      const target = geo[newType]
      if (!target) return
      length.value = roundDimForUnit(target.length)
      width.value = roundDimForUnit(target.width)
      height.value = roundDimForUnit(target.height)
    } catch {
      // 尺寸未通过校验时保持用户输入
    }
  }

  const selectedTemplate = computed(() => (boxCode.value ? getBoxTemplate(boxCode.value) : undefined))

  const canQuote = computed(() => selectedTemplate.value?.quoteEnabled ?? false)

  const hasBoxDims = computed(() => {
    const nums = [length.value, width.value, height.value, thickness.value]
    return nums.every((v) => v !== '' && v !== null && Number(v) > 0)
  })

  const params = computed(() => ({
    boxCode: boxCode.value,
    length: Number(length.value),
    width: Number(width.value),
    height: Number(height.value),
    thickness: Number(thickness.value),
    unit: unit.value,
    dimensionType: dimensionType.value,
    boardType: boardType.value,
    quantity: Math.max(1, Number(quantity.value) || 1),
    printColors: Math.max(0, Number(printColors.value) || 0),
  }))

  const preview = computed(() => {
    previewError.value = ''
    if (!boxCode.value) {
      previewError.value = t('packaging.noBoxSelected')
      return null
    }
    if (!hasBoxDims.value) {
      previewError.value = t('packaging.fillDimsFirst')
      return null
    }
    const tpl = getBoxTemplate(boxCode.value)
    if (!tpl?.previewEnabled) {
      previewError.value = t('packaging.previewNotReady')
      return null
    }
    try {
      return buildPreview(params.value)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      previewError.value =
        message === PARAMETRIC_ASSET_REQUIRED ? t('packaging.parametricAssetRequired') : message || t('packaging.invalidDims')
      return null
    }
  })

  const dimAnnotations = computed(() => {
    if (!preview.value) return []
    return getDimAnnotations(
      preview.value,
      unit.value,
      dimensionType.value,
      getEngineKey(boxCode.value),
      selectedTemplate.value?.activeParametricAsset,
    )
  })

  const dimViewBox = computed(() => {
    if (!preview.value) return ''
    return computeDimViewBox(preview.value, dimAnnotations.value)
  })

  const previewLinesSvg = computed(() => {
    if (!preview.value) return ''
    return DOMPurify.sanitize(renderPreviewLinesSvg(preview.value, dimViewBox.value || preview.value.viewBox))
  })

  const onDimFieldUpdate = ({ field, value }) => {
    if (field === 'length') length.value = value
    else if (field === 'width') width.value = value
    else if (field === 'height') height.value = value
  }

  const selectBox = (code) => {
    suppressDimTypeWatch = true
    boxCode.value = code
    const tpl = getBoxTemplate(code)
    if (tpl?.defaultDimensionType) {
      dimensionType.value = tpl.defaultDimensionType
    }
    applyTemplateDefaults(tpl, dimensionType.value)
    suppressDimTypeWatch = false
  }

  const initFromRoute = () => {
    const code = String(route.query.code || '').trim()
    if (!code) {
      boxCode.value = ''
      return
    }
    const tpl = getBoxTemplate(code)
    if (!tpl) {
      catalogError.value = t('packaging.boxNotFound')
      boxCode.value = ''
      return
    }
    selectBox(code)
  }

  watch([length, width, height, thickness, unit, dimensionType, boxCode], () => {
    error.value = ''
  })

  watch(dimensionType, (newType, oldType) => {
    if (suppressDimTypeWatch) return
    syncDimsForDimensionType(newType, oldType)
  })

  watch(
    () => route.query.code,
    () => {
      if (!catalogReady.value) return
      initFromRoute()
    },
  )

  const loadCatalog = async () => {
    catalogLoading.value = true
    catalogError.value = ''
    try {
      const res = await fetchFefcoCatalog()
      setFefcoCatalogFromApi(res.data || {})
      const cats = categoriesWithTemplates()
      if (!cats.length) {
        catalogError.value = t('packaging.catalogEmpty')
        return
      }
      catalogReady.value = true
      initFromRoute()
    } catch {
      resetFefcoCatalog()
      catalogError.value = t('packaging.catalogLoadFailed')
    } finally {
      catalogLoading.value = false
    }
  }

  const goToLibrary = () => {
    router.push({ name: 'packaging-library' })
  }

  const onGenerate = async () => {
    if (!boxCode.value) {
      error.value = t('packaging.noBoxSelected')
      return
    }
    if (!hasBoxDims.value) {
      error.value = t('packaging.fillDimsFirst')
      return
    }
    if (!canQuote.value) {
      error.value = t('packaging.previewNotReady')
      return
    }
    if (!preview.value) {
      error.value = previewError.value || t('packaging.invalidDims')
      return
    }
    error.value = ''
    submitting.value = true
    result.value = null
    try {
      const res = await createSimpleQuote({
        quote_type: 'paper_box',
        product_name: productName.value,
        inputs: buildQuoteInputs(params.value),
      })
      result.value = res.data
    } catch (err) {
      error.value = err.message || t('packaging.failed')
    } finally {
      submitting.value = false
    }
  }

  const onConvert = async () => {
    if (!result.value?.id) return
    try {
      const res = await convertSimpleQuote(result.value.id, {})
      router.push({ name: 'my-rfq-detail', params: { id: res.data.rfq_id } })
    } catch (err) {
      error.value = err.message || t('packaging.failed')
    }
  }

  onMounted(() => {
    loadCatalog()
  })

  return {
    catalogLoading,
    catalogError,
    catalogReady,

    productName,
    unit,
    dimensionType,
    boardType,
    boxCode,
    length,
    width,
    height,
    thickness,
    quantity,
    printColors,

    error,
    result,
    submitting,

    templateLabel,
    selectedTemplate,
    canQuote,
    hasBoxDims,
    params,

    previewError,
    preview,
    dimAnnotations,
    dimViewBox,
    previewLinesSvg,
    onDimFieldUpdate,

    selectBox,
    initFromRoute,
    loadCatalog,
    goToLibrary,
    onGenerate,
    onConvert,
  }
}
