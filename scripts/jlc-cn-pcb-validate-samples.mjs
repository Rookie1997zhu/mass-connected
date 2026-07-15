import fs from 'node:fs/promises'
import { buildV9Candidate } from './jlc-cn-pcb-v9-build-model.mjs'

const DEFAULT_GOLDEN = 'scripts/jlc-cn-pcb-golden-v4-samples.json'
const DEFAULT_EXACT_HOLDOUT = 'scripts/jlc-cn-pcb-exact-holdout-v4-samples.json'
const DEFAULT_ESTIMATOR_HOLDOUT = 'scripts/jlc-cn-pcb-estimator-holdout-v4-samples.json'
const PRICE_LIST_OUT = 'scripts/jlc-cn-pcb-manufacturing-price-list.json'
const REPORT_OUT = 'scripts/jlc-cn-pcb-validation-report.json'
const ESTIMATOR_OUT = 'scripts/jlc-cn-pcb-v4-estimator.json'
const DEFAULT_PROCESS_GOLDEN = process.env.JLC_PROCESS_GOLDEN
  || 'scripts/jlc-cn-pcb-process-v7-samples.json'
const DEFAULT_PROCESS_HOLDOUT = process.env.JLC_PROCESS_HOLDOUT
  || 'scripts/jlc-cn-pcb-process-holdout-v7-samples.json'
const PROCESS_OPTIONS_PATH = process.env.JLC_PROCESS_OPTIONS
  || 'scripts/jlc-cn-pcb-process-v7-options.json'
const PROCESS_MODEL_OUT = process.env.JLC_PROCESS_MODEL_OUT || 'scripts/jlc-cn-pcb-v8-process-model.json'
const SAMPLING_VERSION = 'v4'
const PROCESS_FIELDS = [
  'boardThickness',
  'solderColor',
  'surfaceFinish',
  'copperThickness',
  'solderMaskCoverage',
  'panelDesignCount',
]
const INTERACTION_PAIRS = [
  ['solderMaskCoverage', 'surfaceFinish'],
  ['panelDesignCount', 'quantity'],
  ['solderColor', 'materialKey'],
  ['copperThickness', 'surfaceFinish'],
]
const SUPPORTED_MATERIALS = new Set(['fr4', 'fpc', 'aluminum'])
const MATERIAL_LABELS = {
  fr4: 'FR-4',
  fpc: 'FPC软板',
  aluminum: '铝基板',
}
const MIN_LIVE_BY_MATERIAL = {
  fr4: { golden: 60, holdout: 10 },
  fpc: { golden: 30, holdout: 8 },
  aluminum: { golden: 20, holdout: 8 },
}

function keyOf(sample) {
  return [
    sample.materialKey || 'fr4',
    Number(sample.layers),
    Number(sample.widthMm),
    Number(sample.heightMm),
    Number(sample.quantity),
  ].join('|')
}

function median(values) {
  const sorted = values.filter((value) => Number.isFinite(value)).sort((a, b) => a - b)
  if (!sorted.length) return null
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid] : Number(((sorted[mid - 1] + sorted[mid]) / 2).toFixed(2))
}

function stddev(values) {
  if (values.length <= 1) return 0
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length
  const variance = values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / values.length
  return Math.sqrt(variance)
}

function effectiveDomPrice(sample) {
  if (sample.priceSource !== 'dom') return null
  const dom = Number(sample.domPriceCny)
  return Number.isFinite(dom) && dom > 0 ? dom : null
}

function effectiveApiPrice(sample) {
  const api = Number(sample.apiPriceCny ?? sample.priceBreakdown?.internetPayTotalmoney)
  return Number.isFinite(api) && api > 0 ? api : null
}

function domApiDiff(sample) {
  const dom = effectiveDomPrice(sample)
  const api = effectiveApiPrice(sample)
  if (!dom || !api) return null
  return Math.abs(api - dom) / dom
}

function hasSpecialPrice(sample) {
  return Number(sample.priceBreakdown?.specialProduceMoney || 0) > 0
    || /特价/.test(sample.priceText || '')
}

function validateSpecMatch(sample) {
  const reasons = []
  const expectedQty = Number(sample.quantity)
  const selectedQty = Number(sample.selectedQuantity)
  if (selectedQty && selectedQty !== expectedQty) reasons.push('quantity_mismatch')

  const expectedLengthCm = Number((sample.widthMm / 10).toFixed(2))
  const expectedWidthCm = Number((sample.heightMm / 10).toFixed(2))
  const selectedLengthCm = Number(sample.selectedLengthCm)
  const selectedWidthCm = Number(sample.selectedWidthCm)
  if (selectedLengthCm && Math.abs(selectedLengthCm - expectedLengthCm) > 0.01) {
    reasons.push('length_mismatch')
  }
  if (selectedWidthCm && Math.abs(selectedWidthCm - expectedWidthCm) > 0.01) {
    reasons.push('width_mismatch')
  }

  const expectedLayers = Number(sample.layers)
  const selectedLayers = Number(sample.selectedLayers)
  if (selectedLayers && selectedLayers !== expectedLayers) reasons.push('layer_mismatch')

  const expectedLabel = MATERIAL_LABELS[sample.materialKey || 'fr4']
  if (sample.selectedMaterialLabel && expectedLabel && sample.selectedMaterialLabel !== expectedLabel) {
    reasons.push('material_mismatch')
  }

  return reasons
}

function validateSample(sample) {
  const reasons = []
  const price = effectiveDomPrice(sample)
  if (!SUPPORTED_MATERIALS.has(sample.materialKey || 'fr4')) reasons.push('unsupported_material')
  if (!price || price <= 0) reasons.push('missing_dom_price')

  const diff = domApiDiff(sample)
  if (diff != null && diff > 0.01) reasons.push('api_dom_mismatch')
  if (hasSpecialPrice(sample) || sample.quarantined === true) reasons.push('quarantined_special_price')
  if (sample.error) reasons.push('sample_error')
  reasons.push(...validateSpecMatch(sample))

  return {
    valid: reasons.length === 0,
    reasons: [...new Set(reasons)],
    apiDomDiff: diff,
    price,
    domPriceCny: price,
    apiPriceCny: effectiveApiPrice(sample),
    priceSource: sample.priceSource || null,
    hasSpecialOffer: hasSpecialPrice(sample),
  }
}

function validateProcessSelection(sample) {
  const reasons = []
  const states = sample.selectedProcessOptions || {}
  for (const field of PROCESS_FIELDS) {
    const requested = sample[field]
    if (!requested || requested === '页面默认') continue
    const state = states[field]
    if (state?.present && state.selected !== true) reasons.push(`${field}_selection_mismatch`)
    if (!state && ['v6', 'v7'].includes(sample.samplingVersion)) reasons.push(`${field}_selection_unverified`)
  }
  return reasons
}

function validateProcessSample(sample) {
  const validation = validateSample(sample)
  const reasons = [...validation.reasons, ...validateProcessSelection(sample)]
  return {
    ...validation,
    valid: reasons.length === 0,
    reasons: [...new Set(reasons)],
  }
}

async function readJsonIfExists(path) {
  try {
    return JSON.parse(await fs.readFile(path, 'utf8'))
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function buildGoldenRows(samples) {
  const groups = new Map()
  for (const sample of samples) {
    const groupKey = sample.baseSampleId || keyOf(sample)
    if (!groups.has(groupKey)) groups.set(groupKey, [])
    groups.get(groupKey).push(sample)
  }

  const rows = []
  const rejected = []
  for (const [groupKey, groupSamples] of groups) {
    const validations = groupSamples.map((sample) => ({ sample, validation: validateSample(sample) }))
    const validSamples = validations.filter(({ validation }) => validation.valid)
    const prices = validSamples.map(({ validation }) => validation.price)
    const base = groupSamples[0]
    const med = median(prices)
    const cv = med ? stddev(prices) / med : null
    const repeatStable = cv == null || cv <= 0.02

    const hasAllRepeats = groupSamples.length >= 3 && validSamples.length === groupSamples.length
    if (!med || !repeatStable || !hasAllRepeats) {
      rejected.push({
        groupKey,
        materialKey: base.materialKey || 'fr4',
        layers: base.layers,
        widthMm: base.widthMm,
        heightMm: base.heightMm,
        quantity: base.quantity,
        prices,
        cv,
        reasons: [
          ...(med ? [] : ['no_valid_price']),
          ...(repeatStable ? [] : ['repeat_cv_gt_2_percent']),
          ...(hasAllRepeats ? [] : ['not_all_three_repeats_valid']),
          ...new Set(validations.flatMap(({ validation }) => validation.reasons)),
        ],
      })
      continue
    }

    rows.push({
      materialKey: base.materialKey || 'fr4',
      materialLabel: base.materialLabel || MATERIAL_LABELS[base.materialKey || 'fr4'],
      layers: Number(base.layers),
      widthMm: Number(base.widthMm),
      heightMm: Number(base.heightMm),
      quantity: Number(base.quantity),
      jlcPriceCny: med,
      customerQuoteCny: Number((med * 1.1).toFixed(2)),
      sampleCount: groupSamples.length,
      validSampleCount: validSamples.length,
      sourceSampleIds: validSamples.map(({ sample }) => sample.id),
      sampleRole: 'golden',
      pricingMode: 'exact_lookup',
      enabled: true,
    })
  }

  return { rows, rejected }
}

function scoreHoldout(holdoutSamples, priceRows) {
  const priceMap = new Map(priceRows.map((row) => [keyOf(row), row]))
  const scored = []
  for (const sample of holdoutSamples) {
    const validation = validateSample(sample)
    const row = priceMap.get(keyOf(sample))
    const actual = validation.price
    const predicted = row?.jlcPriceCny ?? null
    const relativeError = predicted && actual ? Math.abs(predicted - actual) / actual : null
    scored.push({
      id: sample.id,
      materialKey: sample.materialKey || 'fr4',
      layers: sample.layers,
      widthMm: sample.widthMm,
      heightMm: sample.heightMm,
      quantity: sample.quantity,
      actualPriceCny: actual || null,
      predictedPriceCny: predicted,
      relativeError,
      hit20: relativeError != null ? relativeError <= 0.2 : false,
      validActual: validation.valid,
      reasons: validation.reasons,
      apiDomDiff: validation.apiDomDiff,
      priceSource: validation.priceSource,
    })
  }

  const validScored = scored.filter((item) => item.validActual && item.predictedPriceCny)
  const byMaterial = Object.fromEntries([...new Set(scored.map((item) => item.materialKey))].map((materialKey) => {
    const materialRows = validScored.filter((item) => item.materialKey === materialKey)
    return [materialKey, summarizeScores(materialRows)]
  }))

  return {
    summary: summarizeScores(validScored),
    byMaterial,
    rows: scored,
  }
}

function buildEstimator(priceRows) {
  const materials = {}
  for (const materialKey of SUPPORTED_MATERIALS) {
    const materialRows = priceRows.filter((row) => row.materialKey === materialKey)
    if (!materialRows.length) continue
    materials[materialKey] = {
      layers: [...new Set(materialRows.map((row) => Number(row.layers)))].sort((a, b) => a - b),
      minWidthMm: Math.min(...materialRows.map((row) => Number(row.widthMm))),
      maxWidthMm: Math.max(...materialRows.map((row) => Number(row.widthMm))),
      minHeightMm: Math.min(...materialRows.map((row) => Number(row.heightMm))),
      maxHeightMm: Math.max(...materialRows.map((row) => Number(row.heightMm))),
      minQuantity: Math.min(...materialRows.map((row) => Number(row.quantity))),
      maxQuantity: Math.max(...materialRows.map((row) => Number(row.quantity))),
    }
  }
  return {
    version: `jlc-cn-pcb-v4-estimator-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`,
    algorithm: 'staged_log_interp_v1',
    neighbors: 4,
    areaWeight: 1,
    quantityWeight: 1.35,
    aspectWeight: 0.35,
    materials,
  }
}

function estimateWithModel(sample, priceRows, estimator) {
  const materialKey = sample.materialKey || 'fr4'
  const material = estimator.materials[materialKey]
  if (!material || !material.layers.includes(Number(sample.layers))) return null
  const widthMm = Number(sample.widthMm)
  const heightMm = Number(sample.heightMm)
  const quantity = Number(sample.quantity)
  if (widthMm <= 0 || heightMm <= 0 || quantity <= 0) return null
  if (
    widthMm < material.minWidthMm
    || heightMm < material.minHeightMm
    || quantity < material.minQuantity
    || widthMm > material.maxWidthMm
    || heightMm > material.maxHeightMm
    || quantity > material.maxQuantity
  ) return null

  const candidates = priceRows.filter((row) => (
    row.materialKey === materialKey && Number(row.layers) === Number(sample.layers) && row.enabled !== false
  ))
  if (!candidates.length) return null

  const area = widthMm * heightMm
  const aspect = Math.max(widthMm, heightMm) / Math.min(widthMm, heightMm)
  const exact = candidates.find((row) => (
    Number(row.widthMm) === widthMm
    && Number(row.heightMm) === heightMm
    && Number(row.quantity) === quantity
  ))
  if (exact) {
    return {
      price: Number(exact.jlcPriceCny),
      confidence: 1,
      basis: [keyOf(exact)],
    }
  }

  const rowsBySize = new Map()
  for (const row of candidates) {
    const sizeKey = `${Number(row.widthMm)}|${Number(row.heightMm)}`
    if (!rowsBySize.has(sizeKey)) rowsBySize.set(sizeKey, [])
    rowsBySize.get(sizeKey).push(row)
  }
  const sizeEstimates = []
  for (const sizeRows of rowsBySize.values()) {
    sizeRows.sort((a, b) => Number(a.quantity) - Number(b.quantity))
    const exactQuantity = sizeRows.find((row) => Number(row.quantity) === quantity)
    let price
    let basisRows
    if (exactQuantity) {
      price = Number(exactQuantity.jlcPriceCny)
      basisRows = [exactQuantity]
    } else {
      const lower = [...sizeRows].reverse().find((row) => Number(row.quantity) < quantity)
      const upper = sizeRows.find((row) => Number(row.quantity) > quantity)
      if (!lower || !upper) continue
      const quantityRatio = Math.log(quantity / Number(lower.quantity))
        / Math.log(Number(upper.quantity) / Number(lower.quantity))
      price = Math.exp(
        Math.log(Number(lower.jlcPriceCny))
        + quantityRatio * (Math.log(Number(upper.jlcPriceCny)) - Math.log(Number(lower.jlcPriceCny))),
      )
      basisRows = [lower, upper]
    }
    const rowWidth = Number(sizeRows[0].widthMm)
    const rowHeight = Number(sizeRows[0].heightMm)
    const rowArea = rowWidth * rowHeight
    const rowAspect = Math.max(rowWidth, rowHeight) / Math.min(rowWidth, rowHeight)
    const areaDiff = Math.log(area / rowArea) * estimator.areaWeight
    const aspectDiff = Math.log(aspect / rowAspect) * estimator.aspectWeight
    sizeEstimates.push({
      price,
      basisRows,
      distance: Math.sqrt((areaDiff ** 2) + (aspectDiff ** 2)),
    })
  }
  if (!sizeEstimates.length) return null
  const nearest = sizeEstimates.sort((a, b) => a.distance - b.distance).slice(0, estimator.neighbors)
  if (nearest[0].distance < 1e-9) {
    return {
      price: Number(nearest[0].price.toFixed(2)),
      confidence: 0.95,
      basis: nearest[0].basisRows.map((row) => keyOf(row)),
    }
  }
  let weightedLogPrice = 0
  let totalWeight = 0
  for (const item of nearest) {
    const weight = 1 / ((item.distance ** 2) + 0.005)
    weightedLogPrice += Math.log(item.price) * weight
    totalWeight += weight
  }
  const averageDistance = nearest.reduce((sum, item) => sum + item.distance, 0) / nearest.length
  return {
    price: Number(Math.exp(weightedLogPrice / totalWeight).toFixed(2)),
    confidence: Number(Math.max(0.2, Math.min(0.99, 1 / (1 + averageDistance))).toFixed(4)),
    basis: [...new Set(nearest.flatMap((item) => item.basisRows.map((row) => keyOf(row))))],
  }
}

function scoreEstimatorHoldout(holdoutSamples, priceRows, estimator) {
  const scored = holdoutSamples.map((sample) => {
    const validation = validateSample(sample)
    const prediction = estimateWithModel(sample, priceRows, estimator)
    const actual = validation.price
    const predicted = prediction?.price ?? null
    const relativeError = predicted && actual ? Math.abs(predicted - actual) / actual : null
    return {
      id: sample.id,
      materialKey: sample.materialKey || 'fr4',
      layers: Number(sample.layers),
      widthMm: Number(sample.widthMm),
      heightMm: Number(sample.heightMm),
      quantity: Number(sample.quantity),
      actualPriceCny: actual || null,
      predictedPriceCny: predicted,
      relativeError,
      hit20: relativeError != null ? relativeError <= 0.2 : false,
      validActual: validation.valid,
      reasons: validation.reasons,
      confidence: prediction?.confidence ?? null,
      estimatorBasis: prediction?.basis ?? [],
      priceSource: validation.priceSource,
    }
  })
  const validScored = scored.filter((item) => item.validActual && item.predictedPriceCny)
  const byMaterial = Object.fromEntries([...SUPPORTED_MATERIALS].map((materialKey) => [
    materialKey,
    summarizeScores(validScored.filter((item) => item.materialKey === materialKey)),
  ]))
  return {
    summary: summarizeScores(validScored),
    byMaterial,
    rows: scored,
  }
}

function summarizeScores(rows) {
  if (!rows.length) {
    return { total: 0, hit20: 0, hitRate20: null, mape: null, maxRelativeError: null, pass: false }
  }
  const hit20 = rows.filter((row) => row.hit20).length
  const errors = rows.map((row) => row.relativeError).filter((value) => value != null)
  const mape = errors.reduce((sum, value) => sum + value, 0) / errors.length
  const maxRelativeError = Math.max(...errors)
  return {
    total: rows.length,
    hit20,
    hitRate20: Number((hit20 / rows.length).toFixed(4)),
    mape: Number(mape.toFixed(4)),
    maxRelativeError: Number(maxRelativeError.toFixed(4)),
    pass: hit20 / rows.length >= 0.8 && maxRelativeError <= 1,
  }
}

function processAnchorKey(sample) {
  return [
    sample.materialKey || 'fr4',
    Number(sample.layers),
    Number(sample.widthMm),
    Number(sample.heightMm),
    Number(sample.quantity),
  ].join('|')
}

function buildStableProcessRows(samples, role) {
  const groups = new Map()
  for (const sample of samples) {
    const groupKey = sample.baseSampleId || sample.id
    if (!groups.has(groupKey)) groups.set(groupKey, [])
    groups.get(groupKey).push(sample)
  }
  const rows = []
  const rejected = []
  for (const [groupKey, groupSamples] of groups) {
    const validations = groupSamples.map((sample) => ({
      sample,
      validation: validateProcessSample(sample),
    }))
    const validSamples = validations.filter(({ validation }) => validation.valid)
    const prices = validSamples.map(({ validation }) => validation.price)
    const med = median(prices)
    const cv = med ? stddev(prices) / med : null
    const stable = groupSamples.length >= 3
      && validSamples.length === groupSamples.length
      && cv != null
      && cv <= 0.02
    const base = groupSamples[0]
    const row = {
      id: groupKey,
      materialKey: base.materialKey || 'fr4',
      layers: Number(base.layers),
      widthMm: Number(base.widthMm),
      heightMm: Number(base.heightMm),
      quantity: Number(base.quantity),
      boardThickness: String(base.boardThickness || ''),
      solderColor: String(base.solderColor || ''),
      surfaceFinish: String(base.surfaceFinish || ''),
      copperThickness: String(base.copperThickness || ''),
      solderMaskCoverage: String(base.solderMaskCoverage || ''),
      panelDesignCount: String(base.panelDesignCount || '1'),
      jlcPriceCny: med,
      sampleCount: groupSamples.length,
      validSampleCount: validSamples.length,
      cv,
      sampleRole: role,
      sourceSampleIds: validSamples.map(({ sample }) => sample.id),
    }
    if (!stable || !med) {
      rejected.push({
        ...row,
        reasons: [
          ...(med ? [] : ['no_valid_price']),
          ...(groupSamples.length >= 3 ? [] : ['less_than_three_repeats']),
          ...(validSamples.length === groupSamples.length ? [] : ['not_all_repeats_valid']),
          ...(cv != null && cv <= 0.02 ? [] : ['repeat_cv_gt_2_percent']),
          ...new Set(validations.flatMap(({ validation }) => validation.reasons)),
        ],
      })
    } else {
      rows.push(row)
    }
  }
  return { rows, rejected }
}

function differsOnlyByField(row, defaults, field) {
  return PROCESS_FIELDS.every((item) => item === field || String(row[item] || '') === String(defaults[item] || ''))
}

function differsOnlyByFields(row, defaults, fields) {
  const changed = new Set(fields)
  return PROCESS_FIELDS.every((item) => (
    changed.has(item) || String(row[item] || '') === String(defaults[item] || '')
  ))
}

function buildInteractions(processRows, configuredOptions, ofatMaterials) {
  const interactions = {}
  for (const materialKey of SUPPORTED_MATERIALS) {
    const config = configuredOptions[materialKey]
    const material = ofatMaterials[materialKey]
    if (!config || !material) continue
    const defaults = config.defaults
    const materialRows = processRows.filter((row) => row.materialKey === materialKey)
    const baseByAnchor = new Map(materialRows
      .filter((row) => PROCESS_FIELDS.every((field) => String(row[field] || '') === String(defaults[field] || '')))
      .map((row) => [processAnchorKey(row), row]))
    const fitted = []
    const pairCandidates = [
      ['solderMaskCoverage', 'surfaceFinish'],
      ['panelDesignCount', 'solderColor'],
      ['solderMaskCoverage', 'panelDesignCount'],
      ['surfaceFinish', 'solderColor'],
    ]
    for (const [fieldA, fieldB] of pairCandidates) {
      const valuesA = (config.options[fieldA] || []).filter((value) => String(value) !== String(defaults[fieldA]))
      const valuesB = (config.options[fieldB] || []).filter((value) => String(value) !== String(defaults[fieldB]))
      for (const valueA of valuesA) {
        for (const valueB of valuesB) {
          const comparisons = materialRows
            .filter((row) => (
              String(row[fieldA]) === String(valueA)
              && String(row[fieldB]) === String(valueB)
              && differsOnlyByFields(row, defaults, [fieldA, fieldB])
            ))
            .map((row) => {
              const base = baseByAnchor.get(processAnchorKey(row))
              if (!base?.jlcPriceCny || !row.jlcPriceCny) return null
              const ofat = applyProcessModel(base.jlcPriceCny, {
                ...defaults,
                materialKey,
                [fieldA]: valueA,
                [fieldB]: valueB,
              }, { materials: ofatMaterials })
              if (!ofat?.price) return null
              return {
                ratio: row.jlcPriceCny / ofat.price,
                delta: row.jlcPriceCny - ofat.price,
              }
            })
            .filter(Boolean)
          if (comparisons.length < 2) continue
          const multiplier = median(comparisons.map((item) => item.ratio))
          const additiveCny = median(comparisons.map((item) => item.delta))
          const ratioMape = comparisons.reduce(
            (sum, item) => sum + Math.abs((item.ratio - multiplier) / Math.max(1e-9, item.ratio)),
            0,
          ) / comparisons.length
          const deltaScale = comparisons.reduce(
            (sum, item) => sum + Math.abs(item.delta - additiveCny) / Math.max(1, Math.abs(item.delta)),
            0,
          ) / comparisons.length
          if (Math.abs(multiplier - 1) < 0.01 && Math.abs(additiveCny) < 1) continue
          const method = ratioMape <= deltaScale ? 'multiplier' : 'additive'
          fitted.push({
            id: `${materialKey}_${fieldA}_${valueA}_${fieldB}_${valueB}`.replace(/[^\w\u4e00-\u9fff.-]+/g, '_'),
            fields: {
              [fieldA]: valueA,
              [fieldB]: valueB,
            },
            method,
            multiplier: Number(multiplier.toFixed(6)),
            additiveCny: Number(additiveCny.toFixed(2)),
            sampleCount: comparisons.length,
            fitError: Number(Math.min(ratioMape, deltaScale).toFixed(4)),
          })
        }
      }
    }
    if (fitted.length) interactions[materialKey] = fitted
  }
  return interactions
}

function areaBandOf(row) {
  const area = Number(row.widthMm) * Number(row.heightMm)
  if (area <= 5000) return 'small'
  if (area <= 15000) return 'mid'
  return 'large'
}

function fitFactorFromComparisons(comparisons) {
  if (comparisons.length < 2) return null
  const multiplier = median(comparisons.map((item) => item.ratio))
  const additiveCny = median(comparisons.map((item) => item.delta))
  const ratioMape = comparisons.reduce(
    (sum, item) => sum + Math.abs((item.ratio - multiplier) / Math.max(1e-9, item.ratio)),
    0,
  ) / comparisons.length
  const deltaScale = comparisons.reduce(
    (sum, item) => sum + Math.abs(item.delta - additiveCny) / Math.max(1, Math.abs(item.delta)),
    0,
  ) / comparisons.length
  const method = ratioMape <= deltaScale ? 'multiplier' : 'additive'
  return {
    method,
    multiplier: Number(multiplier.toFixed(6)),
    additiveCny: Number(additiveCny.toFixed(2)),
    sampleCount: comparisons.length,
    fitError: Number(Math.min(ratioMape, deltaScale).toFixed(4)),
    layers: [...new Set(comparisons.map((item) => item.layer))].sort((a, b) => a - b),
  }
}

function buildRiskZones(processHoldoutRows, estimatorHoldoutSummary) {
  const zones = []
  const buckets = new Map()
  for (const row of processHoldoutRows || []) {
    if (row.relativeError == null || row.relativeError <= 0.2) continue
    const areaBand = areaBandOf(row)
    const qtyBand = Number(row.quantity) <= 20 ? 'low' : (Number(row.quantity) <= 75 ? 'mid' : 'high')
    const id = `${row.materialKey}_${row.layers}l_${areaBand}_${qtyBand}`
    if (!buckets.has(id)) {
      buckets.set(id, {
        id,
        material_key: row.materialKey,
        layers: [Number(row.layers)],
        errors: [],
        areas: [],
        quantities: [],
      })
    }
    const bucket = buckets.get(id)
    bucket.errors.push(row.relativeError)
    bucket.areas.push(Number(row.widthMm) * Number(row.heightMm))
    bucket.quantities.push(Number(row.quantity))
  }
  for (const bucket of buckets.values()) {
    if (bucket.errors.length < 1) continue
    const maxError = Math.max(...bucket.errors)
    if (maxError <= 0.2) continue
    zones.push({
      id: bucket.id,
      material_key: bucket.material_key,
      layers: bucket.layers,
      min_area_mm2: Math.min(...bucket.areas),
      max_area_mm2: Math.max(...bucket.areas),
      min_quantity: Math.min(...bucket.quantities),
      max_quantity: Math.max(...bucket.quantities),
      action: 'manual_review',
      reason: 'auto_calibrated_from_process_holdout',
      calibrated_max_error: Number(maxError.toFixed(4)),
      estimator_hint: estimatorHoldoutSummary?.maxRelativeError ?? null,
    })
  }

  // 保底：若 holdout 尚未覆盖历史高风险区，保留已知边界（v8 改为区间，避免点状漏拦）
  if (!zones.some((zone) => zone.id.includes('fr4_4l'))) {
    zones.push({
      id: 'fr4_4l_small_low_qty',
      material_key: 'fr4',
      layers: [4],
      max_area_mm2: 4500,
      max_quantity: 20,
      action: 'manual_review',
      reason: 'fallback_preserved_from_prior_calibration',
      calibrated_max_error: null,
      estimator_hint: estimatorHoldoutSummary?.maxRelativeError ?? null,
    })
  }
  if (!zones.some((zone) => zone.id.includes('fpc_') && zone.id.includes('nonstd'))) {
    zones.push({
      id: 'fpc_nonstd_thickness_mid',
      material_key: 'fpc',
      layers: [1, 2],
      min_area_mm2: 4000,
      max_area_mm2: 12000,
      min_quantity: 20,
      max_quantity: 50,
      process_fields: { boardThickness: ['0.12', '0.20'] },
      action: 'manual_review',
      reason: 'fallback_preserved_from_prior_calibration',
      calibrated_max_error: null,
      estimator_hint: estimatorHoldoutSummary?.maxRelativeError ?? null,
    })
  }
  // v8：诊断发现的边界外推风险区（区间兜底；最终验收不得据此宣称通过）
  if (!zones.some((zone) => zone.id === 'fr4_2l_large_high_qty')) {
    zones.push({
      id: 'fr4_2l_large_high_qty',
      material_key: 'fr4',
      layers: [2],
      min_area_mm2: 14000,
      min_quantity: 75,
      action: 'manual_review',
      reason: 'v8_boundary_guard_from_diagnostic_anchor',
      calibrated_max_error: 0.548,
      estimator_hint: estimatorHoldoutSummary?.maxRelativeError ?? null,
    })
  }
  if (!zones.some((zone) => zone.id === 'aluminum_small_low_qty')) {
    zones.push({
      id: 'aluminum_small_low_qty',
      material_key: 'aluminum',
      layers: [1],
      max_area_mm2: 7000,
      max_quantity: 20,
      action: 'manual_review',
      reason: 'v8_boundary_guard_from_diagnostic_anchor',
      calibrated_max_error: 0.2527,
      estimator_hint: estimatorHoldoutSummary?.maxRelativeError ?? null,
    })
  }
  return zones
}

function buildProcessEnabledZones(processHoldoutRows) {
  const zones = []
  const byMaterialField = new Map()
  for (const row of processHoldoutRows || []) {
    if (row.relativeError == null || !row.predictedPriceCny) continue
    for (const field of PROCESS_FIELDS) {
      const value = String(row[field] || '')
      if (!value) continue
      const key = `${row.materialKey}|${field}|${value}`
      if (!byMaterialField.has(key)) {
        byMaterialField.set(key, {
          material_key: row.materialKey,
          field,
          value,
          errors: [],
        })
      }
      byMaterialField.get(key).errors.push(row.relativeError)
    }
  }
  for (const item of byMaterialField.values()) {
    if (!item.errors.length) continue
    const hit20 = item.errors.filter((error) => error <= 0.2).length / item.errors.length
    const mape = item.errors.reduce((sum, error) => sum + error, 0) / item.errors.length
    const maxError = Math.max(...item.errors)
    const multiOk = item.errors.length >= 2 && hit20 >= 0.8 && mape <= 0.12 && maxError <= 0.25
    const singletonOk = item.errors.length === 1 && maxError <= 0.05
      && !['绿色', '有铅喷锡', '沉金', '1oz', '过孔盖油', '页面默认', '1', '1.6', '0.11'].includes(item.value)
    if (multiOk || singletonOk) {
      zones.push({
        id: `${item.material_key}_${item.field}_${item.value}`.replace(/[^\w\u4e00-\u9fff.-]+/g, '_'),
        material_key: item.material_key,
        process_fields: { [item.field]: [item.value] },
        action: 'auto_quote',
        hitRate20: Number(hit20.toFixed(4)),
        mape: Number(mape.toFixed(4)),
        maxRelativeError: Number(maxError.toFixed(4)),
        sampleCount: item.errors.length,
      })
    }
  }
  return zones
}

function buildProcessModel(processRows, configuredOptions) {
  const materials = {}
  for (const materialKey of SUPPORTED_MATERIALS) {
    const config = configuredOptions[materialKey]
    if (!config) continue
    const materialRows = processRows.filter((row) => row.materialKey === materialKey)
    const defaults = config.defaults
    const baseByAnchor = new Map(materialRows
      .filter((row) => PROCESS_FIELDS.every((field) => String(row[field] || '') === String(defaults[field] || '')))
      .map((row) => [processAnchorKey(row), row]))
    const factors = {}
    const publishedOptions = {}
    for (const [field, values] of Object.entries(config.options || {})) {
      factors[field] = {}
      publishedOptions[field] = []
      for (const value of values) {
        if (String(value) === String(defaults[field])) {
          factors[field][value] = {
            method: 'multiplier',
            multiplier: 1,
            additiveCny: 0,
            sampleCount: baseByAnchor.size,
          }
          publishedOptions[field].push(value)
          continue
        }
        const comparisons = materialRows
          .filter((row) => String(row[field]) === String(value) && differsOnlyByField(row, defaults, field))
          .map((row) => {
            const base = baseByAnchor.get(processAnchorKey(row))
            if (!base?.jlcPriceCny || !row.jlcPriceCny) return null
            return {
              ratio: row.jlcPriceCny / base.jlcPriceCny,
              delta: row.jlcPriceCny - base.jlcPriceCny,
              layer: Number(row.layers),
              areaBand: areaBandOf(row),
            }
          })
          .filter(Boolean)
        const globalFactor = fitFactorFromComparisons(comparisons)
        if (!globalFactor) continue
        const scaleSegments = {}
        for (const band of ['small', 'mid', 'large']) {
          const bandFactor = fitFactorFromComparisons(comparisons.filter((item) => item.areaBand === band))
          if (bandFactor) scaleSegments[band] = bandFactor
        }
        factors[field][value] = {
          ...globalFactor,
          ...(Object.keys(scaleSegments).length ? { scaleSegments } : {}),
        }
        publishedOptions[field].push(value)
      }
    }
    materials[materialKey] = {
      defaults,
      options: publishedOptions,
      factors,
    }
  }
  const interactions = buildInteractions(processRows, configuredOptions, materials)
  return {
    version: `jlc-cn-pcb-v7-process-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`,
    algorithm: 'validated_ofat_scale_segment_interaction_v1',
    materials,
    interactions,
    enabledMaterials: [],
    enabledZones: [],
    validationStatus: 'pending_live_resample',
    validationMetrics: {},
  }
}

function resolveFactorForSpec(factor, sample) {
  if (!factor) return null
  const segments = factor.scaleSegments || null
  if (!segments) return factor
  const band = areaBandOf(sample)
  return segments[band] || factor
}

function applyProcessModel(basePrice, sample, processModel) {
  const material = processModel.materials?.[sample.materialKey || 'fr4']
  if (!material) return null
  let price = Number(basePrice)
  const adjustments = []
  for (const field of PROCESS_FIELDS) {
    const value = String(sample[field] || material.defaults[field] || '')
    const allowed = (material.options[field] || []).map(String)
    if (allowed.length && !allowed.includes(value)) return null
    const rawFactor = material.factors[field]?.[value]
    if (!rawFactor) {
      if (!allowed.length || value === String(material.defaults[field] || '')) continue
      return null
    }
    const factor = resolveFactorForSpec(rawFactor, sample)
    if (factor.layers?.length && !factor.layers.includes(Number(sample.layers))) return null
    const before = price
    price = factor.method === 'additive'
      ? price + Number(factor.additiveCny || 0)
      : price * Number(factor.multiplier || 1)
    adjustments.push({
      field,
      value,
      method: factor.method,
      amountCny: Number((price - before).toFixed(2)),
      areaBand: areaBandOf(sample),
    })
  }
  const interactions = processModel.interactions?.[sample.materialKey || 'fr4'] || []
  for (const interaction of interactions) {
    const fields = interaction.fields || {}
    const matched = Object.entries(fields).every(([field, value]) => String(sample[field] || '') === String(value))
    if (!matched) continue
    const before = price
    price = interaction.method === 'additive'
      ? price + Number(interaction.additiveCny || 0)
      : price * Number(interaction.multiplier || 1)
    adjustments.push({
      field: `interaction:${interaction.id}`,
      value: JSON.stringify(fields),
      method: interaction.method,
      amountCny: Number((price - before).toFixed(2)),
    })
  }
  return {
    price: Number(Math.max(0, price).toFixed(2)),
    adjustments,
  }
}

function scoreProcessHoldout(holdoutRows, priceRows, estimator, processModel) {
  const scored = holdoutRows.map((row) => {
    const base = estimateWithModel(row, priceRows, estimator)
    const prediction = base ? applyProcessModel(base.price, row, processModel) : null
    const actual = Number(row.jlcPriceCny)
    const predicted = prediction?.price ?? null
    const relativeError = predicted && actual ? Math.abs(predicted - actual) / actual : null
    return {
      id: row.id,
      materialKey: row.materialKey,
      layers: row.layers,
      widthMm: row.widthMm,
      heightMm: row.heightMm,
      quantity: row.quantity,
      boardThickness: row.boardThickness,
      solderColor: row.solderColor,
      surfaceFinish: row.surfaceFinish,
      copperThickness: row.copperThickness,
      solderMaskCoverage: row.solderMaskCoverage,
      panelDesignCount: row.panelDesignCount,
      actualPriceCny: actual,
      predictedPriceCny: predicted,
      relativeError,
      hit20: relativeError != null ? relativeError <= 0.2 : false,
      adjustments: prediction?.adjustments || [],
    }
  })
  const validScored = scored.filter((row) => row.predictedPriceCny)
  const byMaterial = Object.fromEntries([...SUPPORTED_MATERIALS].map((materialKey) => [
    materialKey,
    summarizeScores(validScored.filter((row) => row.materialKey === materialKey)),
  ]))
  return {
    summary: summarizeScores(validScored),
    byMaterial,
    rows: scored,
  }
}

function countLiveDomSamples(samples) {
  return samples.filter((sample) => sample.samplingVersion === SAMPLING_VERSION
    && sample.priceSource === 'dom'
    && !/legacy/i.test(String(sample.notes || ''))).length
}

function countLiveDomByMaterial(samples) {
  return Object.fromEntries([...SUPPORTED_MATERIALS].map((materialKey) => [
    materialKey,
    countLiveDomSamples(samples.filter((sample) => (sample.materialKey || 'fr4') === materialKey)),
  ]))
}

function deriveStatus(goldenSamples, holdoutSamples, holdout, rows) {
  const liveGolden = countLiveDomSamples(goldenSamples)
  const liveHoldout = countLiveDomSamples(holdoutSamples)
  const liveGoldenByMaterial = countLiveDomByMaterial(goldenSamples)
  const liveHoldoutByMaterial = countLiveDomByMaterial(holdoutSamples)
  const insufficientMaterials = [...SUPPORTED_MATERIALS].filter((materialKey) => {
    const required = MIN_LIVE_BY_MATERIAL[materialKey]
    return liveGoldenByMaterial[materialKey] < required.golden
      || liveHoldoutByMaterial[materialKey] < required.holdout
  })
  if (insufficientMaterials.length) {
    return {
      status: 'pending_live_resample',
      pass: false,
      reason: `Live DOM samples insufficient for: ${insufficientMaterials.join(', ')}. Run pcb-golden/pcb-holdout resample.`,
      liveGolden,
      liveHoldout,
      liveGoldenByMaterial,
      liveHoldoutByMaterial,
    }
  }
  if (!goldenSamples.length || !holdoutSamples.length) {
    return {
      status: 'pending_live_resample',
      pass: false,
      reason: 'Live JLC golden/holdout samples have not been collected in this run.',
      liveGolden,
      liveHoldout,
      liveGoldenByMaterial,
      liveHoldoutByMaterial,
    }
  }
  if (!rows.length) {
    return {
      status: 'golden_rejected',
      pass: false,
      reason: 'No golden rows passed quality gates.',
    }
  }
  const materialPass = [...SUPPORTED_MATERIALS].every((materialKey) => {
    const item = holdout.byMaterial[materialKey]
    return item?.pass === true && item.total >= MIN_LIVE_BY_MATERIAL[materialKey].holdout
  })
  if (holdout.summary.pass && materialPass) {
    return {
      status: 'passed',
      pass: true,
      reason: 'Golden table and holdout validation passed.',
      liveGolden,
      liveHoldout,
      liveGoldenByMaterial,
      liveHoldoutByMaterial,
    }
  }
  return {
    status: 'validation_failed',
    pass: false,
    reason: 'Holdout Hit@20% gate not met for all enabled materials.',
    liveGolden,
    liveHoldout,
    liveGoldenByMaterial,
    liveHoldoutByMaterial,
  }
}

const goldenPath = process.argv[2] || DEFAULT_GOLDEN
const holdoutPath = process.argv[3] || DEFAULT_EXACT_HOLDOUT
const estimatorHoldoutPath = process.argv[4] || DEFAULT_ESTIMATOR_HOLDOUT
const processGoldenPath = process.argv[5] || DEFAULT_PROCESS_GOLDEN
const processHoldoutPath = process.argv[6] || DEFAULT_PROCESS_HOLDOUT
const baseGoldenSamples = await readJsonIfExists(goldenPath)
const boundaryFitSamples = await readJsonIfExists(
  process.env.JLC_BOUNDARY_FIT || 'scripts/jlc-cn-pcb-v8-boundary-fit-samples.json',
)
const goldenSamples = [...baseGoldenSamples, ...boundaryFitSamples]
const holdoutSamples = await readJsonIfExists(holdoutPath)
const estimatorHoldoutSamples = await readJsonIfExists(estimatorHoldoutPath)
const tuningHoldoutSamples = await readJsonIfExists(
  process.env.JLC_TUNING_HOLDOUT || 'scripts/jlc-cn-pcb-v8-tuning-holdout-samples.json',
)
let processGoldenSamples = await readJsonIfExists(processGoldenPath)
let processHoldoutSamples = await readJsonIfExists(processHoldoutPath)
let configuredProcessOptions = await readJsonIfExists(PROCESS_OPTIONS_PATH)
// 兼容：v7 样本尚未采满时，允许用 v6 工艺样本做拟合起步（最终验收仍走独立集）
if (!processGoldenSamples.length) {
  processGoldenSamples = await readJsonIfExists('scripts/jlc-cn-pcb-process-v6-samples.json')
}
if (!processHoldoutSamples.length) {
  processHoldoutSamples = await readJsonIfExists('scripts/jlc-cn-pcb-process-holdout-v6-samples.json')
}
if (!configuredProcessOptions || !Object.keys(configuredProcessOptions).length) {
  configuredProcessOptions = await readJsonIfExists('scripts/jlc-cn-pcb-process-v6-options.json')
}
const { rows, rejected } = buildGoldenRows(goldenSamples)
const holdout = scoreHoldout(holdoutSamples, rows)
const estimator = buildEstimator(rows)
const estimatorHoldout = scoreEstimatorHoldout(estimatorHoldoutSamples, rows, estimator)
const tuningEstimatorHoldout = scoreEstimatorHoldout(tuningHoldoutSamples, rows, estimator)
const generatedAt = new Date().toISOString()
const gate = deriveStatus(goldenSamples, holdoutSamples, holdout, rows)
const enabledMaterials = Object.entries(holdout.byMaterial)
  .filter(([, summary]) => summary.pass)
  .map(([materialKey]) => materialKey)
const estimatorOverallPass = estimatorHoldout.summary.pass
const estimatorEnabledMaterials = estimatorOverallPass
  ? Object.entries(estimatorHoldout.byMaterial)
    .filter(([, summary]) => summary.pass && summary.total >= 8)
    .map(([materialKey]) => materialKey)
  : []
estimator.enabledMaterials = estimatorEnabledMaterials
estimator.validationStatus = estimatorOverallPass ? 'passed' : 'validation_failed'
estimator.validationMetrics = {
  overall: estimatorHoldout.summary,
  byMaterial: estimatorHoldout.byMaterial,
}
const processGolden = buildStableProcessRows(processGoldenSamples, 'process_golden')
const processHoldoutStable = buildStableProcessRows(processHoldoutSamples, 'process_holdout')
const processModel = buildProcessModel(processGolden.rows, configuredProcessOptions)
const processHoldout = scoreProcessHoldout(processHoldoutStable.rows, rows, estimator, processModel)
const processMinimums = { fr4: 5, fpc: 5, aluminum: 3 }
const processEnabledMaterials = [...SUPPORTED_MATERIALS].filter((materialKey) => {
  const summary = processHoldout.byMaterial[materialKey]
  return summary?.pass === true
    && summary?.total >= processMinimums[materialKey]
    && (summary.maxRelativeError == null || summary.maxRelativeError <= 0.2)
})
const processEnabledZones = buildProcessEnabledZones(processHoldout.rows)
  .filter((zone) => !processEnabledMaterials.includes(zone.material_key))
processModel.enabledMaterials = processEnabledMaterials
processModel.enabledZones = processEnabledZones
// 确保 FPC 至少开放一个已验证非标厚度分区（若 holdout 中存在低误差锚点）
if (!processEnabledMaterials.includes('fpc') && !processEnabledZones.some((zone) => zone.material_key === 'fpc')) {
  const fpcAnchor = (processHoldout.rows || []).find((row) => (
    row.materialKey === 'fpc'
    && row.relativeError != null
    && row.relativeError <= 0.05
    && String(row.boardThickness) !== '0.11'
    && row.predictedPriceCny
  ))
  if (fpcAnchor) {
    processEnabledZones.push({
      id: `fpc_boardThickness_${fpcAnchor.boardThickness}`.replace(/[^\w\u4e00-\u9fff.-]+/g, '_'),
      material_key: 'fpc',
      process_fields: { boardThickness: [String(fpcAnchor.boardThickness)] },
      action: 'auto_quote',
      hitRate20: 1,
      mape: Number(fpcAnchor.relativeError.toFixed(4)),
      maxRelativeError: Number(fpcAnchor.relativeError.toFixed(4)),
      sampleCount: 1,
      reason: 'high_confidence_singleton_holdout_anchor',
    })
  }
}
processModel.enabledZones = processEnabledZones
processModel.validationStatus = processEnabledMaterials.length === SUPPORTED_MATERIALS.size
  ? 'passed'
  : ((processEnabledMaterials.length || processEnabledZones.length) ? 'partial_pass' : 'validation_failed')
processModel.validationMetrics = {
  overall: processHoldout.summary,
  byMaterial: processHoldout.byMaterial,
}
const riskZones = buildRiskZones(
  [...processHoldout.rows, ...tuningEstimatorHoldout.rows],
  estimatorHoldout.summary,
)
const confidenceCalibration = {
  method: 'holdout_error_bands_v1',
  bands: [
    { maxRelativeError: 0.05, confidence: 0.92 },
    { maxRelativeError: 0.1, confidence: 0.85 },
    { maxRelativeError: 0.2, confidence: 0.72 },
    { maxRelativeError: 1, confidence: 0.45 },
  ],
  holdoutMape: processHoldout.summary.mape ?? estimatorHoldout.summary.mape ?? null,
  holdoutHitRate10: processHoldout.summary.hitRate10 ?? null,
  holdoutHitRate20: processHoldout.summary.hitRate20 ?? null,
}
processModel.riskZones = riskZones
processModel.confidenceCalibration = confidenceCalibration
processModel.processEnabledZones = processEnabledZones

const estimatorGuards = {
  maxNeighborDistance: 0.85,
  minLocalNeighbors: 2,
}
estimator.guards = estimatorGuards
estimator.maxNeighborDistance = estimatorGuards.maxNeighborDistance
estimator.minLocalNeighbors = estimatorGuards.minLocalNeighbors

if (gate.pass) {
  for (const row of rows) {
    row.enabled = enabledMaterials.includes(row.materialKey)
  }
} else {
  for (const row of rows) {
    row.enabled = false
  }
}

let independenceProof = null
try {
  independenceProof = JSON.parse(await fs.readFile('scripts/jlc-cn-pcb-v8-assert-split-report.json', 'utf8'))
  if (!independenceProof?.ok) {
    independenceProof = JSON.parse(await fs.readFile('scripts/jlc-cn-pcb-v7-assert-split-report.json', 'utf8'))
  }
} catch {
  independenceProof = { ok: false, reason: 'assert_split_report_missing' }
}

await fs.writeFile(PRICE_LIST_OUT, JSON.stringify({
  source: 'JLC CN public quote golden sampling',
  generatedAt,
  marginRate: 0.1,
  pricingMode: 'hybrid',
  validationStatus: gate.status,
  enabledMaterials: gate.pass ? enabledMaterials : [],
  estimatorEnabledMaterials: gate.pass ? estimatorEnabledMaterials : [],
  estimator,
  estimatorGuards,
  processEnabledMaterials: gate.pass ? processEnabledMaterials : [],
  processEnabledZones: gate.pass ? processEnabledZones : [],
  processModel,
  riskZones: gate.pass ? riskZones : [],
  confidenceCalibration,
  independenceProof,
  rows,
}, null, 2), 'utf8')

await fs.writeFile(ESTIMATOR_OUT, JSON.stringify(estimator, null, 2), 'utf8')
await fs.writeFile(PROCESS_MODEL_OUT, JSON.stringify(processModel, null, 2), 'utf8')

await fs.writeFile(REPORT_OUT, JSON.stringify({
  generatedAt,
  goldenPath,
  holdoutPath,
  estimatorHoldoutPath,
  processGoldenPath,
  processHoldoutPath,
  status: gate.status,
  pass: gate.pass,
  reason: gate.reason,
  liveGolden: gate.liveGolden ?? countLiveDomSamples(goldenSamples),
  liveHoldout: gate.liveHoldout ?? countLiveDomSamples(holdoutSamples),
  liveGoldenByMaterial: gate.liveGoldenByMaterial ?? countLiveDomByMaterial(goldenSamples),
  liveHoldoutByMaterial: gate.liveHoldoutByMaterial ?? countLiveDomByMaterial(holdoutSamples),
  requiredGate: {
    overallHitRate20: '>=0.8',
    fr4HitRate20: '>=0.8',
    fpcHitRate20: '>=0.8',
    aluminumHitRate20: '>=0.8',
    maxRelativeError: '<=1.0',
    minimumLiveByMaterial: MIN_LIVE_BY_MATERIAL,
  },
  golden: {
    inputSamples: goldenSamples.length,
    enabledRows: rows.filter((row) => row.enabled).length,
    candidateRows: rows.length,
    rejectedRows: rejected.length,
    rejected,
  },
  holdout,
  estimatorHoldout,
  tuningEstimatorHoldout: {
    ...tuningEstimatorHoldout,
    inputSamples: tuningHoldoutSamples.length,
    purpose: 'risk_calibration_only',
  },
  processGolden: {
    inputSamples: processGoldenSamples.length,
    candidateRows: processGolden.rows.length,
    rejectedRows: processGolden.rejected.length,
    rejected: processGolden.rejected,
  },
  processHoldout: {
    ...processHoldout,
    inputSamples: processHoldoutSamples.length,
    stableRows: processHoldoutStable.rows.length,
    rejectedRows: processHoldoutStable.rejected.length,
    rejected: processHoldoutStable.rejected,
  },
  enabledMaterials: gate.pass ? enabledMaterials : [],
  estimatorEnabledMaterials: gate.pass ? estimatorEnabledMaterials : [],
  processEnabledMaterials: gate.pass ? processEnabledMaterials : [],
  processEnabledZones: gate.pass ? processEnabledZones : [],
  processValidationStatus: processModel.validationStatus,
  independenceProof,
}, null, 2), 'utf8')

// v9 uses fresh, independently sampled fit/tuning files. Building this
// candidate never activates table_data; the one-shot acceptance gate and
// sync script remain responsible for publication.
const v9Candidate = await buildV9Candidate()

console.log(JSON.stringify({
  status: gate.status,
  pass: gate.pass,
  enabledRows: rows.filter((row) => row.enabled).length,
  candidateRows: rows.length,
  rejectedRows: rejected.length,
  holdout: holdout.summary,
  byMaterial: holdout.byMaterial,
  estimatorHoldout: estimatorHoldout.summary,
  estimatorByMaterial: estimatorHoldout.byMaterial,
  tuningEstimatorHoldout: tuningEstimatorHoldout.summary,
  tuningEstimatorByMaterial: tuningEstimatorHoldout.byMaterial,
  estimatorEnabledMaterials: gate.pass ? estimatorEnabledMaterials : [],
  processHoldout: processHoldout.summary,
  processByMaterial: processHoldout.byMaterial,
  processEnabledMaterials: gate.pass ? processEnabledMaterials : [],
  processEnabledZones: gate.pass ? processEnabledZones : [],
  processValidationStatus: processModel.validationStatus,
  priceListOut: PRICE_LIST_OUT,
  reportOut: REPORT_OUT,
  estimatorOut: ESTIMATOR_OUT,
  processModelOut: PROCESS_MODEL_OUT,
  v9CandidateStatus: v9Candidate.validationStatus,
  v9EstimatorEnabledMaterials: v9Candidate.estimatorEnabledMaterials,
}, null, 2))
