import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import DOMPurify from 'dompurify'
import {
  downloadDielineTemplate,
  fetchDielinePurchases,
  fetchFefcoCatalog,
  fetchPointWallet,
  purchaseDielineTemplate,
} from '../../api'
import {
  buildPreview,
  computeDimViewBox,
  computeGeometry,
  fromMm,
  getDimAnnotations,
  PARAMETRIC_ASSET_REQUIRED,
  renderPreviewLinesSvg,
  toMm,
} from '../../lib/packaging/boxEngine'
import {
  categoriesWithTemplates,
  defaultDimsForTemplate,
  getBoxTemplate,
  getEngineKey,
  resetFefcoCatalog,
  setFefcoCatalogFromApi,
} from '../../lib/packaging/fefcoCatalog'
import { resolveApiMessage } from '../../utils/apiErrors'

/**
 * 纸箱生成器：目录、预览、积分解锁与后端下载。
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
  const submitting = ref(false)
  const unlockedCodes = ref(new Set())
  const pointsBalance = ref(null)
  const downloadBusy = ref(false)

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
    if (!tpl?.previewEnabled || tpl.geometryMode === 'fixed_asset') return
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
      // keep user input when validation fails
    }
  }

  const selectedTemplate = computed(() => (boxCode.value ? getBoxTemplate(boxCode.value) : undefined))
  const isFixedAsset = computed(() => selectedTemplate.value?.geometryMode === 'fixed_asset')
  const canPurchase = computed(() => selectedTemplate.value?.purchaseEnabled ?? false)
  const pointsCost = computed(() => Number(selectedTemplate.value?.pointsCost) || 0)
  const isUnlocked = computed(() => Boolean(boxCode.value && unlockedCodes.value.has(boxCode.value)))

  const hasBoxDims = computed(() => {
    if (isFixedAsset.value) return true
    const nums = [length.value, width.value, height.value, thickness.value]
    return nums.every((v) => v !== '' && v !== null && Number(v) > 0)
  })

  const params = computed(() => ({
    boxCode: boxCode.value,
    length: Number(length.value) || Number(selectedTemplate.value?.defaultLengthMm) || 100,
    width: Number(width.value) || Number(selectedTemplate.value?.defaultWidthMm) || 80,
    height: Number(height.value) || Number(selectedTemplate.value?.defaultHeightMm) || 50,
    thickness: Number(thickness.value) || Number(selectedTemplate.value?.defaultThicknessMm) || 1.5,
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
    if (!preview.value || isFixedAsset.value) return []
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
    if (isFixedAsset.value) return
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

  const refreshUnlockState = async () => {
    try {
      const [purchasesRes, walletRes] = await Promise.all([
        fetchDielinePurchases({ page_size: 200 }),
        fetchPointWallet().catch(() => null),
      ])
      const rows = purchasesRes?.data?.items || purchasesRes?.data?.results || []
      const next = new Set()
      ;(Array.isArray(rows) ? rows : []).forEach((row) => {
        if (row.template_code) next.add(row.template_code)
      })
      unlockedCodes.value = next
      if (walletRes?.data) {
        pointsBalance.value = walletRes.data.balance
      }
    } catch {
      // ignore — unlock state stays empty until login/purchase
    }
  }

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
      await refreshUnlockState()
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

  const onUnlock = async () => {
    if (!boxCode.value) {
      error.value = t('packaging.noBoxSelected')
      return
    }
    if (!canPurchase.value) {
      error.value = t('packaging.previewNotReady')
      return
    }
    error.value = ''
    submitting.value = true
    try {
      const res = await purchaseDielineTemplate({ template_code: boxCode.value })
      const code = res?.data?.template_code || boxCode.value
      unlockedCodes.value = new Set([...unlockedCodes.value, code])
      if (typeof res?.data?.points_spent === 'number' && pointsBalance.value != null) {
        pointsBalance.value = Math.max(0, pointsBalance.value - Number(res.data.points_spent || 0))
      } else {
        await refreshUnlockState()
      }
    } catch (err) {
      const apiCode = err?.response?.data?.code || err?.code
      if (apiCode === 'POINT_INSUFFICIENT') {
        error.value = t('packaging.pointsInsufficient')
      } else {
        error.value = resolveApiMessage(err, t, 'packaging.unlockFailed')
      }
    } finally {
      submitting.value = false
    }
  }

  const triggerBlobDownload = (blob, filename) => {
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const onDownload = async (format) => {
    if (!boxCode.value || !preview.value) return
    if (!isUnlocked.value) {
      error.value = t('packaging.unlockRequired')
      return
    }
    downloadBusy.value = true
    error.value = ''
    try {
      const query = { format }
      if (!isFixedAsset.value) {
        query.length_mm = toMm(Number(length.value), unit.value)
        query.width_mm = toMm(Number(width.value), unit.value)
        query.height_mm = toMm(Number(height.value), unit.value)
        query.thickness_mm = toMm(Number(thickness.value), unit.value)
        query.dimension_type = dimensionType.value
      }
      const res = await downloadDielineTemplate(boxCode.value, query)
      const blob = res instanceof Blob ? res : new Blob([res])
      triggerBlobDownload(blob, `dieline-${boxCode.value}.${format}`)
    } catch (err) {
      error.value = resolveApiMessage(err, t, 'packaging.downloadFailed')
    } finally {
      downloadBusy.value = false
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
    submitting,
    downloadBusy,
    pointsBalance,
    pointsCost,
    isUnlocked,
    isFixedAsset,

    templateLabel,
    selectedTemplate,
    canPurchase,
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
    onUnlock,
    onDownload,
  }
}
