import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  aggregateStableTriples,
  buildV9Estimator,
  scoreRows,
} from './jlc-cn-pcb-v9-model.mjs'

async function readJson(pathname, fallback = []) {
  try {
    return JSON.parse(await fs.readFile(pathname, 'utf8'))
  } catch (error) {
    if (error.code === 'ENOENT') return fallback
    throw error
  }
}

function metrics(rows, expected = rows.length) {
  const errors = rows.map((row) => row.relativeError).filter(Number.isFinite)
  if (!errors.length) {
    return {
      n: 0, coverage: 0, hitRate20: null, mape: null, maxRelativeError: null, pass: false,
    }
  }
  const hitRate20 = errors.filter((error) => error <= 0.2).length / errors.length
  const mape = errors.reduce((sum, error) => sum + error, 0) / errors.length
  const maxRelativeError = Math.max(...errors)
  return {
    n: errors.length,
    coverage: expected ? Number((errors.length / expected).toFixed(4)) : 0,
    hitRate20: Number(hitRate20.toFixed(4)),
    mape: Number(mape.toFixed(4)),
    maxRelativeError: Number(maxRelativeError.toFixed(4)),
    pass: errors.length >= 8
      && errors.length / expected >= 0.8
      && hitRate20 >= 0.95
      && maxRelativeError <= 0.2,
  }
}

function tuneMaterial(fitRows, estimator, tuningRows, materialKey) {
  const base = estimator.materials?.[materialKey]
  if (!base || !tuningRows.length) return
  const candidates = []
  if (materialKey === 'fr4') {
    for (const floorPriceCny of [0, 20, 30, 50, 80]) {
      for (const areaExponent of [0.7, 0.8, 0.9, 1, 1.1]) {
        for (const quantityExponent of [0.5, 0.6, 0.7, 0.8, 0.9, 1]) {
          for (const maxNeighborDistance of [0.4, 0.5, 0.6, 0.7]) {
            candidates.push({
              ...base,
              formula: 'floor_area_quantity',
              useSegments: false,
              floorPriceCny,
              neighbors: 6,
              guards: {
                ...base.guards,
                areaExponent,
                quantityExponent,
                maxNeighborDistance,
                minLocalNeighbors: 2,
              },
            })
          }
        }
      }
    }
  } else if (materialKey === 'fpc') {
    for (const maxNeighborDistance of [0.35, 0.4, 0.45, 0.5, 0.6, 0.75]) {
      for (const neighbors of [4, 6]) {
        for (const minLocalNeighbors of [2, 3]) {
          candidates.push({
            ...base,
            neighbors,
            guards: { ...base.guards, maxNeighborDistance, minLocalNeighbors },
          })
        }
      }
    }
  } else {
    candidates.push(base)
  }
  let best = null
  for (const config of candidates) {
    const testEstimator = {
      ...estimator,
      materials: { ...estimator.materials, [materialKey]: config },
    }
    const rows = scoreRows(fitRows, testEstimator, tuningRows)
    const result = metrics(rows, tuningRows.length)
    const rank = (result.pass ? 0 : 100)
      + (1 - result.coverage) * 10
      + Number(result.maxRelativeError ?? 10)
      + Number(result.mape ?? 10)
    if (!best || rank < best.rank) best = { rank, config, result }
  }
  if (best) {
    estimator.materials[materialKey] = {
      ...best.config,
      tuningMetrics: best.result,
    }
  }
}

function toCandidateRow(row) {
  return {
    materialKey: row.materialKey || row.material_key,
    materialLabel: row.materialLabel || row.material_label,
    layers: Number(row.layers),
    widthMm: Number(row.widthMm ?? row.width_mm),
    heightMm: Number(row.heightMm ?? row.height_mm),
    quantity: Number(row.quantity),
    jlcPriceCny: Number(row.jlcPriceCny ?? row.jlc_price_cny),
    enabled: true,
    pricingMode: 'exact_lookup',
  }
}

export async function buildV9Candidate() {
  const fitRaw = await readJson('scripts/jlc-cn-pcb-v9-boundary-fit-samples.json')
  const tuningRaw = await readJson('scripts/jlc-cn-pcb-v9-tuning-holdout-samples.json')
  const processRaw = await readJson('scripts/jlc-cn-pcb-v9-process-holdout-samples.json')
  const fit = aggregateStableTriples(fitRaw)
  const tuning = aggregateStableTriples(tuningRaw)
  const process = aggregateStableTriples(processRaw)
  const candidateRows = fit.accepted.map(toCandidateRow)
  const estimator = buildV9Estimator(candidateRows)
  for (const materialKey of ['fr4', 'fpc', 'aluminum']) {
    tuneMaterial(
      candidateRows,
      estimator,
      tuning.accepted.filter((row) => (row.materialKey || row.material_key) === materialKey),
      materialKey,
    )
  }
  const scored = scoreRows(candidateRows, estimator, tuning.accepted)
  const byMaterial = {}
  for (const materialKey of ['fr4', 'fpc', 'aluminum']) {
    const materialTuning = tuning.accepted.filter(
      (row) => (row.materialKey || row.material_key) === materialKey,
    )
    byMaterial[materialKey] = metrics(
      scored.filter((row) => row.materialKey === materialKey),
      materialTuning.length,
    )
  }
  const estimatorEnabledMaterials = Object.entries(byMaterial)
    .filter(([, result]) => result.pass)
    .map(([materialKey]) => materialKey)
  const allMaterialsPassed = estimatorEnabledMaterials.length === 3
  estimator.validationStatus = allMaterialsPassed ? 'passed' : 'pending_tuning'
  estimator.enabledMaterials = estimatorEnabledMaterials
  const guards = Object.fromEntries(
    Object.entries(estimator.materials || {}).map(([materialKey, config]) => [materialKey, config.guards]),
  )
  const candidate = {
    source: 'JLC CN v9 fresh independent fit sampling',
    generatedAt: new Date().toISOString(),
    validationStatus: allMaterialsPassed ? 'passed' : 'pending_live_sampling',
    enabledMaterials: allMaterialsPassed ? ['fr4', 'fpc', 'aluminum'] : [],
    estimatorEnabledMaterials,
    estimator,
    estimatorGuardsByMaterial: guards,
    estimatorGuards: { maxNeighborDistance: 0.65, minLocalNeighbors: 2 },
    processEnabledMaterials: [],
    processEnabledZones: [],
    processModel: {
      version: 'jlc-cn-pcb-v9-process-model',
      validationStatus: process.accepted.length ? 'pending_holdout' : 'pending_live_sampling',
      materials: {},
      enabledZones: [],
    },
    riskZones: [],
    rows: candidateRows,
    fit: { accepted: fit.accepted.length, rejected: fit.rejected },
    tuning: {
      accepted: tuning.accepted.length,
      rejected: tuning.rejected,
      byMaterial,
      rows: scored,
    },
    processHoldout: { accepted: process.accepted.length, rejected: process.rejected },
  }
  await fs.writeFile(
    'scripts/jlc-cn-pcb-v9-candidate-price-list.json',
    `${JSON.stringify(candidate, null, 2)}\n`,
    'utf8',
  )
  await fs.writeFile(
    'scripts/jlc-cn-pcb-v9-model-report.json',
    `${JSON.stringify({
      generatedAt: candidate.generatedAt,
      status: candidate.validationStatus,
      estimatorEnabledMaterials,
      fitRows: candidateRows.length,
      tuningByMaterial: byMaterial,
      rejectedFitGroups: fit.rejected,
      rejectedTuningGroups: tuning.rejected,
    }, null, 2)}\n`,
    'utf8',
  )
  return candidate
}

const isDirect = process.argv[1]
  && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))
if (isDirect) {
  const candidate = await buildV9Candidate()
  console.log(JSON.stringify({
    status: candidate.validationStatus,
    fitRows: candidate.rows.length,
    estimatorEnabledMaterials: candidate.estimatorEnabledMaterials,
  }, null, 2))
}
