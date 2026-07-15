/**
 * Generate v9 development and one-shot acceptance splits.
 * Prior v7/v8 acceptance data is diagnostic-only and never enters fit/tuning.
 */
import fs from 'node:fs/promises'
import {
  fingerprintTargets,
  geometryKey,
  markDiagnostic,
  neighborBandKey,
  processKey,
  splitIntegrityReport,
} from './jlc-cn-pcb-v9-spec-key.mjs'

async function readJson(path, fallback = []) {
  try {
    const raw = JSON.parse(await fs.readFile(path, 'utf8'))
    return Array.isArray(raw) ? raw : fallback
  } catch (error) {
    if (error.code === 'ENOENT') return fallback
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
    samplingVersion: 'v9',
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
    samplingVersion: role === 'final_acceptance' ? 'v9-acceptance' : 'v9',
  })))
}

const quantities = [5, 10, 15, 20, 30, 50, 75, 100, 150, 200]
const materials = [
  ['fr4', (index) => (index % 2 === 0 ? 2 : 4)],
  ['fpc', (index) => (index % 2 === 0 ? 1 : 2)],
  ['aluminum', () => 1],
]

function buildFit(materialKey, layersFor) {
  return Array.from({ length: 48 }, (_, index) => sample(
    `JLC-CN-PCB-V9-FIT-${materialKey.toUpperCase()}-${String(index + 1).padStart(3, '0')}`,
    materialKey,
    layersFor(index),
    60 + ((index % 12) * 10),
    70 + (Math.floor(index / 12) * 25),
    quantities[index % quantities.length],
  ))
}

function buildTuning(materialKey, layersFor) {
  return Array.from({ length: 12 }, (_, index) => sample(
    `JLC-CN-PCB-V9-TUNE-${materialKey.toUpperCase()}-${String(index + 1).padStart(3, '0')}`,
    materialKey,
    layersFor(index),
    67 + ((index % 6) * 20),
    82 + (Math.floor(index / 6) * 45),
    quantities[(index + 3) % quantities.length],
  ))
}

function buildProcessHoldout() {
  return [
    sample('JLC-CN-PCB-V9-PROC-FR4-001', 'fr4', 2, 83, 113, 30, { surfaceFinish: '沉金' }),
    sample('JLC-CN-PCB-V9-PROC-FR4-002', 'fr4', 4, 107, 137, 75, { copperThickness: '2oz' }),
    sample('JLC-CN-PCB-V9-PROC-FPC-001', 'fpc', 1, 91, 121, 20, { boardThickness: '0.12' }),
    sample('JLC-CN-PCB-V9-PROC-FPC-002', 'fpc', 2, 117, 147, 50, { boardThickness: '0.20' }),
    sample('JLC-CN-PCB-V9-PROC-ALU-001', 'aluminum', 1, 89, 129, 15, { boardThickness: '2.0' }),
    sample('JLC-CN-PCB-V9-PROC-ALU-002', 'aluminum', 1, 139, 169, 100, { solderColor: '白色' }),
  ]
}

const fitBase = materials.flatMap(([materialKey, layersFor]) => buildFit(materialKey, layersFor))
const tuningBase = materials.flatMap(([materialKey, layersFor]) => buildTuning(materialKey, layersFor))
const processBase = buildProcessHoldout()
const acceptanceBase = materials.flatMap(([materialKey, layersFor]) => (
  Array.from({ length: 48 }, (_, index) => sample(
    `JLC-CN-PCB-V9-ACC-${materialKey.toUpperCase()}-${String(index + 1).padStart(3, '0')}`,
    materialKey,
    layersFor(index),
    63 + ((index % 12) * 10),
    74 + (Math.floor(index / 12) * 25),
    quantities[index % quantities.length],
  ))
))

const diagnostic = [
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v7-acceptance-targets.json'), 'v7_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v7-acceptance-samples.json'), 'v7_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v8-acceptance-targets.json'), 'v8_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v8-acceptance-samples.json'), 'v8_final_acceptance_do_not_train'),
]

const forbidden = [...fitBase, ...tuningBase, ...processBase, ...diagnostic]
const forbiddenNeighborBands = new Set(forbidden.map(neighborBandKey))
const forbiddenGeometry = new Set(forbidden.map(geometryKey))
const forbiddenProcess = new Set(forbidden.map(processKey))
const usedNeighborBands = new Set()
for (const row of acceptanceBase) {
  let attempts = 0
  while (
    forbiddenNeighborBands.has(neighborBandKey(row))
    || forbiddenGeometry.has(geometryKey(row))
    || forbiddenProcess.has(processKey(row))
    || usedNeighborBands.has(neighborBandKey(row))
  ) {
    row.widthMm += 2
    attempts += 1
    if (attempts > 80) throw new Error(`cannot isolate v9 acceptance target ${row.id}`)
  }
  usedNeighborBands.add(neighborBandKey(row))
}

const integrity = splitIntegrityReport({
  fit: fitBase,
  tuningHoldout: tuningBase,
  processHoldout: processBase,
  finalAcceptance: acceptanceBase,
  diagnostic,
})
if (!integrity.ok) {
  console.error(JSON.stringify(integrity, null, 2))
  throw new Error('v9 split integrity or support envelope failed')
}

const fingerprint = fingerprintTargets(acceptanceBase)
const frozenPath = 'scripts/jlc-cn-pcb-v9-acceptance-fingerprint.json'
try {
  const frozen = JSON.parse(await fs.readFile(frozenPath, 'utf8'))
  if (frozen.hash !== fingerprint.hash || frozen.count !== fingerprint.count) {
    throw new Error('refusing to replace an existing v9 acceptance fingerprint')
  }
} catch (error) {
  if (error.code !== 'ENOENT') throw error
  await fs.writeFile(frozenPath, `${JSON.stringify({
    frozenAt: new Date().toISOString(),
    ...fingerprint,
    oneShot: true,
    consumed: false,
  }, null, 2)}\n`, 'utf8')
}

await fs.writeFile('scripts/jlc-cn-pcb-v9-diagnostic-prior-acceptance.json', `${JSON.stringify(diagnostic, null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v9-boundary-fit-targets.json', `${JSON.stringify(repeat3(fitBase, 'boundary_fit'), null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v9-tuning-holdout-targets.json', `${JSON.stringify(repeat3(tuningBase, 'tuning_holdout'), null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v9-process-holdout-targets.json', `${JSON.stringify(repeat3(processBase, 'process_holdout'), null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v9-acceptance-targets.json', `${JSON.stringify(repeat3(acceptanceBase, 'final_acceptance'), null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v9-split-report.json', `${JSON.stringify({
  generatedAt: new Date().toISOString(),
  ...integrity,
  fingerprint,
}, null, 2)}\n`, 'utf8')

console.log(JSON.stringify({
  diagnostic: diagnostic.length,
  fit: fitBase.length,
  tuningHoldout: tuningBase.length,
  processHoldout: processBase.length,
  finalAcceptance: acceptanceBase.length,
  repeatedAcceptanceRows: acceptanceBase.length * 3,
  fingerprint,
  supportEnvelopeOk: integrity.supportEnvelope.ok,
}, null, 2))
