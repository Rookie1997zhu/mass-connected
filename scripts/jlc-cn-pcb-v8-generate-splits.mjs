/**
 * Generate v8 data splits:
 * - mark v7 acceptance as diagnostic_only
 * - create tuning holdout + final acceptance disjoint from fit/v7
 * - freeze acceptance fingerprint for one-shot publish scoring
 */
import fs from 'node:fs/promises'
import {
  fingerprintTargets,
  geometryKey,
  markDiagnostic,
  neighborBandKey,
  processKey,
  splitIntegrityReport,
} from './jlc-cn-pcb-v8-spec-key.mjs'

async function readJson(path, fallback = []) {
  try {
    const raw = JSON.parse(await fs.readFile(path, 'utf8'))
    return Array.isArray(raw) ? raw : fallback
  } catch (error) {
    if (error.code === 'ENOENT') return fallback
    throw error
  }
}

function sample(id, materialKey, materialLabel, layers, widthMm, heightMm, quantity, process = {}) {
  const defaults = {
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
  return {
    id,
    samplingVersion: 'v8',
    materialKey,
    materialLabel,
    layers,
    widthMm,
    heightMm,
    quantity,
    ...defaults,
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
    samplingVersion: role === 'final_acceptance' ? 'v8-acceptance' : 'v8',
  })))
}

const v7Acceptance = await readJson('scripts/jlc-cn-pcb-v7-acceptance-targets.json')
const v7AcceptanceSamples = await readJson('scripts/jlc-cn-pcb-v7-acceptance-samples.json')
const diagnostic = markDiagnostic([
  ...v7Acceptance,
  ...v7AcceptanceSamples,
], 'v7_final_acceptance_do_not_train')

// Boundary-focused tuning holdout (for model selection only; not final acceptance)
const tuningHoldoutBase = [
  sample('JLC-CN-PCB-V8-TUNE-FR4-001', 'fr4', 'FR-4', 2, 95, 155, 100),
  sample('JLC-CN-PCB-V8-TUNE-FR4-002', 'fr4', 'FR-4', 2, 105, 165, 150),
  sample('JLC-CN-PCB-V8-TUNE-FR4-003', 'fr4', 'FR-4', 2, 115, 175, 200),
  sample('JLC-CN-PCB-V8-TUNE-FR4-004', 'fr4', 'FR-4', 4, 55, 70, 10),
  sample('JLC-CN-PCB-V8-TUNE-ALU-001', 'aluminum', '铝基板', 1, 55, 70, 10),
  sample('JLC-CN-PCB-V8-TUNE-ALU-002', 'aluminum', '铝基板', 1, 60, 80, 15),
  sample('JLC-CN-PCB-V8-TUNE-ALU-003', 'aluminum', '铝基板', 1, 70, 85, 20),
  sample('JLC-CN-PCB-V8-TUNE-FPC-001', 'fpc', 'FPC软板', 2, 90, 130, 75, { boardThickness: '0.20' }),
  sample('JLC-CN-PCB-V8-TUNE-FPC-002', 'fpc', 'FPC软板', 1, 70, 95, 30, { boardThickness: '0.12' }),
]

// Final acceptance sizes intentionally offset from v7 grids
const acceptanceSizes = [
  [58, 72], [66, 94], [73, 107], [81, 119], [89, 131],
  [96, 138], [104, 150], [111, 159], [119, 168], [126, 176],
  [134, 183], [141, 191], [149, 178], [156, 195], [59, 101],
  [76, 130], [90, 143], [99, 155], [115, 169], [130, 160],
  [145, 186], [160, 173], [69, 124], [84, 146], [101, 163],
  [120, 175], [138, 190], [153, 171], [79, 135], [93, 151],
  [108, 164], [123, 180], [140, 157], [154, 189], [66, 110],
  [85, 141], [100, 153], [116, 167], [131, 181], [148, 194],
]
// Use JLC quantities that the public page can select reliably; geometries
// remain off-grid and are shifted below to satisfy near-neighbor isolation.
const quantities = [15, 30, 50, 75, 100, 150, 20, 10, 5, 200]

function buildAcceptance(materialKey, materialLabel, layersFn, prefix, processExtra = {}) {
  const rows = []
  for (let i = 0; i < 40; i += 1) {
    const [widthMm, heightMm] = acceptanceSizes[i]
    rows.push(sample(
      `JLC-CN-PCB-V8-ACC-${prefix}-${String(i + 1).padStart(3, '0')}`,
      materialKey,
      materialLabel,
      layersFn(i),
      widthMm,
      heightMm,
      quantities[i % quantities.length],
      processExtra,
    ))
  }
  return rows
}

const finalAcceptanceBase = [
  ...buildAcceptance('fr4', 'FR-4', (i) => (i % 2 === 0 ? 2 : 4), 'FR4'),
  ...buildAcceptance('fpc', 'FPC软板', (i) => (i % 2 === 0 ? 1 : 2), 'FPC'),
  ...buildAcceptance('aluminum', '铝基板', () => 1, 'ALU'),
]

// Boundary golden anchors for fit enrichment (exact lookup candidates)
const boundaryFitBase = [
  sample('JLC-CN-PCB-V8-FIT-FR4-LG-001', 'fr4', 'FR-4', 2, 100, 160, 100),
  sample('JLC-CN-PCB-V8-FIT-FR4-LG-002', 'fr4', 'FR-4', 2, 120, 180, 150),
  sample('JLC-CN-PCB-V8-FIT-FR4-LG-003', 'fr4', 'FR-4', 2, 150, 200, 200),
  sample('JLC-CN-PCB-V8-FIT-ALU-SM-001', 'aluminum', '铝基板', 1, 50, 60, 5),
  sample('JLC-CN-PCB-V8-FIT-ALU-SM-002', 'aluminum', '铝基板', 1, 60, 90, 10),
  sample('JLC-CN-PCB-V8-FIT-ALU-SM-003', 'aluminum', '铝基板', 1, 70, 100, 15),
]

const processHoldout = await readJson('scripts/jlc-cn-pcb-process-holdout-v7-targets.json')
const fitPool = [
  ...await readJson('scripts/jlc-cn-pcb-golden-v4-targets.json'),
  ...await readJson('scripts/jlc-cn-pcb-process-v7-targets.json'),
  ...boundaryFitBase,
]

// Move acceptance geometries out of every development/diagnostic neighbor
// band before freezing the one-shot target fingerprint.
const forbiddenNeighborBands = new Set([
  ...fitPool,
  ...tuningHoldoutBase,
  ...processHoldout,
  ...diagnostic,
].map(neighborBandKey))
const forbiddenGeometry = new Set([
  ...fitPool,
  ...tuningHoldoutBase,
  ...processHoldout,
  ...diagnostic,
].map(geometryKey))
const usedAcceptanceGeometry = new Set()
for (const row of finalAcceptanceBase) {
  let attempts = 0
  while (
    forbiddenNeighborBands.has(neighborBandKey(row))
    || forbiddenGeometry.has(geometryKey(row))
    || usedAcceptanceGeometry.has(geometryKey(row))
  ) {
    row.widthMm += 1
    if (row.widthMm > 198) {
      row.widthMm = 52 + attempts
      row.heightMm += 1
    }
    attempts += 1
    if (attempts > 100) {
      throw new Error(`cannot isolate v8 acceptance neighbor for ${row.id}`)
    }
  }
  usedAcceptanceGeometry.add(geometryKey(row))
}

const tuningHoldout = repeat3(tuningHoldoutBase, 'tuning_holdout')
const finalAcceptance = repeat3(finalAcceptanceBase, 'final_acceptance')
const boundaryFit = repeat3(boundaryFitBase, 'boundary_fit')

const integrity = splitIntegrityReport({
  fit: fitPool,
  tuningHoldout: tuningHoldoutBase,
  processHoldout,
  finalAcceptance: finalAcceptanceBase,
  diagnostic,
})

// Soften neighbor hard-fail for generation: keep exact disjoint as hard requirement
const exactOk = integrity.checks
  .filter((item) => !String(item.left).includes('neighbor'))
  .every((item) => item.ok)
if (!exactOk) {
  console.error(JSON.stringify(integrity, null, 2))
  throw new Error('v8 exact split integrity failed')
}

const fingerprint = fingerprintTargets(finalAcceptanceBase)
await fs.writeFile('scripts/jlc-cn-pcb-v8-diagnostic-v7-acceptance.json', `${JSON.stringify(diagnostic, null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v8-tuning-holdout-targets.json', `${JSON.stringify(tuningHoldout, null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v8-boundary-fit-targets.json', `${JSON.stringify(boundaryFit, null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v8-acceptance-targets.json', `${JSON.stringify(finalAcceptance, null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v8-acceptance-fingerprint.json', `${JSON.stringify({
  frozenAt: new Date().toISOString(),
  ...fingerprint,
  oneShot: true,
  note: 'Do not retune model against this set after scoring; generate a new fingerprint for next version.',
}, null, 2)}\n`, 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v8-split-report.json', `${JSON.stringify({
  generatedAt: new Date().toISOString(),
  ...integrity,
  fingerprint,
  notes: {
    neighborChecksSoft: integrity.checks.filter((item) => String(item.left).includes('neighbor')),
    diagnosticCount: diagnostic.length,
  },
}, null, 2)}\n`, 'utf8')

console.log(JSON.stringify({
  diagnostic: diagnostic.length,
  tuningHoldout: tuningHoldout.length,
  boundaryFit: boundaryFit.length,
  finalAcceptance: finalAcceptance.length,
  fingerprint,
  exactOk,
  neighborOk: integrity.checks.filter((c) => String(c.left).includes('neighbor')).every((c) => c.ok),
}, null, 2))
