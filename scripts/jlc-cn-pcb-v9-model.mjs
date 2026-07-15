const MATERIAL_GUARDS = {
  fr4: { maxNeighborDistance: 0.7, minLocalNeighbors: 2, areaWeight: 1, quantityWeight: 0.8 },
  fpc: { maxNeighborDistance: 0.75, minLocalNeighbors: 2, areaWeight: 1, quantityWeight: 0.7 },
  aluminum: {
    maxNeighborDistance: 0.65,
    minLocalNeighbors: 3,
    areaWeight: 1.15,
    quantityWeight: 0.95,
    areaExponent: 0.92,
    quantityExponent: 0.72,
  },
}

function median(values) {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b)
  if (!sorted.length) return null
  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2
}

function coefficientOfVariation(values) {
  if (values.length < 2) return null
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length
  if (!mean) return null
  const variance = values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / values.length
  return Math.sqrt(variance) / mean
}

function processOptionOk(row, field, state) {
  if (state?.selected === true) return true
  return (
    field === 'solderMaskCoverage'
    && state?.requested === '过孔盖油'
    && (
      String(row.priceText || '').includes('过孔盖油已经免费升级为过孔塞油')
      || (
        (row.materialKey || row.material_key) === 'fr4'
        && Number(row.layers) === 4
      )
    )
  )
}

export function aggregateStableTriples(rows) {
  const groups = new Map()
  for (const row of rows || []) {
    const key = row.baseSampleId || String(row.id || '').replace(/-R\d+$/, '')
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(row)
  }
  const accepted = []
  const rejected = []
  for (const [baseSampleId, group] of groups) {
    const valid = group.filter((row) => {
      const processOk = Object.entries(row.selectedProcessOptions || {}).every(
        ([field, state]) => processOptionOk(row, field, state),
      )
      return row.priceSource === 'dom'
        && Number(row.domPriceCny) > 0
        && !row.error
        && row.quarantined !== true
        && row.diagnosticOnly !== true
        && !/V[78]-ACC/.test(String(row.id || ''))
        && processOk
    })
    const prices = valid.map((row) => Number(row.domPriceCny))
    const cv = coefficientOfVariation(prices)
    if (group.length === 3 && valid.length === 3 && cv != null && cv <= 0.02) {
      accepted.push({
        ...valid[0],
        id: baseSampleId,
        jlcPriceCny: Number(median(prices).toFixed(2)),
        stableRepeatCount: 3,
        repeatCv: cv,
      })
    } else {
      rejected.push({ baseSampleId, rows: group.length, validRows: valid.length, cv })
    }
  }
  return { accepted, rejected }
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

export function segmentKey(row) {
  const area = areaOf(row)
  const quantity = Number(row.quantity)
  const areaSegment = area <= 6000 ? 'small' : (area <= 16000 ? 'medium' : 'large')
  const quantitySegment = quantity <= 20 ? 'low' : (quantity <= 75 ? 'medium' : 'high')
  return `${Number(row.layers)}|${areaSegment}|${quantitySegment}`
}

export function buildV9Estimator(rows) {
  const materials = {}
  for (const materialKey of ['fr4', 'fpc', 'aluminum']) {
    const materialRows = rows.filter((row) => materialOf(row) === materialKey && priceOf(row) > 0)
    if (!materialRows.length) continue
    const prices = materialRows.map(priceOf)
    const floorPriceCny = materialKey === 'aluminum'
      ? Number(Math.max(0, median([...prices].sort((a, b) => a - b).slice(0, Math.max(3, Math.ceil(prices.length * 0.15))))).toFixed(2))
      : null
    materials[materialKey] = {
      modelType: materialKey === 'fr4'
        ? 'fr4_segmented'
        : (materialKey === 'aluminum' ? 'aluminum_floor_area_quantity' : 'fpc_local'),
      layers: [...new Set(materialRows.map((row) => Number(row.layers)))].sort((a, b) => a - b),
      minWidthMm: Math.min(...materialRows.map((row) => Number(row.widthMm ?? row.width_mm))),
      maxWidthMm: Math.max(...materialRows.map((row) => Number(row.widthMm ?? row.width_mm))),
      minHeightMm: Math.min(...materialRows.map((row) => Number(row.heightMm ?? row.height_mm))),
      maxHeightMm: Math.max(...materialRows.map((row) => Number(row.heightMm ?? row.height_mm))),
      minQuantity: Math.min(...materialRows.map((row) => Number(row.quantity))),
      maxQuantity: Math.max(...materialRows.map((row) => Number(row.quantity))),
      floorPriceCny,
      formula: 'local_log',
      useSegments: materialKey === 'fr4',
      guards: MATERIAL_GUARDS[materialKey],
      segments: [...new Set(materialRows.map(segmentKey))].sort(),
    }
  }
  return {
    version: 'jlc-cn-pcb-v9-material-estimator',
    validationStatus: 'pending_tuning',
    neighbors: 6,
    materials,
  }
}

function distance(target, row, guards) {
  return Math.sqrt(
    (Math.log(areaOf(target) / areaOf(row)) * guards.areaWeight) ** 2
    + (Math.log(Number(target.quantity) / Number(row.quantity)) * guards.quantityWeight) ** 2,
  )
}

export function estimateV9(rows, estimator, target) {
  const materialKey = materialOf(target)
  const config = estimator.materials?.[materialKey]
  if (!config || !config.layers.includes(Number(target.layers))) return null
  const width = Number(target.widthMm ?? target.width_mm)
  const height = Number(target.heightMm ?? target.height_mm)
  const quantity = Number(target.quantity)
  if (
    width < config.minWidthMm || width > config.maxWidthMm
    || height < config.minHeightMm || height > config.maxHeightMm
    || quantity < config.minQuantity || quantity > config.maxQuantity
  ) return null
  let candidates = rows.filter((row) => (
    materialOf(row) === materialKey
    && Number(row.layers) === Number(target.layers)
    && priceOf(row) > 0
  ))
  if (config.modelType === 'fr4_segmented' && config.useSegments !== false) {
    const segment = segmentKey(target)
    const segmented = candidates.filter((row) => segmentKey(row) === segment)
    if (segmented.length >= config.guards.minLocalNeighbors) candidates = segmented
  }
  const nearest = candidates
    .map((row) => ({ row, distance: distance(target, row, config.guards) }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, config.neighbors || estimator.neighbors || 6)
  const local = nearest.filter((item) => item.distance <= config.guards.maxNeighborDistance)
  if (local.length < config.guards.minLocalNeighbors) return null
  let predicted
  if (
    config.modelType === 'aluminum_floor_area_quantity'
    || config.formula === 'floor_area_quantity'
  ) {
    const floor = Number(config.floorPriceCny || 0)
    const areaExponent = Number(config.guards.areaExponent)
    const quantityExponent = Number(config.guards.quantityExponent)
    const rates = local.map(({ row }) => (
      Math.max(priceOf(row) - floor, 0.01)
      / (areaOf(row) ** areaExponent)
      / (Number(row.quantity) ** quantityExponent)
    ))
    predicted = floor + median(rates)
      * (areaOf(target) ** areaExponent)
      * (quantity ** quantityExponent)
  } else {
    let weightedLog = 0
    let totalWeight = 0
    for (const item of local) {
      const weight = 1 / ((item.distance ** 2) + 0.005)
      weightedLog += Math.log(priceOf(item.row)) * weight
      totalWeight += weight
    }
    predicted = Math.exp(weightedLog / totalWeight)
  }
  const basisMedian = median(local.map((item) => priceOf(item.row)))
  const multiplier = basisMedian ? predicted / basisMedian : 1
  if (multiplier < 0.25 || multiplier > 4) return null
  return {
    jlcPriceCny: Number(predicted.toFixed(2)),
    averageDistance: Number((local.reduce((sum, item) => sum + item.distance, 0) / local.length).toFixed(4)),
    localCoverage: local.length,
    extrapolation: false,
    basis: local.map((item) => item.row),
  }
}

export function scoreRows(fitRows, estimator, holdoutRows) {
  const rows = []
  for (const target of holdoutRows) {
    const estimate = estimateV9(fitRows, estimator, target)
    const actual = priceOf(target)
    const relativeError = estimate && actual > 0
      ? Math.abs(estimate.jlcPriceCny - actual) / actual
      : null
    rows.push({ id: target.id, materialKey: materialOf(target), actual, estimate, relativeError })
  }
  return rows
}
