import fs from 'node:fs/promises'
import {
  fingerprintTargets,
  geometryKey,
  markDiagnostic,
  neighborBandKey,
  processKey,
  splitIntegrityReport,
} from './jlc-cn-pcb-v13-spec-key.mjs'

async function readRows(pathname) {
  try {
    const raw = JSON.parse(await fs.readFile(pathname, 'utf8'))
    return Array.isArray(raw) ? raw : (raw.rows || raw.samples || [])
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function defaults(materialKey) {
  return {
    fr4: {
      boardThickness: '1.6', solderColor: '绿色', surfaceFinish: '有铅喷锡',
      copperThickness: '1oz', solderMaskCoverage: '过孔盖油', panelDesignCount: '1',
    },
    fpc: {
      boardThickness: '0.11', solderColor: '页面默认', surfaceFinish: '沉金',
      copperThickness: '1oz', solderMaskCoverage: '页面默认', panelDesignCount: '1',
    },
    aluminum: {
      boardThickness: '1.6', solderColor: '绿色', surfaceFinish: '无铅喷锡',
      copperThickness: '1oz', solderMaskCoverage: '页面默认', panelDesignCount: '1',
    },
  }[materialKey]
}

function sample(id, materialKey, layers, widthMm, heightMm, quantity, process = {}) {
  return {
    id,
    samplingVersion: 'v13',
    materialKey,
    materialLabel: { fr4: 'FR-4', fpc: 'FPC软板', aluminum: '铝基板' }[materialKey],
    layers,
    widthMm,
    heightMm,
    quantity,
    ...defaults(materialKey),
    ...process,
  }
}

function repeat3(rows, role) {
  return rows.flatMap((row) => [1, 2, 3].map((repeatIndex) => ({
    ...row,
    id: `${row.id}-R${repeatIndex}`,
    baseSampleId: row.id,
    repeatIndex,
    sampleRole: role,
    samplingVersion: role === 'final_acceptance' ? 'v13-acceptance' : 'v13',
  })))
}

/**
 * V13 quantity whitelist — inherit V12 stable tiers; drop aluminum@50/200 which
 * still intermittently failed during V12 resume ("quantity option not found").
 */
const SAFE_QUANTITIES = {
  fr4: [5, 10, 15, 20, 30, 100, 150, 200],
  fpc: [5, 10, 15, 20, 50, 100],
  aluminum: [5, 10, 15, 20, 30, 150],
}
function quantitiesFor(materialKey) {
  return SAFE_QUANTITIES[materialKey] || SAFE_QUANTITIES.fr4
}
const materials = [
  ['fr4', (index) => (index % 2 === 0 ? 2 : 4)],
  ['fpc', (index) => (index % 2 === 0 ? 1 : 2)],
  ['aluminum', () => 1],
]

const mediumAreaSizes = [
  [80, 80], [90, 90], [100, 80], [110, 90], [100, 100], [120, 90],
  [90, 110], [100, 120], [110, 110], [120, 100], [130, 100], [110, 130],
]
const largeAreaSizes = [
  [140, 130], [150, 120], [160, 120], [150, 150], [180, 110], [200, 100],
  [170, 130], [160, 140], [190, 110], [180, 120], [150, 160], [200, 110],
]
const fr4FitBase = Array.from({ length: 96 }, (_, index) => {
  const areaPool = index % 2 === 0 ? mediumAreaSizes : largeAreaSizes
  const [widthMm, heightMm] = areaPool[index % areaPool.length]
  const fr4Qtys = quantitiesFor('fr4')
  return sample(
    `JLC-CN-PCB-V13-FIT-FR4-${String(index + 1).padStart(3, '0')}`,
    'fr4',
    index % 2 === 0 ? 2 : 4,
    widthMm + (index % 6),
    heightMm + (Math.floor(index / 12) % 5),
    fr4Qtys[index % fr4Qtys.length],
  )
})
const fpcFitBase = Array.from({ length: 64 }, (_, index) => {
  const fpcQtys = quantitiesFor('fpc')
  return sample(
    `JLC-CN-PCB-V13-FIT-FPC-${String(index + 1).padStart(3, '0')}`,
    'fpc',
    index % 2 === 0 ? 1 : 2,
    48 + ((index % 8) * 18),
    54 + (Math.floor(index / 8) * 18),
    fpcQtys[index % fpcQtys.length],
  )
})
const tuningBase = Array.from({ length: 30 }, (_, index) => {
  const fpcQtys = quantitiesFor('fpc')
  return sample(
    `JLC-CN-PCB-V13-TUNE-FPC-${String(index + 1).padStart(3, '0')}`,
    'fpc',
    index % 2 === 0 ? 1 : 2,
    55 + ((index % 6) * 22),
    63 + (Math.floor(index / 6) * 26),
    fpcQtys[(index + 2) % fpcQtys.length],
  )
})
const processBase = materials.flatMap(([materialKey, layersFor]) => (
  Array.from({ length: 6 }, (_, index) => {
    const qtys = quantitiesFor(materialKey)
    return sample(
      `JLC-CN-PCB-V13-REG-${materialKey.toUpperCase()}-${String(index + 1).padStart(3, '0')}`,
      materialKey,
      layersFor(index),
      59 + (index * 19),
      71 + (index * 23),
      qtys[(index + 1) % qtys.length],
    )
  })
))
// Extra aluminum fit under SAFE qty — historical aluminum alone is too sparse in q1–q4 bands.
const aluminumFitBase = Array.from({ length: 64 }, (_, index) => {
  const areaPool = index % 2 === 0 ? mediumAreaSizes : largeAreaSizes
  const [widthMm, heightMm] = areaPool[index % areaPool.length]
  const aluQtys = quantitiesFor('aluminum')
  return sample(
    `JLC-CN-PCB-V13-FIT-ALUMINUM-${String(index + 1).padStart(3, '0')}`,
    'aluminum',
    1,
    widthMm + ((index * 3) % 7),
    heightMm + ((index * 5) % 6),
    aluQtys[index % aluQtys.length],
  )
})
// Acceptance geometry offset vs V12 ACC to avoid geometry-key collisions.
const acceptanceBase = materials.flatMap(([materialKey, layersFor]) => (
  Array.from({ length: 48 }, (_, index) => {
    const qtys = quantitiesFor(materialKey)
    return sample(
      `JLC-CN-PCB-V13-ACC-${materialKey.toUpperCase()}-${String(index + 1).padStart(3, '0')}`,
      materialKey,
      layersFor(index),
      78 + ((index % 12) * 9),
      88 + (Math.floor(index / 12) * 22),
      qtys[(index + 3) % qtys.length],
    )
  })
))

const historicalFit = (await readRows('scripts/jlc-cn-pcb-v9-boundary-fit-targets.json'))
  .filter((row) => Number(row.repeatIndex || 1) === 1)
  .map((row) => ({ ...row, id: row.baseSampleId || row.id.replace(/-R\d+$/, '') }))
const diagnostic = [
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v7-acceptance-targets.json'), 'v7_final_acceptance_do_not_train'),
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v8-acceptance-targets.json'), 'v8_final_acceptance_do_not_train'),
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v9-acceptance-targets.json'), 'v9_final_acceptance_do_not_train'),
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v10-diagnostic-v9-acceptance.json'), 'v9_final_acceptance_do_not_train'),
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v10-acceptance-targets.json'), 'v10_final_acceptance_do_not_train'),
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v11-acceptance-targets.json'), 'v11_final_acceptance_do_not_train'),
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v12-acceptance-targets.json'), 'v12_final_acceptance_do_not_train'),
]
const fitForIntegrity = [...historicalFit, ...fr4FitBase, ...fpcFitBase, ...aluminumFitBase]
const forbidden = [...fitForIntegrity, ...tuningBase, ...processBase, ...diagnostic]
const forbiddenNeighborBands = new Set(forbidden.map(neighborBandKey))
const forbiddenGeometry = new Set(forbidden.map(geometryKey))
const forbiddenProcess = new Set(forbidden.map(processKey))
const usedNeighborBands = new Set()
function areaSegment(area) {
  if (area <= 6000) return 'small'
  if (area <= 16000) return 'medium'
  return 'large'
}
function quantitySegment(quantity) {
  if (quantity <= 20) return 'low'
  if (quantity <= 75) return 'medium'
  return 'high'
}
function hasRuntimeShapeSupport(target) {
  const targetArea = target.widthMm * target.heightMm
  const targetAreaSegment = areaSegment(targetArea)
  const targetQuantitySegment = quantitySegment(target.quantity)
  if (target.materialKey !== 'fr4') return true
  return fitForIntegrity.some((fit) => {
    const fitArea = Number(fit.widthMm ?? fit.width_mm) * Number(fit.heightMm ?? fit.height_mm)
    if (
      (fit.materialKey || fit.material_key) !== 'fr4'
      || Number(fit.layers) !== Number(target.layers)
      || areaSegment(fitArea) !== targetAreaSegment
      || quantitySegment(Number(fit.quantity)) !== targetQuantitySegment
    ) return false
    const distance = Math.sqrt(
      Math.log(targetArea / fitArea) ** 2
      + (0.8 * Math.log(Number(target.quantity) / Number(fit.quantity))) ** 2,
    )
    return distance <= 1.25
  })
}
function fitSupportDistance(target, fit) {
  const targetArea = target.widthMm * target.heightMm
  const fitArea = Number(fit.widthMm ?? fit.width_mm) * Number(fit.heightMm ?? fit.height_mm)
  return Math.sqrt(
    Math.log(targetArea / fitArea) ** 2
    + (0.65 * Math.log(Number(target.quantity) / Number(fit.quantity))) ** 2,
  )
}
function supportNeighborCount(row, maxDistance = 0.75) {
  return fitForIntegrity.filter((fit) => (
    (fit.materialKey || fit.material_key) === row.materialKey
    && Number(fit.layers) === Number(row.layers)
    && fitSupportDistance(row, fit) <= maxDistance
  )).length
}
function candidateIsValid(row) {
  return (
    supportNeighborCount(row) >= 2
    && hasRuntimeShapeSupport(row)
    && !forbiddenNeighborBands.has(neighborBandKey(row))
    && !forbiddenGeometry.has(geometryKey(row))
    && !forbiddenProcess.has(processKey(row))
    && !usedNeighborBands.has(neighborBandKey(row))
  )
}
function isolateAcceptanceTarget(row, index) {
  // Prefer medium/high within whitelist for BandHit coverage; fall back to full SAFE pool.
  const materialQtys = quantitiesFor(row.materialKey)
  const preferredQuantities = materialQtys.filter((qty) => quantitySegment(qty) !== 'low')
  const pools = [
    preferredQuantities.length ? preferredQuantities : materialQtys,
    materialQtys,
  ]
  for (const quantityPool of pools) {
    if (!quantityPool.length) continue
    for (let attempt = 0; attempt < 40000; attempt += 1) {
      const quantity = quantityPool[(index + attempt) % quantityPool.length]
      row.quantity = quantity
      // Offset area search vs V11 isolate formula to reduce neighbor-band collisions.
      const areaBucket = 9 + ((index * 13 + attempt * 7) % 52)
      const areaTarget = (areaBucket * 1000) + 480
      const aspect = 0.72 + ((index + attempt) % 13) * 0.04
      row.heightMm = Math.max(45, Math.round(Math.sqrt(areaTarget / aspect)))
      row.widthMm = Math.max(45, Math.round(areaTarget / row.heightMm))
      if (candidateIsValid(row)) return true
      row.widthMm = 64 + ((index * 17 + attempt * 13) % 109)
      row.heightMm = 74 + ((index * 19 + attempt * 7) % 73)
      if (candidateIsValid(row)) return true
      row.widthMm = 48 + ((index * 23 + attempt * 11) % 140)
      row.heightMm = 52 + ((index * 29 + attempt * 9) % 120)
      if (candidateIsValid(row)) return true
    }
  }
  return false
}
for (let index = 0; index < acceptanceBase.length; index += 1) {
  const row = acceptanceBase[index]
  if (!isolateAcceptanceTarget(row, index)) {
    throw new Error(`cannot isolate v13 target ${row.id} inside runtime bounds`)
  }
  usedNeighborBands.add(neighborBandKey(row))
}

const integrity = splitIntegrityReport({
  fit: fitForIntegrity,
  tuningHoldout: tuningBase,
  processHoldout: processBase,
  finalAcceptance: acceptanceBase,
  diagnostic,
})
if (!integrity.ok) {
  console.error(JSON.stringify(integrity, null, 2))
  throw new Error('v13 split integrity or support envelope failed')
}

const fingerprint = fingerprintTargets(acceptanceBase)
const frozenPath = 'scripts/jlc-cn-pcb-v13-acceptance-fingerprint.json'
try {
  const frozen = JSON.parse(await fs.readFile(frozenPath, 'utf8'))
  if (frozen.hash !== fingerprint.hash || frozen.count !== fingerprint.count) {
    throw new Error('refusing to replace existing v13 acceptance fingerprint')
  }
} catch (error) {
  if (error.code !== 'ENOENT') throw error
  await fs.writeFile(frozenPath, `${JSON.stringify({
    frozenAt: new Date().toISOString(),
    ...fingerprint,
    oneShot: true,
    consumed: false,
  }, null, 2)}\n`)
}

await fs.writeFile('scripts/jlc-cn-pcb-v13-diagnostic-prior-acceptance.json', `${JSON.stringify(diagnostic, null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v13-fr4-fit-targets.json', `${JSON.stringify(repeat3(fr4FitBase, 'boundary_fit'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v13-fpc-fit-targets.json', `${JSON.stringify(repeat3(fpcFitBase, 'boundary_fit'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v13-aluminum-fit-targets.json', `${JSON.stringify(repeat3(aluminumFitBase, 'boundary_fit'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v13-tuning-holdout-targets.json', `${JSON.stringify(repeat3(tuningBase, 'tuning_holdout'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v13-process-holdout-targets.json', `${JSON.stringify(repeat3(processBase, 'process_holdout'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v13-acceptance-targets.json', `${JSON.stringify(repeat3(acceptanceBase, 'final_acceptance'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v13-split-report.json', `${JSON.stringify({
  generatedAt: new Date().toISOString(),
  ...integrity,
  fingerprint,
  safeQuantities: SAFE_QUANTITIES,
}, null, 2)}\n`)
console.log(JSON.stringify({
  newFr4Fit: fr4FitBase.length,
  newFpcFit: fpcFitBase.length,
  newAluminumFit: aluminumFitBase.length,
  historicalFit: historicalFit.length,
  tuning: tuningBase.length,
  processHoldout: processBase.length,
  finalAcceptance: acceptanceBase.length,
  repeatedAcceptanceRows: acceptanceBase.length * 3,
  diagnosticRows: diagnostic.length,
  safeQuantities: SAFE_QUANTITIES,
  fingerprint,
}, null, 2))
