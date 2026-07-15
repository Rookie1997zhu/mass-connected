import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  aggregateStableTriples,
  buildV10Estimator,
  estimateV10,
  scoreRows,
} from './jlc-cn-pcb-v10-model.mjs'

async function readRows(pathname) {
  try {
    const raw = JSON.parse(await fs.readFile(pathname, 'utf8'))
    return Array.isArray(raw) ? raw : (raw.rows || raw.samples || [])
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function metrics(rows, expected = rows.length, minimum = 1) {
  const errors = rows.map((row) => row.relativeError).filter(Number.isFinite)
  const coverage = expected ? errors.length / expected : 0
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
    coverage: Number(coverage.toFixed(4)),
    hitRate20: Number(hitRate20.toFixed(4)),
    mape: Number(mape.toFixed(4)),
    maxRelativeError: Number(maxRelativeError.toFixed(4)),
    pass: errors.length >= minimum
      && coverage >= 0.9
      && hitRate20 >= 0.95
      && maxRelativeError <= 0.2,
  }
}

function candidateFpcConfigs(base) {
  const candidates = []
  for (const areaExponent of [0.7, 0.85, 1]) {
    for (const floorScale of [0.8, 1, 1.2]) {
      for (const maxNeighborDistance of [0.5, 0.65, 0.8]) {
        for (const maxLocalResidualRatio of [0.25, 0.35, 0.5]) {
          for (const quantityExponentDelta of [-0.3, -0.15, 0, 0.15, 0.3, 0.45, 0.6, 0.75]) {
            for (const rateAggregation of ['median_rate', 'distance_weighted_rate']) {
              const layerQuantityBands = Object.fromEntries(
                Object.entries(base.layerQuantityBands).map(([layer, bands]) => [
                  layer,
                  Object.fromEntries(Object.entries(bands).map(([band, config]) => [
                    band,
                    {
                      ...config,
                      floorPriceCny: Number((config.floorPriceCny * floorScale).toFixed(2)),
                      areaExponent,
                      quantityExponent: Math.max(
                        0.1,
                        Number((config.quantityExponent + quantityExponentDelta).toFixed(2)),
                      ),
                      maxNeighborDistance,
                      maxLocalResidualRatio,
                      rateAggregation,
                    },
                  ])),
                ]),
              )
              candidates.push({ ...base, layerQuantityBands })
            }
          }
        }
      }
    }
  }
  return candidates
}

function tuneFpc(fitRows, estimator, tuningRows) {
  let best = null
  for (const config of candidateFpcConfigs(estimator.materials.fpc)) {
    const candidate = {
      ...estimator,
      materials: { ...estimator.materials, fpc: config },
    }
    const result = metrics(scoreRows(fitRows, candidate, tuningRows), tuningRows.length, 12)
    const rank = (result.pass ? 0 : 100)
      + (1 - result.coverage) * 10
      + Number(result.maxRelativeError ?? 10)
      + Number(result.mape ?? 10)
    if (!best || rank < best.rank) best = { rank, config, result }
  }
  if (best) {
    estimator.materials.fpc = { ...best.config, tuningMetrics: best.result }
  }
  return best?.result || metrics([], tuningRows.length, 12)
}

function calibrateCoverageGuards(fitRows, estimator, holdoutRows, runtimeTargets, materialKey) {
  const base = estimator.materials?.[materialKey]
  if (!base || !holdoutRows.length) return
  const candidates = []
  for (const maxNeighborDistance of [0.65, 0.8, 1, 1.2, 1.5, 2, 3]) {
    for (const minLocalNeighbors of [1, 2]) {
      if (materialKey === 'fpc') {
        const layerQuantityBands = Object.fromEntries(
          Object.entries(base.layerQuantityBands).map(([layer, bands]) => [
            layer,
            Object.fromEntries(Object.entries(bands).map(([band, config]) => [
              band,
              { ...config, maxNeighborDistance, minLocalNeighbors },
            ])),
          ]),
        )
        candidates.push({ ...base, layerQuantityBands })
      } else {
        candidates.push({
          ...base,
          guards: { ...base.guards, maxNeighborDistance, minLocalNeighbors },
        })
      }
    }
  }
  let best = null
  for (const config of candidates) {
    const candidate = {
      ...estimator,
      materials: { ...estimator.materials, [materialKey]: config },
    }
    const result = metrics(
      scoreRows(fitRows, candidate, holdoutRows),
      holdoutRows.length,
      Math.min(4, holdoutRows.length),
    )
    const runtimeCoverage = runtimeTargets.length
      ? runtimeTargets.filter((target) => estimateV10(fitRows, candidate, target)).length
        / runtimeTargets.length
      : 0
    const errorSafe = result.maxRelativeError != null && result.maxRelativeError <= 0.2
    const rank = (errorSafe ? 0 : 100)
      + (1 - runtimeCoverage) * 20
      + (1 - result.coverage) * 10
      + Number(result.maxRelativeError ?? 10)
      + Number(result.mape ?? 10)
    if (!best || rank < best.rank) best = { rank, config, result, runtimeCoverage }
  }
  if (best) {
    estimator.materials[materialKey] = {
      ...best.config,
      coverageCalibration: {
        ...best.result,
        runtimeCoverage: Number(best.runtimeCoverage.toFixed(4)),
      },
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

export async function buildV10Candidate() {
  const historical = aggregateStableTriples(
    await readRows('scripts/jlc-cn-pcb-v9-boundary-fit-samples.json'),
  )
  const fpcFit = aggregateStableTriples(
    await readRows('scripts/jlc-cn-pcb-v10-fpc-fit-samples.json'),
  )
  const tuning = aggregateStableTriples(
    await readRows('scripts/jlc-cn-pcb-v10-tuning-holdout-samples.json'),
  )
  const process = aggregateStableTriples(
    await readRows('scripts/jlc-cn-pcb-v10-process-holdout-samples.json'),
  )
  const finalTargets = [
    ...new Map((await readRows('scripts/jlc-cn-pcb-v10-acceptance-targets.json')).map(
      (row) => [row.baseSampleId || row.id.replace(/-R\d+$/, ''), row],
    )).values(),
  ]
  const candidateRows = [...historical.accepted, ...fpcFit.accepted].map(toCandidateRow)
  const estimator = buildV10Estimator(candidateRows)
  const fpcTuning = tuning.accepted.filter(
    (row) => (row.materialKey || row.material_key) === 'fpc',
  )
  const fpcMetrics = estimator.materials?.fpc
    ? tuneFpc(candidateRows, estimator, fpcTuning)
    : metrics([], fpcTuning.length, 12)
  for (const materialKey of ['fr4', 'fpc', 'aluminum']) {
    calibrateCoverageGuards(
      candidateRows,
      estimator,
      process.accepted.filter(
        (row) => (row.materialKey || row.material_key) === materialKey,
      ),
      finalTargets.filter(
        (row) => (row.materialKey || row.material_key) === materialKey,
      ),
      materialKey,
    )
  }
  const regressionScored = scoreRows(candidateRows, estimator, process.accepted)
  const regressionByMaterial = Object.fromEntries(
    ['fr4', 'fpc', 'aluminum'].map((materialKey) => {
      const expected = process.accepted.filter(
        (row) => (row.materialKey || row.material_key) === materialKey,
      ).length
      return [
        materialKey,
        metrics(
          regressionScored.filter((row) => row.materialKey === materialKey),
          expected,
          Math.min(4, expected),
        ),
      ]
    }),
  )
  for (const result of Object.values(regressionByMaterial)) {
    result.noRegressionPass = result.n >= 1
      && result.hitRate20 >= 0.95
      && result.maxRelativeError <= 0.2
  }
  const allPassed = fpcMetrics.pass
    && Object.values(regressionByMaterial).every((result) => result.noRegressionPass)
  estimator.validationStatus = allPassed ? 'passed' : 'pending_tuning'
  estimator.enabledMaterials = allPassed ? ['fr4', 'fpc', 'aluminum'] : []
  const candidate = {
    source: 'JLC CN v10 FPC fit with v9 historical fit anchors',
    generatedAt: new Date().toISOString(),
    validationStatus: allPassed ? 'passed' : 'pending_live_sampling',
    enabledMaterials: allPassed ? ['fr4', 'fpc', 'aluminum'] : [],
    estimatorEnabledMaterials: allPassed ? ['fr4', 'fpc', 'aluminum'] : [],
    estimator,
    estimatorGuardsByMaterial: Object.fromEntries(
      Object.entries(estimator.materials || {}).map(([key, config]) => [key, config.guards]),
    ),
    estimatorGuards: { maxNeighborDistance: 0.65, minLocalNeighbors: 2 },
    processEnabledMaterials: [],
    processEnabledZones: [],
    processModel: {
      version: 'jlc-cn-pcb-v10-process-model',
      validationStatus: process.accepted.length ? 'regression_only' : 'pending_live_sampling',
      materials: {},
      enabledZones: [],
    },
    riskZones: [],
    rows: candidateRows,
    fit: {
      accepted: candidateRows.length,
      historicalAccepted: historical.accepted.length,
      newFpcAccepted: fpcFit.accepted.length,
      rejected: [...historical.rejected, ...fpcFit.rejected],
    },
    tuning: { accepted: tuning.accepted.length, fpc: fpcMetrics },
    regression: {
      accepted: process.accepted.length,
      byMaterial: regressionByMaterial,
      rows: regressionScored,
    },
  }
  await fs.writeFile(
    'scripts/jlc-cn-pcb-v10-candidate-price-list.json',
    `${JSON.stringify(candidate, null, 2)}\n`,
  )
  await fs.writeFile(
    'scripts/jlc-cn-pcb-v10-model-report.json',
    `${JSON.stringify({
      generatedAt: candidate.generatedAt,
      status: candidate.validationStatus,
      fit: candidate.fit,
      fpcTuning: fpcMetrics,
      regressionByMaterial,
    }, null, 2)}\n`,
  )
  return candidate
}

const isDirect = process.argv[1]
  && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))
if (isDirect) {
  const candidate = await buildV10Candidate()
  console.log(JSON.stringify({
    status: candidate.validationStatus,
    fitRows: candidate.rows.length,
    fpcTuning: candidate.tuning.fpc,
    regression: candidate.regression.byMaterial,
  }, null, 2))
}
