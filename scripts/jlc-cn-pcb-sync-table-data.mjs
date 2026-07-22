import fs from 'node:fs/promises'

const LEGACY_PRICE_LIST = 'scripts/jlc-cn-pcb-manufacturing-price-list.json'
const LEGACY_REPORT = 'scripts/jlc-cn-pcb-validation-report.json'
const V9_PRICE_LIST = 'scripts/jlc-cn-pcb-v9-candidate-price-list.json'
const V9_ACCEPTANCE = 'scripts/jlc-cn-pcb-v9-acceptance-report.json'
const V9_CONSUMPTION = 'scripts/jlc-cn-pcb-v9-acceptance-consumption.json'
const V10_PRICE_LIST = 'scripts/jlc-cn-pcb-v10-candidate-price-list.json'
const V10_ACCEPTANCE = 'scripts/jlc-cn-pcb-v10-acceptance-report.json'
const V10_CONSUMPTION = 'scripts/jlc-cn-pcb-v10-acceptance-consumption.json'
const V11_PRICE_LIST = 'scripts/jlc-cn-pcb-v11-candidate-price-list.json'
const V11_ACCEPTANCE = 'scripts/jlc-cn-pcb-v11-acceptance-report.json'
const V11_CONSUMPTION = 'scripts/jlc-cn-pcb-v11-acceptance-consumption.json'
const V12_PRICE_LIST = 'scripts/jlc-cn-pcb-v12-candidate-price-list.json'
const V12_ACCEPTANCE = 'scripts/jlc-cn-pcb-v12-acceptance-report.json'
const V12_CONSUMPTION = 'scripts/jlc-cn-pcb-v12-acceptance-consumption.json'
const V13_PRICE_LIST = 'scripts/jlc-cn-pcb-v13-candidate-price-list.json'
const V13_ACCEPTANCE = 'scripts/jlc-cn-pcb-v13-acceptance-report.json'
const V13_CONSUMPTION = 'scripts/jlc-cn-pcb-v13-acceptance-consumption.json'
const TABLE_DATA = 'backend/apps/simplequote/table_data.py'
const FALLBACK_VERSION = 'jlc-cn-pcb-v6-20260712'
const ALLOW_UNACCEPTED = process.env.ALLOW_UNACCEPTED_PUBLISH === 'true'

function pyRow(row) {
  const materialKey = row.materialKey || row.material_key
  const materialLabel = row.materialLabel || row.material_label
  const widthMm = row.widthMm ?? row.width_mm
  const heightMm = row.heightMm ?? row.height_mm
  const jlcPrice = row.jlcPriceCny ?? row.jlc_price_cny
  const enabled = row.enabled ?? false
  return `    {"material_key": "${materialKey}", "material_label": "${materialLabel}", "layers": ${row.layers}, "width_mm": ${widthMm}, "height_mm": ${heightMm}, "quantity": ${row.quantity}, "jlc_price_cny": ${jlcPrice}, "enabled": ${enabled ? 'True' : 'False'}, "pricing_mode": "exact_lookup"},`
}

function pyLiteral(value, indent = 0) {
  if (value == null) return 'None'
  if (typeof value === 'boolean') return value ? 'True' : 'False'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string') return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map((item) => pyLiteral(item, indent + 4)).join(', ')}]`
  const entries = Object.entries(value)
  if (!entries.length) return '{}'
  const padding = ' '.repeat(indent + 4)
  const closing = ' '.repeat(indent)
  return `{\n${entries.map(([key, item]) => `${padding}${JSON.stringify(key)}: ${pyLiteral(item, indent + 4)},`).join('\n')}\n${closing}}`
}

async function readJson(path) {
  return JSON.parse(await fs.readFile(path, 'utf8'))
}

let v9Acceptance = null
let v10Acceptance = null
let v11Acceptance = null
let v12Acceptance = null
let v13Acceptance = null
try {
  v13Acceptance = await readJson(V13_ACCEPTANCE)
} catch {
  // v13 not generated yet; fall back to earlier hard gates.
}
try {
  v12Acceptance = await readJson(V12_ACCEPTANCE)
} catch {
  // v12 not generated yet; fall back to earlier hard gates.
}
try {
  v11Acceptance = await readJson(V11_ACCEPTANCE)
} catch {
  // v11 not generated yet; fall back to earlier hard gates.
}
try {
  v10Acceptance = await readJson(V10_ACCEPTANCE)
} catch {
  // v10 not generated yet; fall back to earlier hard gates.
}
try {
  v9Acceptance = await readJson(V9_ACCEPTANCE)
} catch {
  // v9 not generated yet; legacy hard gates still apply.
}
const isV13 = v13Acceptance?.status === 'passed'
const isV12 = !isV13 && v12Acceptance?.status === 'passed'
const isV11 = !isV13 && !isV12 && v11Acceptance?.status === 'passed'
const isV10 = !isV13 && !isV12 && !isV11 && v10Acceptance?.status === 'passed'
const isV9 = !isV13 && !isV12 && !isV11 && !isV10 && v9Acceptance?.status === 'passed'
const priceList = await readJson(
  isV13 ? V13_PRICE_LIST
    : (isV12 ? V12_PRICE_LIST
      : (isV11 ? V11_PRICE_LIST : (isV10 ? V10_PRICE_LIST : (isV9 ? V9_PRICE_LIST : LEGACY_PRICE_LIST)))),
)
const report = isV13 || isV12 || isV11 || isV10 || isV9
  ? {
      pass: priceList.validationStatus === 'passed',
      status: priceList.validationStatus,
      enabledMaterials: priceList.enabledMaterials,
      estimatorEnabledMaterials: priceList.estimatorEnabledMaterials,
      processEnabledMaterials: priceList.processEnabledMaterials,
      processEnabledZones: priceList.processEnabledZones,
    }
  : await readJson(LEGACY_REPORT)
const requiredMaterials = ['fr4', 'fpc', 'aluminum']
const enabledMaterials = report.enabledMaterials || priceList.enabledMaterials || []
if (report.pass !== true || report.status !== 'passed') {
  throw new Error(`refusing to publish unvalidated price list: ${report.status || 'unknown'}`)
}
if (!requiredMaterials.every((material) => enabledMaterials.includes(material))) {
  throw new Error(`refusing to publish incomplete material set: ${enabledMaterials.join(', ')}`)
}

// 发布前强制防泄漏证明（优先 v13）。
let independence = null
const independenceCandidates = [
  ...(isV13 ? ['scripts/jlc-cn-pcb-v13-assert-split-report.json'] : []),
  ...(isV12 ? ['scripts/jlc-cn-pcb-v12-assert-split-report.json'] : []),
  ...(isV11 ? ['scripts/jlc-cn-pcb-v11-assert-split-report.json'] : []),
  ...(isV10 ? ['scripts/jlc-cn-pcb-v10-assert-split-report.json'] : []),
  ...(isV9 ? ['scripts/jlc-cn-pcb-v9-assert-split-report.json'] : []),
  'scripts/jlc-cn-pcb-v8-assert-split-report.json',
  'scripts/jlc-cn-pcb-v7-assert-split-report.json',
]
for (const path of independenceCandidates) {
  try {
    independence = await readJson(path)
    if (independence?.ok) break
  } catch {
    // try next
  }
}
if (!independence?.ok) {
  throw new Error('refusing to publish without independence proof')
}

let acceptanceStatus = 'pending_live_acceptance'
let acceptanceReport = null
const acceptanceCandidates = [
  'scripts/jlc-cn-pcb-v13-acceptance-report.json',
  'scripts/jlc-cn-pcb-v12-acceptance-report.json',
  'scripts/jlc-cn-pcb-v11-acceptance-report.json',
  'scripts/jlc-cn-pcb-v10-acceptance-report.json',
  'scripts/jlc-cn-pcb-v9-acceptance-report.json',
  'scripts/jlc-cn-pcb-v8-acceptance-report.json',
  'scripts/jlc-cn-pcb-v7-acceptance-report.json',
]
for (const path of acceptanceCandidates) {
  try {
    acceptanceReport = await readJson(path)
    acceptanceStatus = acceptanceReport.status || acceptanceStatus
    break
  } catch {
    // try next
  }
}

const acceptancePassed = acceptanceStatus === 'passed'
if (!acceptancePassed && !ALLOW_UNACCEPTED) {
  throw new Error(
    `refusing to publish active version: acceptance_status=${acceptanceStatus}. `
    + `Keep ${FALLBACK_VERSION}. Set ALLOW_UNACCEPTED_PUBLISH=true only for non-active staging dumps.`,
  )
}
let v9Consumption = null
let v10Consumption = null
let v11Consumption = null
let v12Consumption = null
let v13Consumption = null
if (isV13 || isV12 || isV11 || isV10 || isV9) {
  const consumptionPath = isV13 ? V13_CONSUMPTION
    : (isV12 ? V12_CONSUMPTION
      : (isV11 ? V11_CONSUMPTION : (isV10 ? V10_CONSUMPTION : V9_CONSUMPTION)))
  const versionLabel = isV13 ? 'v13' : (isV12 ? 'v12' : (isV11 ? 'v11' : (isV10 ? 'v10' : 'v9')))
  const versionConsumption = await readJson(consumptionPath)
  if (isV13) v13Consumption = versionConsumption
  else if (isV12) v12Consumption = versionConsumption
  else if (isV11) v11Consumption = versionConsumption
  else if (isV10) v10Consumption = versionConsumption
  else v9Consumption = versionConsumption
  const fingerprint = acceptanceReport?.fingerprint?.hash
  if (
    versionConsumption.fingerprint !== fingerprint
    || versionConsumption.consumed !== true
    || versionConsumption.decision !== 'passed'
    || versionConsumption.published === true
  ) {
    throw new Error(`refusing ${versionLabel} publish: fingerprint decision missing, failed, or already published`)
  }
}

const rows = priceList.rows || []
const sampledAt = (priceList.generatedAt || report.generatedAt || new Date().toISOString()).slice(0, 10)
const versionPrefix = acceptancePassed
  ? (isV13 ? 'jlc-cn-pcb-v13'
    : (isV12 ? 'jlc-cn-pcb-v12'
      : (isV11 ? 'jlc-cn-pcb-v11' : (isV10 ? 'jlc-cn-pcb-v10' : (isV9 ? 'jlc-cn-pcb-v9' : 'jlc-cn-pcb-v8')))))
  : 'jlc-cn-pcb-staging'
const version = `${versionPrefix}-${sampledAt.replace(/-/g, '')}`
const activePriceVersion = acceptancePassed ? version : FALLBACK_VERSION
const estimator = priceList.estimator || {}
const estimatorEnabledMaterials = report.estimatorEnabledMaterials || priceList.estimatorEnabledMaterials || []
const processModel = priceList.processModel || {}
const processEnabledMaterials = report.processEnabledMaterials || priceList.processEnabledMaterials || []
const processEnabledZones = report.processEnabledZones || priceList.processEnabledZones || processModel.enabledZones || []
const riskZones = priceList.riskZones || processModel.riskZones || []
const confidenceCalibration = priceList.confidenceCalibration || processModel.confidenceCalibration || {}
const quoteRangeRate = priceList.quoteRangeRate ?? 0.20
const estimatorGuards = priceList.estimatorGuards || estimator.guards || {
  maxNeighborDistance: 0.85,
  minLocalNeighbors: 2,
}

const listBlock = [
  '# PCB 样板制造费精确查表（JLC 中文公开页 golden 采样，CNY，不含运费/税费/Gerber 附加费）。',
  '# v13：仅当三材料独立验收、BandHit(±20%) 与覆盖率门禁 passed 时原子切换；否则保持 fallback。',
  'PCB_MANUFACTURING_PRICE_LIST = [',
  ...rows.map(pyRow),
  ']',
].join('\n')

const metaBlock = `PCB_MANUFACTURING_PRICE_META = [
    ${pyLiteral({
      version,
      active_price_version: activePriceVersion,
      fallback_version: FALLBACK_VERSION,
      source: priceList.source || 'JLC CN public quote golden sampling',
      sampled_at: sampledAt,
      valid_days: 30,
      enabled_materials: enabledMaterials,
      pricing_mode: 'hybrid',
      validation_status: report.status || priceList.validationStatus || 'pending_live_resample',
      acceptance_status: acceptanceStatus,
      estimator_enabled_materials: estimatorEnabledMaterials,
      estimator,
      estimator_guards: estimatorGuards,
      process_enabled_materials: processEnabledMaterials,
      process_enabled_zones: processEnabledZones,
      process_options: Object.fromEntries(Object.entries(processModel.materials || {}).map(([materialKey, config]) => [
        materialKey,
        {
          defaults: config.defaults || {},
          options: config.options || {},
        },
      ])),
      process_model: processModel,
      risk_zones: riskZones,
      confidence_calibration: confidenceCalibration,
      quote_range_rate: quoteRangeRate,
      independence_proof: independence,
    }, 4)}
]`

const metaPayload = {
  version,
  active_price_version: activePriceVersion,
  fallback_version: FALLBACK_VERSION,
  source: priceList.source || 'JLC CN public quote golden sampling',
  sampled_at: sampledAt,
  valid_days: 30,
  enabled_materials: enabledMaterials,
  pricing_mode: 'hybrid',
  validation_status: report.status || priceList.validationStatus || 'pending_live_resample',
  acceptance_status: acceptanceStatus,
  estimator_enabled_materials: estimatorEnabledMaterials,
  estimator,
  estimator_guards: estimatorGuards,
  process_enabled_materials: processEnabledMaterials,
  process_enabled_zones: processEnabledZones,
  process_options: Object.fromEntries(Object.entries(processModel.materials || {}).map(([materialKey, config]) => [
    materialKey,
    {
      defaults: config.defaults || {},
      options: config.options || {},
    },
  ])),
  process_model: processModel,
  risk_zones: riskZones,
  confidence_calibration: confidenceCalibration,
  quote_range_rate: quoteRangeRate,
  independence_proof: independence,
}
for (const key of ['version', 'active_price_version', 'fallback_version', 'acceptance_status', 'estimator']) {
  if (metaPayload[key] == null) throw new Error(`refusing publish: incomplete meta field ${key}`)
}
const verifiedMetaBlock = `PCB_MANUFACTURING_PRICE_META = [
    ${pyLiteral(metaPayload, 4)}
]`
if (verifiedMetaBlock !== metaBlock) throw new Error('refusing publish: generated meta integrity mismatch')

let tableData = await fs.readFile(TABLE_DATA, 'utf8')
const start = tableData.indexOf('# PCB 样板制造费精确查表')
const end = tableData.indexOf('SHIPPING_PARAM_META')
if (start < 0 || end < 0) {
  throw new Error('table_data.py markers not found')
}
tableData = `${tableData.slice(0, start)}${listBlock}\n\n${metaBlock}\n\n${tableData.slice(end)}`
const tableTemp = `${TABLE_DATA}.${isV13 ? 'v13' : (isV12 ? 'v12' : (isV11 ? 'v11' : (isV10 ? 'v10' : 'v9')))}.tmp`
await fs.writeFile(tableTemp, tableData, 'utf8')
await fs.rename(tableTemp, TABLE_DATA)
if (isV13 || isV12 || isV11 || isV10 || isV9) {
  const consumptionPath = isV13 ? V13_CONSUMPTION
    : (isV12 ? V12_CONSUMPTION
      : (isV11 ? V11_CONSUMPTION : (isV10 ? V10_CONSUMPTION : V9_CONSUMPTION)))
  const versionConsumption = isV13 ? v13Consumption
    : (isV12 ? v12Consumption
      : (isV11 ? v11Consumption : (isV10 ? v10Consumption : v9Consumption)))
  const consumptionTemp = `${consumptionPath}.tmp`
  await fs.writeFile(consumptionTemp, `${JSON.stringify({
    ...versionConsumption,
    published: true,
    publishedAt: new Date().toISOString(),
    activePriceVersion,
  }, null, 2)}\n`, 'utf8')
  await fs.rename(consumptionTemp, consumptionPath)
}
console.log(JSON.stringify({
  version,
  activePriceVersion,
  fallbackVersion: FALLBACK_VERSION,
  rows: rows.length,
  enabledRows: rows.filter((row) => row.enabled).length,
  validationStatus: report.status,
  acceptanceStatus,
  published: acceptancePassed,
  estimatorEnabledMaterials,
  processEnabledMaterials,
  processEnabledZones: processEnabledZones.map((zone) => zone.id || zone),
}, null, 2))
