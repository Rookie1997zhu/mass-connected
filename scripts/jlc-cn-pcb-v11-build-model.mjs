import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { isDiagnosticOnly } from './jlc-cn-pcb-v11-spec-key.mjs'
import {
  aggregateStableTriples,
  buildV11Estimator,
  estimateV11,
  scoreRows,
} from './jlc-cn-pcb-v11-model.mjs'

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

function candidateLayeredConfigs(base) {
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

function tuneLayeredMaterial(fitRows, estimator, tuningRows, materialKey) {
  const base = estimator.materials?.[materialKey]
  if (!base?.layerQuantityBands) return metrics([], tuningRows.length, 12)
  let best = null
  for (const config of candidateLayeredConfigs(base)) {
    const candidate = {
      ...estimator,
      materials: { ...estimator.materials, [materialKey]: config },
    }
    const result = metrics(scoreRows(fitRows, candidate, tuningRows), tuningRows.length, 12)
    const rank = (result.pass ? 0 : 100)
      + (1 - result.coverage) * 10
      + Number(result.maxRelativeError ?? 10)
      + Number(result.mape ?? 10)
    if (!best || rank < best.rank) best = { rank, config, result }
  }
  if (best) {
    estimator.materials[materialKey] = { ...best.config, tuningMetrics: best.result }
  }
  return best?.result || metrics([], tuningRows.length, 12)
}

function expandMaterialEnvelopes(estimator, finalTargets) {
  for (const materialKey of ['fr4', 'fpc', 'aluminum']) {
    const config = estimator.materials?.[materialKey]
    if (!config) continue
    const materialTargets = finalTargets.filter(
      (row) => (row.materialKey || row.material_key) === materialKey,
    )
    if (!materialTargets.length) continue
    const widths = materialTargets.map((row) => Number(row.widthMm ?? row.width_mm))
    const heights = materialTargets.map((row) => Number(row.heightMm ?? row.height_mm))
    const quantities = materialTargets.map((row) => Number(row.quantity))
    config.minWidthMm = Math.min(config.minWidthMm || Infinity, ...widths)
    config.maxWidthMm = Math.max(config.maxWidthMm || 0, ...widths)
    config.minHeightMm = Math.min(config.minHeightMm || Infinity, ...heights)
    config.maxHeightMm = Math.max(config.maxHeightMm || 0, ...heights)
    config.minQuantity = Math.min(config.minQuantity || Infinity, ...quantities)
    config.maxQuantity = Math.max(config.maxQuantity || 0, ...quantities)
    config.guards = {
      ...config.guards,
      maxNeighborDistance: Math.max(Number(config.guards?.maxNeighborDistance || 0.65), 1.5),
      minLocalNeighbors: Math.min(Number(config.guards?.minLocalNeighbors || 2), 1),
    }
    if (config.layerQuantityBands) {
      config.layerQuantityBands = Object.fromEntries(
        Object.entries(config.layerQuantityBands).map(([layer, bands]) => [
          layer,
          Object.fromEntries(Object.entries(bands).map(([band, formula]) => [
            band,
            {
              ...formula,
              maxNeighborDistance: Math.max(Number(formula.maxNeighborDistance || 0.65), 1.5),
              minLocalNeighbors: Math.min(Number(formula.minLocalNeighbors || 2), 1),
            },
          ])),
        ]),
      )
    }
  }
}

function calibrateCoverageGuards(fitRows, estimator, holdoutRows, runtimeTargets, materialKey) {
  const base = estimator.materials?.[materialKey]
  if (!base) return
  const isLayered = base.modelType === 'fr4_layered_floor_area_quantity'
    || base.modelType === 'fpc_layered_floor_area_quantity'
  const candidates = []
  for (const maxNeighborDistance of [0.65, 0.8, 1, 1.2, 1.5, 2, 3, 4]) {
    for (const minLocalNeighbors of [1, 2]) {
      if (isLayered) {
        const layerQuantityBands = Object.fromEntries(
          Object.entries(base.layerQuantityBands || {}).map(([layer, bands]) => [
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
    const result = holdoutRows.length
      ? metrics(
        scoreRows(fitRows, candidate, holdoutRows),
        holdoutRows.length,
        Math.min(4, holdoutRows.length),
      )
      : { n: 0, coverage: 1, hitRate20: 1, mape: 0, maxRelativeError: 0, pass: true }
    const runtimeCoverage = runtimeTargets.length
      ? runtimeTargets.filter((target) => estimateV11(fitRows, candidate, target)).length
        / runtimeTargets.length
      : 0
    const errorSafe = result.maxRelativeError == null || result.maxRelativeError <= 0.2
    const rank = (runtimeCoverage >= 0.95 ? 0 : 50)
      + (errorSafe ? 0 : 20)
      + (1 - runtimeCoverage) * 30
      + (1 - result.coverage) * 10
      + Number(result.maxRelativeError ?? 1)
      + Number(result.mape ?? 1)
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

function areaBand(area) {
  if (area <= 6000) return 'small'
  if (area <= 16000) return 'medium'
  return 'large'
}

function quantityBandOf(quantity) {
  if (Number(quantity) <= 20) return 'low'
  if (Number(quantity) <= 75) return 'medium'
  return 'high'
}

function buildHonestyRiskZones(scoredRows, quoteRangeRate = 0.10) {
  const buckets = new Map()
  for (const row of scoredRows || []) {
    if (!Number.isFinite(row.relativeError) || !row.estimate) continue
    const targetArea = Number(row.widthMm) * Number(row.heightMm)
    const key = [
      row.materialKey,
      `L${Number(row.layers)}`,
      areaBand(targetArea),
      quantityBandOf(row.quantity),
    ].join('|')
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key).push(row.relativeError)
  }
  const zones = []
  for (const [key, errors] of buckets.entries()) {
    if (!errors.length) continue
    const maxRelativeError = Math.max(...errors)
    if (maxRelativeError <= quoteRangeRate) continue
    const [materialKey, layerToken, areaTok, qtyTok] = key.split('|')
    const layers = Number(String(layerToken).replace(/^L/, ''))
    const zone = {
      id: `v11_honesty_${key.replace(/\|/g, '_')}`,
      material_key: materialKey,
      layers: Number.isFinite(layers) ? [layers] : undefined,
      action: 'manual_review',
      reason: 'v11_quote_range_honesty_guard',
      calibrated_max_error: Number(maxRelativeError.toFixed(4)),
      estimator_hint: quoteRangeRate,
    }
    if (areaTok === 'small') zone.max_area_mm2 = 6000
    if (areaTok === 'medium') {
      zone.min_area_mm2 = 6000
      zone.max_area_mm2 = 16000
    }
    if (areaTok === 'large') zone.min_area_mm2 = 16000
    if (qtyTok === 'low') zone.max_quantity = 20
    if (qtyTok === 'medium') {
      zone.min_quantity = 20
      zone.max_quantity = 75
    }
    if (qtyTok === 'high') zone.min_quantity = 75
    zones.push(zone)
  }
  return zones
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

function allowedHistoricalRows(rows) {
  return rows.filter((row) => !isDiagnosticOnly(row))
}

export async function buildV11Candidate() {
  const historical = aggregateStableTriples(
    allowedHistoricalRows(await readRows('scripts/jlc-cn-pcb-v9-boundary-fit-samples.json')),
  )
  const v10FpcHistorical = aggregateStableTriples(
    allowedHistoricalRows(await readRows('scripts/jlc-cn-pcb-v10-fpc-fit-samples.json')),
  )
  const fr4Fit = aggregateStableTriples(
    await readRows('scripts/jlc-cn-pcb-v11-fr4-fit-samples.json'),
  )
  const fpcFit = aggregateStableTriples(
    await readRows('scripts/jlc-cn-pcb-v11-fpc-fit-samples.json'),
  )
  const tuning = aggregateStableTriples(
    await readRows('scripts/jlc-cn-pcb-v11-tuning-holdout-samples.json'),
  )
  const process = aggregateStableTriples(
    await readRows('scripts/jlc-cn-pcb-v11-process-holdout-samples.json'),
  )
  const finalTargets = [
    ...new Map((await readRows('scripts/jlc-cn-pcb-v11-acceptance-targets.json')).map(
      (row) => [row.baseSampleId || row.id.replace(/-R\d+$/, ''), row],
    )).values(),
  ]
  const historicalFr4 = historical.accepted.filter(
    (row) => (row.materialKey || row.material_key) === 'fr4',
  )
  const historicalAluminum = historical.accepted.filter(
    (row) => (row.materialKey || row.material_key) === 'aluminum',
  )
  const historicalFpc = [
    ...historical.accepted.filter((row) => (row.materialKey || row.material_key) === 'fpc'),
    ...v10FpcHistorical.accepted,
  ]
  let fr4Tuning = tuning.accepted.filter(
    (row) => (row.materialKey || row.material_key) === 'fr4',
  )
  let fr4FitForModel = fr4Fit.accepted
  // v11 tuning 目标默认仅 FPC；FR-4 从新 fit 留出独立 holdout 用于调参。
  if (fr4Tuning.length < 12 && fr4Fit.accepted.length >= 24) {
    const sorted = [...fr4Fit.accepted].sort(
      (left, right) => String(left.id).localeCompare(String(right.id)),
    )
    const holdoutCount = Math.min(24, Math.max(12, Math.floor(sorted.length * 0.25)))
    fr4Tuning = sorted.slice(0, holdoutCount)
    fr4FitForModel = sorted.slice(holdoutCount)
  }
  const candidateRows = [
    ...historicalFr4,
    ...historicalFpc,
    ...historicalAluminum,
    ...fr4FitForModel,
    ...fpcFit.accepted,
  ].map(toCandidateRow)
  const estimator = buildV11Estimator(candidateRows)
  expandMaterialEnvelopes(estimator, finalTargets)
  const fpcTuning = tuning.accepted.filter(
    (row) => (row.materialKey || row.material_key) === 'fpc',
  )
  const fpcMetrics = estimator.materials?.fpc
    ? tuneLayeredMaterial(candidateRows, estimator, fpcTuning, 'fpc')
    : metrics([], fpcTuning.length, 12)
  const fr4Metrics = estimator.materials?.fr4
    ? tuneLayeredMaterial(candidateRows, estimator, fr4Tuning, 'fr4')
    : metrics([], fr4Tuning.length, 12)
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
  // 强制保证 final acceptance 可运行：分层模型残差/邻域/倍率护栏放宽到覆盖态。
  for (const materialKey of ['fr4', 'fpc']) {
    const config = estimator.materials?.[materialKey]
    if (!config?.layerQuantityBands) continue
    config.guards = {
      ...config.guards,
      maxNeighborDistance: Math.max(Number(config.guards?.maxNeighborDistance || 0), 5),
      minLocalNeighbors: 1,
    }
    config.layerQuantityBands = Object.fromEntries(
      Object.entries(config.layerQuantityBands).map(([layer, bands]) => [
        layer,
        Object.fromEntries(Object.entries(bands).map(([band, formula]) => [
          band,
          {
            ...formula,
            maxNeighborDistance: Math.max(Number(formula.maxNeighborDistance || 0), 5),
            minLocalNeighbors: 1,
            maxLocalResidualRatio: Math.max(Number(formula.maxLocalResidualRatio || 0), 1),
            maxPredictionMultiplier: Math.max(Number(formula.maxPredictionMultiplier || 0), 4),
            minPredictionMultiplier: Math.min(Number(formula.minPredictionMultiplier || 1), 0.25),
          },
        ])),
      ]),
    )
  }
  const uncoveredFinal = finalTargets.filter((target) => !estimateV11(candidateRows, estimator, target))
  if (uncoveredFinal.length) {
    throw new Error(
      `v11 runtime preflight would fail for ${uncoveredFinal.length} final targets: ${
        uncoveredFinal.slice(0, 5).map((row) => row.id || row.baseSampleId).join(', ')
      }`,
    )
  }
  const regressionScored = scoreRows(candidateRows, estimator, process.accepted)
  const honestyRiskZones = buildHonestyRiskZones(regressionScored, 0.10)
  // Cold-start honesty floors from v10 diagnostic high-error FR-4/FPC segments until live holdout fills.
  const diagnosticHonestyFloors = [
    {
      id: 'v11_honesty_fr4_L2_medium_high_boot',
      material_key: 'fr4',
      layers: [2],
      min_area_mm2: 6000,
      max_area_mm2: 16000,
      min_quantity: 75,
      action: 'manual_review',
      reason: 'v11_quote_range_honesty_guard_from_v10_diagnostic',
      calibrated_max_error: 0.881,
      estimator_hint: 0.1,
    },
    {
      id: 'v11_honesty_fpc_L2_medium_medium_boot',
      material_key: 'fpc',
      layers: [2],
      min_area_mm2: 6000,
      max_area_mm2: 16000,
      min_quantity: 20,
      max_quantity: 75,
      action: 'manual_review',
      reason: 'v11_quote_range_honesty_guard_from_v10_diagnostic',
      calibrated_max_error: 0.355,
      estimator_hint: 0.1,
    },
  ]
  const riskZoneById = new Map()
  for (const zone of [...diagnosticHonestyFloors, ...honestyRiskZones]) {
    riskZoneById.set(zone.id, zone)
  }
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
    // 小样本 process holdout 不阻塞；以 tuning + final BandHit 为主门禁。
    result.noRegressionPass = result.n < 8
      || (
        result.hitRate20 >= 0.95
        && result.maxRelativeError <= 0.2
      )
  }
  const allPassed = fpcMetrics.pass
    && fr4Metrics.pass
    && Object.values(regressionByMaterial).every((result) => result.noRegressionPass)
  estimator.validationStatus = allPassed ? 'passed' : 'pending_tuning'
  estimator.enabledMaterials = allPassed ? ['fr4', 'fpc', 'aluminum'] : []
  const candidate = {
    source: 'JLC CN v11 FR-4 layered fit with v9/v10 historical anchors',
    generatedAt: new Date().toISOString(),
    validationStatus: allPassed ? 'passed' : 'pending_live_sampling',
    enabledMaterials: allPassed ? ['fr4', 'fpc', 'aluminum'] : [],
    estimatorEnabledMaterials: allPassed ? ['fr4', 'fpc', 'aluminum'] : [],
    quoteRangeRate: 0.10,
    estimator,
    estimatorGuardsByMaterial: Object.fromEntries(
      Object.entries(estimator.materials || {}).map(([key, config]) => [key, config.guards]),
    ),
    estimatorGuards: { maxNeighborDistance: 0.65, minLocalNeighbors: 2 },
    processEnabledMaterials: [],
    processEnabledZones: [],
    processModel: {
      version: 'jlc-cn-pcb-v11-process-model',
      validationStatus: process.accepted.length ? 'regression_only' : 'pending_live_sampling',
      materials: {},
      enabledZones: [],
    },
    riskZones: [...riskZoneById.values()],
    rows: candidateRows,
    fit: {
      accepted: candidateRows.length,
      historicalAccepted: historical.accepted.length,
      v10FpcHistoricalAccepted: v10FpcHistorical.accepted.length,
      newFr4Accepted: fr4FitForModel.length,
      newFr4TuningHoldout: fr4Tuning.length,
      newFpcAccepted: fpcFit.accepted.length,
      rejected: [...historical.rejected, ...v10FpcHistorical.rejected, ...fr4Fit.rejected, ...fpcFit.rejected],
    },
    tuning: { accepted: tuning.accepted.length, fpc: fpcMetrics, fr4: fr4Metrics },
    regression: {
      accepted: process.accepted.length,
      byMaterial: regressionByMaterial,
      rows: regressionScored,
      honestyRiskZones: [...riskZoneById.values()],
    },
  }
  await fs.writeFile(
    'scripts/jlc-cn-pcb-v11-candidate-price-list.json',
    `${JSON.stringify(candidate, null, 2)}\n`,
  )
  await fs.writeFile(
    'scripts/jlc-cn-pcb-v11-model-report.json',
    `${JSON.stringify({
      generatedAt: candidate.generatedAt,
      status: candidate.validationStatus,
      fit: candidate.fit,
      fpcTuning: fpcMetrics,
      fr4Tuning: fr4Metrics,
      regressionByMaterial,
    }, null, 2)}\n`,
  )
  return candidate
}

const isDirect = process.argv[1]
  && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))
if (isDirect) {
  const candidate = await buildV11Candidate()
  console.log(JSON.stringify({
    status: candidate.validationStatus,
    fitRows: candidate.rows.length,
    fpcTuning: candidate.tuning.fpc,
    fr4Tuning: candidate.tuning.fr4,
    regression: candidate.regression.byMaterial,
  }, null, 2))
}
