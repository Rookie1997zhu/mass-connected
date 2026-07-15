import fs from 'node:fs/promises'
import {
  fingerprintTargets,
  geometryKey,
  markDiagnostic,
  neighborBandKey,
  processKey,
  splitIntegrityReport,
} from './jlc-cn-pcb-v10-spec-key.mjs'

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
    samplingVersion: 'v10',
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
    samplingVersion: role === 'final_acceptance' ? 'v10-acceptance' : 'v10',
  })))
}

const quantities = [5, 10, 15, 20, 30, 50, 75, 100, 150, 200]
const materials = [
  ['fr4', (index) => (index % 2 === 0 ? 2 : 4)],
  ['fpc', (index) => (index % 2 === 0 ? 1 : 2)],
  ['aluminum', () => 1],
]

const fpcFitBase = Array.from({ length: 64 }, (_, index) => sample(
  `JLC-CN-PCB-V10-FIT-FPC-${String(index + 1).padStart(3, '0')}`,
  'fpc',
  index % 2 === 0 ? 1 : 2,
  46 + ((index % 8) * 18),
  52 + (Math.floor(index / 8) * 18),
  quantities[index % quantities.length],
))
const tuningBase = Array.from({ length: 30 }, (_, index) => sample(
  `JLC-CN-PCB-V10-TUNE-FPC-${String(index + 1).padStart(3, '0')}`,
  'fpc',
  index % 2 === 0 ? 1 : 2,
  53 + ((index % 6) * 22),
  61 + (Math.floor(index / 6) * 26),
  quantities[(index + 2) % quantities.length],
))
const processBase = materials.flatMap(([materialKey, layersFor]) => (
  Array.from({ length: 6 }, (_, index) => sample(
    `JLC-CN-PCB-V10-REG-${materialKey.toUpperCase()}-${String(index + 1).padStart(3, '0')}`,
    materialKey,
    layersFor(index),
    57 + (index * 19),
    69 + (index * 23),
    quantities[(index + 1) % quantities.length],
  ))
))
const acceptanceBase = materials.flatMap(([materialKey, layersFor]) => (
  Array.from({ length: 48 }, (_, index) => sample(
    `JLC-CN-PCB-V10-ACC-${materialKey.toUpperCase()}-${String(index + 1).padStart(3, '0')}`,
    materialKey,
    layersFor(index),
    65 + ((index % 12) * 8),
    75 + (Math.floor(index / 12) * 20),
    quantities[(index + 1) % quantities.length],
  ))
))

const historicalFit = (await readRows('scripts/jlc-cn-pcb-v9-boundary-fit-targets.json'))
  .filter((row) => Number(row.repeatIndex || 1) === 1)
  .map((row) => ({ ...row, id: row.baseSampleId || row.id.replace(/-R\d+$/, '') }))
const diagnostic = [
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v7-acceptance-targets.json'), 'v7_final_acceptance_do_not_train'),
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v8-acceptance-targets.json'), 'v8_final_acceptance_do_not_train'),
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v9-acceptance-targets.json'), 'v9_final_acceptance_do_not_train'),
  ...markDiagnostic(await readRows('scripts/jlc-cn-pcb-v10-diagnostic-v9-acceptance.json'), 'v9_final_acceptance_do_not_train'),
]
const fitForIntegrity = [...historicalFit, ...fpcFitBase]
const forbidden = [...fitForIntegrity, ...tuningBase, ...processBase, ...diagnostic]
const forbiddenNeighborBands = new Set(forbidden.map(neighborBandKey))
const forbiddenGeometry = new Set(forbidden.map(geometryKey))
const forbiddenProcess = new Set(forbidden.map(processKey))
const usedNeighborBands = new Set()
function hasLocalSupport(target) {
  const targetArea = target.widthMm * target.heightMm
  return fitForIntegrity.filter((fit) => {
    if (
      (fit.materialKey || fit.material_key) !== target.materialKey
      || Number(fit.layers) !== Number(target.layers)
    ) return false
    const fitArea = Number(fit.widthMm ?? fit.width_mm) * Number(fit.heightMm ?? fit.height_mm)
    const distance = Math.sqrt(
      Math.log(targetArea / fitArea) ** 2
      + (0.65 * Math.log(Number(target.quantity) / Number(fit.quantity))) ** 2,
    )
    return distance <= 0.75
  }).length >= 2
}
function hasRuntimeShapeSupport(target) {
  if (target.materialKey !== 'fr4') return true
  const targetArea = target.widthMm * target.heightMm
  const targetAreaSegment = targetArea <= 6000
    ? 'small'
    : (targetArea <= 16000 ? 'medium' : 'large')
  const targetQuantitySegment = target.quantity <= 20
    ? 'low'
    : (target.quantity <= 75 ? 'medium' : 'high')
  return fitForIntegrity.some((fit) => {
    const fitArea = Number(fit.widthMm ?? fit.width_mm) * Number(fit.heightMm ?? fit.height_mm)
    const fitAreaSegment = fitArea <= 6000 ? 'small' : (fitArea <= 16000 ? 'medium' : 'large')
    const fitQuantity = Number(fit.quantity)
    const fitQuantitySegment = fitQuantity <= 20 ? 'low' : (fitQuantity <= 75 ? 'medium' : 'high')
    if (
      (fit.materialKey || fit.material_key) !== 'fr4'
      || Number(fit.layers) !== Number(target.layers)
      || fitAreaSegment !== targetAreaSegment
      || fitQuantitySegment !== targetQuantitySegment
    ) return false
    const distance = Math.sqrt(
      Math.log(targetArea / fitArea) ** 2
      + (0.8 * Math.log(Number(target.quantity) / fitQuantity)) ** 2,
    )
    return distance <= 1
  })
}
for (let index = 0; index < acceptanceBase.length; index += 1) {
  const row = acceptanceBase[index]
  let isolated = false
  for (let attempt = 0; attempt < 5000; attempt += 1) {
    row.widthMm = 61 + ((index * 17 + attempt * 13) % 109)
    row.heightMm = 71 + ((index * 19 + attempt * 7) % 73)
    if (
      !forbiddenNeighborBands.has(neighborBandKey(row))
      && !forbiddenGeometry.has(geometryKey(row))
      && !forbiddenProcess.has(processKey(row))
      && !usedNeighborBands.has(neighborBandKey(row))
      && hasLocalSupport(row)
      && hasRuntimeShapeSupport(row)
    ) {
      isolated = true
      break
    }
  }
  if (!isolated) throw new Error(`cannot isolate v10 target ${row.id} inside runtime bounds`)
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
  throw new Error('v10 split integrity or support envelope failed')
}

const fingerprint = fingerprintTargets(acceptanceBase)
const frozenPath = 'scripts/jlc-cn-pcb-v10-acceptance-fingerprint.json'
try {
  const frozen = JSON.parse(await fs.readFile(frozenPath, 'utf8'))
  if (frozen.hash !== fingerprint.hash || frozen.count !== fingerprint.count) {
    throw new Error('refusing to replace existing v10 acceptance fingerprint')
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

await fs.writeFile('scripts/jlc-cn-pcb-v10-diagnostic-prior-acceptance.json', `${JSON.stringify(diagnostic, null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v10-fpc-fit-targets.json', `${JSON.stringify(repeat3(fpcFitBase, 'boundary_fit'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v10-tuning-holdout-targets.json', `${JSON.stringify(repeat3(tuningBase, 'tuning_holdout'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v10-process-holdout-targets.json', `${JSON.stringify(repeat3(processBase, 'process_holdout'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v10-acceptance-targets.json', `${JSON.stringify(repeat3(acceptanceBase, 'final_acceptance'), null, 2)}\n`)
await fs.writeFile('scripts/jlc-cn-pcb-v10-split-report.json', `${JSON.stringify({
  generatedAt: new Date().toISOString(),
  ...integrity,
  fingerprint,
}, null, 2)}\n`)
console.log(JSON.stringify({
  newFpcFit: fpcFitBase.length,
  historicalFit: historicalFit.length,
  tuning: tuningBase.length,
  processHoldout: processBase.length,
  finalAcceptance: acceptanceBase.length,
  repeatedAcceptanceRows: acceptanceBase.length * 3,
  fingerprint,
}, null, 2))
