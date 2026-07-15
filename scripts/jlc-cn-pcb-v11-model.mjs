import {
  aggregateStableTriples,
  estimateV9,
} from './jlc-cn-pcb-v9-model.mjs'
import {
  buildV10Estimator,
  estimateV10,
  quantityBand,
} from './jlc-cn-pcb-v10-model.mjs'

export { aggregateStableTriples, quantityBand } from './jlc-cn-pcb-v10-model.mjs'

function median(values) {
  const sorted = values.filter(Number.isFinite).sort((left, right) => left - right)
  if (!sorted.length) return null
  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
}

function areaOf(row) {
  return Number(row.widthMm ?? row.width_mm) * Number(row.heightMm ?? row.height_mm)
}

function priceOf(row) {
  return Number(row.jlcPriceCny ?? row.jlc_price_cny ?? row.domPriceCny)
}

function materialOf(row) {
  return row.materialKey || row.material_key
}

function buildLayerBandConfig(rows, baseGuards) {
  const result = {}
  for (const layer of [...new Set(rows.map((row) => Number(row.layers)))]) {
    result[layer] = {}
    for (const band of ['low', 'medium', 'high']) {
      const bandRows = rows.filter(
        (row) => Number(row.layers) === layer && quantityBand(row.quantity) === band,
      )
      if (!bandRows.length) continue
      const prices = bandRows.map(priceOf).sort((left, right) => left - right)
      result[layer][band] = {
        floorPriceCny: Number(
          median(prices.slice(0, Math.max(3, Math.ceil(prices.length * 0.2)))).toFixed(2),
        ),
        areaExponent: 0.85,
        quantityExponent: band === 'low' ? 0.35 : (band === 'medium' ? 0.65 : 0.85),
        maxNeighborDistance: baseGuards.maxNeighborDistance,
        minLocalNeighbors: baseGuards.minLocalNeighbors,
        neighbors: 6,
        maxPredictionMultiplier: 2.5,
        minPredictionMultiplier: 0.5,
        maxLocalResidualRatio: 0.35,
        rateAggregation: 'median_rate',
      }
    }
  }
  return result
}

export function buildV11Estimator(rows) {
  const estimator = buildV10Estimator(rows)
  estimator.version = 'jlc-cn-pcb-v11-material-estimator'
  const fr4Rows = rows.filter((row) => materialOf(row) === 'fr4' && priceOf(row) > 0)
  if (fr4Rows.length) {
    const base = estimator.materials.fr4
    estimator.materials.fr4 = {
      ...base,
      modelType: 'fr4_layered_floor_area_quantity',
      formula: 'layered_floor_area_quantity',
      layerQuantityBands: buildLayerBandConfig(fr4Rows, base.guards),
      guards: {
        ...base.guards,
        maxNeighborDistance: 0.65,
        minLocalNeighbors: 2,
      },
    }
  }
  return estimator
}

function distance(target, row, guards) {
  return Math.sqrt(
    (Math.log(areaOf(target) / areaOf(row)) * Number(guards.areaWeight || 1)) ** 2
    + (Math.log(Number(target.quantity) / Number(row.quantity))
      * Number(guards.quantityWeight || 0.7)) ** 2,
  )
}

function estimateLayered(rows, estimator, target, materialKey) {
  const config = estimator.materials?.[materialKey]
  const layer = String(Number(target.layers))
  const band = quantityBand(target.quantity)
  const formula = config.layerQuantityBands?.[layer]?.[band]
  if (!formula) return null
  const width = Number(target.widthMm ?? target.width_mm)
  const height = Number(target.heightMm ?? target.height_mm)
  const quantity = Number(target.quantity)
  if (
    width < config.minWidthMm || width > config.maxWidthMm
    || height < config.minHeightMm || height > config.maxHeightMm
    || quantity < config.minQuantity || quantity > config.maxQuantity
  ) return null
  const candidates = rows.filter((row) => (
    materialOf(row) === materialKey
    && Number(row.layers) === Number(target.layers)
    && quantityBand(row.quantity) === band
    && priceOf(row) > 0
  ))
  const nearest = candidates
    .map((row) => ({ row, distance: distance(target, row, config.guards) }))
    .sort((left, right) => left.distance - right.distance)
    .slice(0, formula.neighbors)
  const local = nearest.filter((item) => item.distance <= formula.maxNeighborDistance)
  if (local.length < formula.minLocalNeighbors) return null
  const floor = Number(formula.floorPriceCny)
  const rates = local.map(({ row }) => (
    Math.max(priceOf(row) - floor, 0.01)
    / (areaOf(row) ** formula.areaExponent)
    / (Number(row.quantity) ** formula.quantityExponent)
  ))
  const rate = formula.rateAggregation === 'distance_weighted_rate'
    ? local.reduce(
      (sum, item, index) => sum + (rates[index] / ((item.distance ** 2) + 0.005)),
      0,
    ) / local.reduce((sum, item) => sum + (1 / ((item.distance ** 2) + 0.005)), 0)
    : median(rates)
  const predicted = floor
    + rate * (areaOf(target) ** formula.areaExponent) * (quantity ** formula.quantityExponent)
  const basisMedian = median(local.map(({ row }) => priceOf(row)))
  const multiplier = predicted / basisMedian
  if (
    !Number.isFinite(predicted)
    || multiplier < formula.minPredictionMultiplier
    || multiplier > formula.maxPredictionMultiplier
  ) return null
  const residuals = local.map(({ row }) => {
    const fitted = floor
      + rate * (areaOf(row) ** formula.areaExponent)
      * (Number(row.quantity) ** formula.quantityExponent)
    return Math.abs(fitted - priceOf(row)) / priceOf(row)
  })
  if (median(residuals) > formula.maxLocalResidualRatio) return null
  return {
    jlcPriceCny: Number(predicted.toFixed(2)),
    averageDistance: Number(
      (local.reduce((sum, item) => sum + item.distance, 0) / local.length).toFixed(4),
    ),
    localCoverage: local.length,
    extrapolation: false,
    basis: local.map((item) => item.row),
    layer: Number(layer),
    quantityBand: band,
  }
}

export function estimateV11(rows, estimator, target) {
  const materialKey = materialOf(target)
  const config = estimator.materials?.[materialKey]
  if (
    config?.modelType === 'fr4_layered_floor_area_quantity'
    || config?.modelType === 'fpc_layered_floor_area_quantity'
  ) {
    return estimateLayered(rows, estimator, target, materialKey)
  }
  return estimateV10(rows, estimator, target)
}

export function scoreRows(fitRows, estimator, holdoutRows) {
  return holdoutRows.map((target) => {
    const estimate = estimateV11(fitRows, estimator, target)
    const actual = priceOf(target)
    return {
      id: target.id,
      materialKey: materialOf(target),
      layers: Number(target.layers),
      widthMm: Number(target.widthMm ?? target.width_mm),
      heightMm: Number(target.heightMm ?? target.height_mm),
      quantity: Number(target.quantity),
      actual,
      estimate,
      relativeError: estimate && actual > 0
        ? Math.abs(estimate.jlcPriceCny - actual) / actual
        : null,
    }
  })
}
