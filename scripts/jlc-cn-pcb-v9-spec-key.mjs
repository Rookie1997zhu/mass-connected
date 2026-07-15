/**
 * v9 PCB data protocol: reject all prior acceptance data, enforce split
 * isolation and require every final-acceptance target to remain inside a
 * locally supported fit envelope.
 */
export {
  PROCESS_FIELDS,
  geometryKey,
  processKey,
  collectKeys,
  intersectKeys,
  assertDisjoint,
  fingerprintTargets,
  assertFrozenFingerprint,
  neighborBandKey,
  assertNeighborDisjoint,
} from './jlc-cn-pcb-v8-spec-key.mjs'

import {
  assertDisjoint,
  assertFrozenFingerprint,
  assertNeighborDisjoint,
  collectKeys,
  fingerprintTargets,
  geometryKey,
  neighborBandKey,
  processKey,
} from './jlc-cn-pcb-v8-spec-key.mjs'

export function isDiagnosticOnly(row) {
  if (!row) return false
  if (row.diagnosticOnly === true || row.sampleRole === 'diagnostic_only') return true
  const id = String(row.id || row.baseSampleId || '')
  const reason = String(row.diagnosticReason || '')
  return /V[78]-ACC/.test(id)
    || /v[78]_final_acceptance_do_not_train/.test(reason)
    || ['v7-acceptance', 'v8-acceptance'].includes(String(row.samplingVersion || ''))
}

export function markDiagnostic(rows, reason = 'prior_final_acceptance_do_not_train') {
  return (rows || []).map((row) => ({
    ...row,
    diagnosticOnly: true,
    sampleRole: 'diagnostic_only',
    diagnosticReason: reason,
  }))
}

export function rejectDiagnostic(rows, splitName) {
  const blocked = (rows || []).filter(isDiagnosticOnly)
  if (blocked.length) {
    const error = new Error(`${splitName} contains ${blocked.length} v7/v8 diagnostic acceptance rows`)
    error.blocked = blocked.slice(0, 20).map((row) => row.id)
    throw error
  }
}

function numeric(row, camel, snake = camel) {
  return Number(row[camel] ?? row[snake])
}

function supportDistance(target, fit) {
  const targetArea = numeric(target, 'widthMm', 'width_mm') * numeric(target, 'heightMm', 'height_mm')
  const fitArea = numeric(fit, 'widthMm', 'width_mm') * numeric(fit, 'heightMm', 'height_mm')
  const targetQuantity = numeric(target, 'quantity')
  const fitQuantity = numeric(fit, 'quantity')
  return Math.sqrt(
    Math.log(targetArea / fitArea) ** 2
    + (0.65 * Math.log(targetQuantity / fitQuantity)) ** 2,
  )
}

export function supportEnvelopeReport(fitRows, acceptanceRows, {
  minNeighbors = 2,
  maxDistance = 0.75,
} = {}) {
  const uniqueFit = [...new Map((fitRows || [])
    .filter((row) => !isDiagnosticOnly(row))
    .map((row) => [processKey(row), row])).values()]
  const rows = (acceptanceRows || []).map((target) => {
    const candidates = uniqueFit
      .filter((fit) => (
        (fit.materialKey || fit.material_key) === (target.materialKey || target.material_key)
        && Number(fit.layers) === Number(target.layers)
      ))
      .map((fit) => ({ id: fit.id, distance: supportDistance(target, fit) }))
      .sort((a, b) => a.distance - b.distance)
    const qualified = candidates.filter((item) => item.distance <= maxDistance)
    return {
      id: target.id,
      materialKey: target.materialKey || target.material_key,
      layers: Number(target.layers),
      neighborCount: qualified.length,
      nearest: candidates.slice(0, Math.max(minNeighbors, 4)),
      ok: qualified.length >= minNeighbors,
    }
  })
  return {
    ok: rows.every((row) => row.ok),
    minNeighbors,
    maxDistance,
    failed: rows.filter((row) => !row.ok),
    rows,
  }
}

export function splitIntegrityReport({
  fit = [],
  tuningHoldout = [],
  processHoldout = [],
  finalAcceptance = [],
  diagnostic = [],
} = {}) {
  rejectDiagnostic(fit, 'fit')
  rejectDiagnostic(tuningHoldout, 'tuning_holdout')
  rejectDiagnostic(processHoldout, 'process_holdout')
  rejectDiagnostic(finalAcceptance, 'final_acceptance')
  const checks = [
    assertDisjoint('fit', collectKeys(fit, processKey), 'tuning_holdout', collectKeys(tuningHoldout, processKey), { hard: false }),
    assertDisjoint('fit', collectKeys(fit, processKey), 'process_holdout', collectKeys(processHoldout, processKey), { hard: false }),
    assertDisjoint('fit', collectKeys(fit, geometryKey), 'final_acceptance', collectKeys(finalAcceptance, geometryKey), { hard: false }),
    assertDisjoint('tuning_holdout', collectKeys(tuningHoldout, processKey), 'final_acceptance', collectKeys(finalAcceptance, processKey), { hard: false }),
    assertDisjoint('process_holdout', collectKeys(processHoldout, processKey), 'final_acceptance', collectKeys(finalAcceptance, processKey), { hard: false }),
    assertDisjoint('diagnostic_v7_v8', collectKeys(diagnostic, geometryKey), 'final_acceptance', collectKeys(finalAcceptance, geometryKey), { hard: false }),
    assertNeighborDisjoint('fit', fit, 'final_acceptance', finalAcceptance, { hard: false }),
    assertNeighborDisjoint('tuning_holdout', tuningHoldout, 'final_acceptance', finalAcceptance, { hard: false }),
    assertNeighborDisjoint('process_holdout', processHoldout, 'final_acceptance', finalAcceptance, { hard: false }),
    assertNeighborDisjoint('diagnostic_v7_v8', diagnostic, 'final_acceptance', finalAcceptance, { hard: false }),
  ]
  const supportEnvelope = supportEnvelopeReport(fit, finalAcceptance)
  return {
    ok: checks.every((item) => item.ok) && supportEnvelope.ok,
    checks,
    supportEnvelope,
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

export function assertUnconsumedFingerprint(fingerprint, consumption, { hard = true } = {}) {
  const consumed = Boolean(
    fingerprint?.hash
    && consumption?.fingerprint === fingerprint.hash
    && consumption?.consumed === true,
  )
  const result = { ok: !consumed, consumed, fingerprint: fingerprint?.hash || null }
  if (consumed && hard) {
    throw new Error(`v9 acceptance fingerprint already consumed: ${fingerprint.hash}`)
  }
  return result
}

export function verifyFrozenFingerprint(current, frozen) {
  return assertFrozenFingerprint(current, frozen, { hard: true })
}
