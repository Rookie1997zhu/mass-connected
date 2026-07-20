/**
 * Quote param grouping + Chinese label/unit fallbacks for admin config UI.
 * Display priority: row.label → META.label → param_key; unit: row.unit → META.unit.
 */

const startsWith = (prefix) => (key) => String(key || '').startsWith(prefix)
const equalsAny = (...keys) => (key) => keys.includes(key)
const matchesAny = (...preds) => (key) => preds.some((fn) => fn(key))

const MATERIALS = ['ABS', 'ABS_Gf', 'PC', 'PA66', 'PP']

function materialMeta(prefix, labelTpl, unit) {
  const out = {}
  for (const m of MATERIALS) {
    out[`${prefix}${m}`] = { label: labelTpl.replace('{m}', m.replace('_', ' ')), unit }
  }
  return out
}

export const PARAM_META = {
  injection: {
    ...materialMeta('mold_base_', '{m} 模具基础价', 'RMB'),
    ...materialMeta('unit_price_kg_', '{m} 材料单价', 'RMB/kg'),
    ...materialMeta('unit_base_', '{m} 基础件价', 'RMB'),
    ...materialMeta('density_', '{m} 密度', 'g/cm³'),
    slider_unit: { label: '滑块每个加价', unit: 'RMB' },
    precision_add: { label: '精密度 ≤0.2mm 加价', unit: 'RMB' },
    loss_factor: { label: '耗材重量系数（含流道/损耗）', unit: '' },
    color_transparent: { label: '透明色加价率', unit: 'rate' },
    color_semi: { label: '半透明色加价率', unit: 'rate' },
    packaging_rate: { label: '包装费率', unit: 'rate' },
    profit_rate: { label: '利润率', unit: 'rate' },
    rmb_to_krw: { label: 'RMB→KRW 展示汇率', unit: 'KRW/RMB' },
    moq_kg: { label: '未指定色号时 MOQ', unit: 'kg' },
  },
  print3d: {
    pricing_mode: { label: '计价模式(0=成本累加,1=按克)', unit: '' },
    base_cost: { label: '基础费用', unit: 'KRW' },
    electricity_rate_per_kwh: { label: '电费单价', unit: 'KRW/kWh' },
    printer_power_watts: { label: '打印机功率', unit: 'W' },
    depreciation_per_hour: { label: '设备折旧/时', unit: 'KRW/h' },
    other_costs_per_print: { label: '其他成本/件', unit: 'KRW' },
    gst_rate: { label: '税率(小数)', unit: '' },
    loss_factor: { label: '材料损耗系数', unit: '' },
    rush_factor: { label: '加急系数', unit: '' },
    machine_hour_rate: { label: '机时费率(兼容)', unit: 'KRW/h' },
    default_infill: { label: '默认填充率', unit: '%' },
    slicer_timeout_seconds: { label: '切片超时', unit: 's' },
    max_file_size_mb: { label: '上传大小上限', unit: 'MB' },
    material_price_PLA: { label: 'PLA 单价(兼容)', unit: 'KRW/g' },
    material_price_ABS: { label: 'ABS 单价(兼容)', unit: 'KRW/g' },
    material_price_PETG: { label: 'PETG 单价(兼容)', unit: 'KRW/g' },
    material_price_Resin: { label: 'Resin 单价(兼容)', unit: 'KRW/g' },
    material_price_Nylon: { label: 'Nylon 单价(兼容)', unit: 'KRW/g' },
    material_price_TPU: { label: 'TPU 单价(兼容)', unit: 'KRW/g' },
    post_none: { label: '后处理:无', unit: 'KRW' },
    post_sanding: { label: '后处理:打磨', unit: 'KRW' },
    post_paint: { label: '后处理:喷漆', unit: 'KRW' },
  },
  shipping: {
    usd_to_krw: { label: 'USD→KRW 汇率', unit: 'KRW/USD' },
    cny_to_krw: { label: 'CNY→KRW 汇率', unit: 'KRW/CNY' },
    usd_to_krw_battery: { label: '含电池 LCL USD→KRW', unit: 'KRW/USD' },
    lcl_rate_4day: { label: 'LCL 无电池 4日 $/R/T', unit: 'USD/R/T' },
    lcl_rate_5day: { label: 'LCL 无电池 5日 $/R/T', unit: 'USD/R/T' },
    lcl_min_4day: { label: 'LCL 无电池 4日最低运费', unit: 'USD' },
    lcl_min_5day: { label: 'LCL 无电池 5日最低运费', unit: 'USD' },
    battery_rate_4day: { label: 'LCL 含电池 4日 $/CBM', unit: 'USD/CBM' },
    battery_rate_5day: { label: 'LCL 含电池 5日 $/CBM', unit: 'USD/CBM' },
    battery_min_cbm: { label: '含电池最低计费 CBM', unit: 'CBM' },
    battery_overweight_4day: { label: '含电池超重 4日 ¥/kg', unit: 'CNY/kg' },
    battery_overweight_5day: { label: '含电池超重 5日 ¥/kg', unit: 'CNY/kg' },
    pcb_shipping_under_1kg: { label: 'PCB 配送 ≤1kg 固定费', unit: 'KRW' },
    pcb_shipping_per_kg: { label: 'PCB 配送 ≥2kg 单价', unit: 'KRW/kg' },
  },
  pcba: {
    smt_score_price: { label: 'SMT 每分单价', unit: 'RMB/分' },
    dip_score_price: { label: 'DIP 每分单价', unit: 'RMB/分' },
    rmb_to_krw: { label: 'RMB→KRW 展示汇率', unit: 'KRW/RMB' },
    mask_fee: { label: '钢网费(量产)', unit: 'RMB' },
    smt_test_fee: { label: 'SMT 测试费/PCB', unit: 'RMB' },
    packaging_fee: { label: '包装费/ARRAY', unit: 'RMB' },
    default_smt_score: { label: '未知封装 SMT 默认计分', unit: '分' },
    default_dip_score: { label: '未知封装 DIP 默认计分', unit: '分' },
  },
  pcb: {
    ad_discount_rate: { label: '广告同意折扣率', unit: 'rate' },
    valid_days: { label: '报价有效期(天)', unit: 'day' },
    pcb_manufacturing_margin_rate: { label: 'PCB 样板制造费 margin', unit: 'rate' },
  },
}

const GROUP_DEFS = {
  injection: [
    { id: 'mold', titleKey: 'quoteParams.groupMold', match: startsWith('mold_base_') },
    { id: 'materialPrice', titleKey: 'quoteParams.groupMaterialPrice', match: startsWith('unit_price_kg_') },
    { id: 'unitBase', titleKey: 'quoteParams.groupUnitBase', match: startsWith('unit_base_') },
    { id: 'density', titleKey: 'quoteParams.groupDensity', match: startsWith('density_') },
    {
      id: 'surcharge',
      titleKey: 'quoteParams.groupSurcharge',
      match: matchesAny(
        startsWith('slider_'),
        startsWith('precision_'),
        startsWith('loss_'),
        startsWith('color_'),
        startsWith('packaging_'),
        startsWith('profit_'),
      ),
    },
    {
      id: 'fxMoq',
      titleKey: 'quoteParams.groupFxMoq',
      match: equalsAny('rmb_to_krw', 'moq_kg'),
    },
  ],
  print3d: [
    {
      id: 'costPricing',
      titleKey: 'quoteParams.groupCostPricing',
      match: equalsAny(
        'pricing_mode',
        'base_cost',
        'electricity_rate_per_kwh',
        'printer_power_watts',
        'depreciation_per_hour',
        'other_costs_per_print',
        'gst_rate',
        'loss_factor',
        'rush_factor',
        'machine_hour_rate',
        'default_infill',
      ),
    },
    {
      id: 'materialCompat',
      titleKey: 'quoteParams.groupMaterialCompat',
      match: startsWith('material_price_'),
    },
    {
      id: 'postProcess',
      titleKey: 'quoteParams.groupPostProcess',
      match: startsWith('post_'),
    },
    {
      id: 'slicerLimits',
      titleKey: 'quoteParams.groupSlicerLimits',
      match: equalsAny('slicer_timeout_seconds', 'max_file_size_mb'),
    },
  ],
  shipping: [
    {
      id: 'fx',
      titleKey: 'quoteParams.groupFx',
      match: matchesAny(startsWith('usd_to_krw'), startsWith('cny_to_krw')),
    },
    {
      id: 'lclNoBattery',
      titleKey: 'quoteParams.groupLclNoBattery',
      match: matchesAny(startsWith('lcl_rate_'), startsWith('lcl_min_')),
    },
    {
      id: 'lclBattery',
      titleKey: 'quoteParams.groupLclBattery',
      match: matchesAny(startsWith('battery_')),
    },
    {
      id: 'pcbShip',
      titleKey: 'quoteParams.groupPcbShip',
      match: startsWith('pcb_shipping_'),
    },
  ],
  pcba: [
    {
      id: 'scorePrice',
      titleKey: 'quoteParams.groupScorePrice',
      match: equalsAny('smt_score_price', 'dip_score_price'),
    },
    {
      id: 'fees',
      titleKey: 'quoteParams.groupFees',
      match: equalsAny('mask_fee', 'smt_test_fee', 'packaging_fee'),
    },
    {
      id: 'defaultScore',
      titleKey: 'quoteParams.groupDefaultScore',
      match: equalsAny('default_smt_score', 'default_dip_score'),
    },
    {
      id: 'fx',
      titleKey: 'quoteParams.groupFx',
      match: equalsAny('rmb_to_krw'),
    },
  ],
  pcb: [
    {
      id: 'pcbRules',
      titleKey: 'quoteParams.groupPcbRules',
      match: equalsAny('ad_discount_rate', 'valid_days', 'pcb_manufacturing_margin_rate'),
    },
  ],
}

const OTHER_GROUP = { id: 'other', titleKey: 'quoteParams.groupOther', match: () => true }
const GENERAL_GROUP = { id: 'general', titleKey: 'quoteParams.groupGeneral', match: () => true }

export function getParamMeta(quoteType, paramKey) {
  const map = PARAM_META[quoteType] || {}
  return map[paramKey] || null
}

export function resolveParamLabel(row, quoteType) {
  if (row?.label) return row.label
  const meta = getParamMeta(quoteType, row?.param_key)
  if (meta?.label) return meta.label
  return row?.param_key || ''
}

export function resolveParamUnit(row, quoteType) {
  if (row?.unit) return row.unit
  const meta = getParamMeta(quoteType, row?.param_key)
  return meta?.unit || ''
}

/**
 * @returns {{ id: string, titleKey: string, items: object[] }[]}
 */
export function groupQuoteParams(quoteType, items) {
  const list = Array.isArray(items) ? items : []
  const defs = GROUP_DEFS[quoteType]
  if (!defs || !defs.length) {
    return list.length ? [{ ...GENERAL_GROUP, items: [...list] }] : []
  }

  const used = new Set()
  const groups = []

  for (const def of defs) {
    const matched = list.filter((row) => {
      if (used.has(row.id)) return false
      return def.match(row.param_key)
    })
    matched.forEach((row) => used.add(row.id))
    if (matched.length) {
      groups.push({ id: def.id, titleKey: def.titleKey, items: matched })
    }
  }

  const rest = list.filter((row) => !used.has(row.id))
  if (rest.length) {
    groups.push({ id: OTHER_GROUP.id, titleKey: OTHER_GROUP.titleKey, items: rest })
  }

  return groups
}
