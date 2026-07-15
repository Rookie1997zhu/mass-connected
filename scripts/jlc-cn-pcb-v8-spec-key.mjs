/**
 * v8 PCB sample identity helpers: exact keys + neighbor-band anti-leakage.
 * Extends v7 protocol; v7 final acceptance is diagnostic_only and must not
 * enter v8 final acceptance.
 */
export {
  PROCESS_FIELDS,
  geometryKey,
  processKey,
  collectKeys,
  intersectKeys,
  assertDisjoint,
  areaBandMm2,
  quantityBand,
} from './jlc-cn-pcb-v7-spec-key.mjs'

import {
  areaBandMm2,
  assertDisjoint,
  collectKeys,
  geometryKey,
  processKey,
  quantityBand,
} from './jlc-cn-pcb-v7-spec-key.mjs'

export const DIAGNOSTIC_ROLES = new Set(['final_acceptance', 'v7_acceptance', 'diagnostic_only'])

export function neighborBandKey(sample) {
  const material = sample.materialKey || sample.material_key || 'fr4'
  const layers = Number(sample.layers)
  const width = Number(sample.widthMm ?? sample.width_mm)
  const height = Number(sample.heightMm ?? sample.height_mm)
  const area = width * height
  // Fine-grained near-neighbor bands: 1,000mm² area buckets and 5-piece
  // quantity steps. Broad small/mid/large bands are useful for modeling but
  // are too coarse for leakage detection because every split spans them.
  const areaBucket = Math.round(area / 1000)
  const quantityBucket = Math.round(Number(sample.quantity) / 5)
  return [
    material,
    layers,
    `a${areaBucket}`,
    `q${quantityBucket}`,
  ].join('|')
}

export function collectNeighborBands(rows) {
  return collectKeys(rows, neighborBandKey)
}

export function assertNeighborDisjoint(nameA, rowsA, nameB, rowsB, { hard = true } = {}) {
  return assertDisjoint(
    `${nameA}_neighbor`,
    collectNeighborBands(rowsA),
    `${nameB}_neighbor`,
    collectNeighborBands(rowsB),
    { hard },
  )
}

export function isDiagnosticOnly(row) {
  if (!row) return false
  if (row.diagnosticOnly === true || row.sampleRole === 'diagnostic_only') return true
  if (DIAGNOSTIC_ROLES.has(row.sampleRole) && String(row.samplingVersion || '').startsWith('v7')) {
    return true
  }
  const id = String(row.id || row.baseSampleId || '')
  return id.includes('V7-ACC')
}

export function markDiagnostic(rows, reason = 'v7_final_acceptance_do_not_train') {
  return (rows || []).map((row) => ({
    ...row,
    diagnosticOnly: true,
    sampleRole: 'diagnostic_only',
    diagnosticReason: reason,
  }))
}

export function rejectDiagnosticInAcceptance(rows) {
  const blocked = (rows || []).filter(isDiagnosticOnly)
  if (blocked.length) {
    const error = new Error(`v8 acceptance contains ${blocked.length} diagnostic/v7 samples`)
    error.blocked = blocked.slice(0, 20).map((row) => row.id)
    throw error
  }
  return true
}

export function fingerprintTargets(rows) {
  const keys = [...collectKeys(rows, processKey)].sort()
  let hash = 0
  const payload = keys.join('\n')
  for (let i = 0; i < payload.length; i += 1) {
    hash = ((hash << 5) - hash) + payload.charCodeAt(i)
    hash |= 0
  }
  return {
    count: keys.length,
    hash: `fnvish_${(hash >>> 0).toString(16)}`,
    sampleKeysHead: keys.slice(0, 5),
  }
}

export function assertFrozenFingerprint(current, frozen, { hard = true } = {}) {
  const ok = current?.hash && frozen?.hash && current.hash === frozen.hash && current.count === frozen.count
  const payload = { ok, current, frozen }
  if (!ok && hard) {
    const error = new Error('v8 acceptance fingerprint mismatch; refusing retune on same set')
    error.payload = payload
    throw error
  }
  return payload
}

export function splitIntegrityReport({
  fit = [],
  tuningHoldout = [],
  processHoldout = [],
  finalAcceptance = [],
  diagnostic = [],
} = {}) {
  rejectDiagnosticInAcceptance(finalAcceptance)
  const checks = [
    assertDisjoint('fit', collectKeys(fit, processKey), 'tuning_holdout', collectKeys(tuningHoldout, processKey), { hard: false }),
    assertDisjoint('fit', collectKeys(fit, processKey), 'process_holdout', collectKeys(processHoldout, processKey), { hard: false }),
    assertDisjoint('fit', collectKeys(fit, geometryKey), 'final_acceptance', collectKeys(finalAcceptance, geometryKey), { hard: false }),
    assertDisjoint('tuning_holdout', collectKeys(tuningHoldout, geometryKey), 'final_acceptance', collectKeys(finalAcceptance, geometryKey), { hard: false }),
    assertDisjoint('process_holdout', collectKeys(processHoldout, processKey), 'final_acceptance', collectKeys(finalAcceptance, processKey), { hard: false }),
    assertDisjoint('diagnostic_v7', collectKeys(diagnostic, geometryKey), 'final_acceptance', collectKeys(finalAcceptance, geometryKey), { hard: false }),
    assertNeighborDisjoint('fit', fit, 'final_acceptance', finalAcceptance, { hard: false }),
    assertNeighborDisjoint('tuning_holdout', tuningHoldout, 'final_acceptance', finalAcceptance, { hard: false }),
    assertNeighborDisjoint('process_holdout', processHoldout, 'final_acceptance', finalAcceptance, { hard: false }),
    assertNeighborDisjoint('diagnostic_v7', diagnostic, 'final_acceptance', finalAcceptance, { hard: false }),
  ]
  return {
    ok: checks.every((item) => item.ok),
    checks,
    fingerprint: fingerprintTargets(finalAcceptance),
    counts: {
      fit: fit.length,
      tuningHoldout: tuningHoldout.length,
      processHoldout: processHoldout.length,
      finalAcceptance: finalAcceptance.length,
      diagnostic: diagnostic.length,
    },
  }
}
