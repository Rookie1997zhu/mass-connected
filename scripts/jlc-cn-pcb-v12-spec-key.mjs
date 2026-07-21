/**
 * v12 data protocol. All v7-v11 final acceptance data is diagnostic-only.
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
  processKey,
} from './jlc-cn-pcb-v8-spec-key.mjs'

export function isDiagnosticOnly(row) {
  if (!row) return false
  if (row.diagnosticOnly === true || row.sampleRole === 'diagnostic_only') return true
  const id = String(row.id || row.baseSampleId || '')
  const reason = String(row.diagnosticReason || '')
  return /V(?:7|8|9|10|11)-ACC/.test(id)
    || /v(?:7|8|9|10|11)_final_acceptance_do_not_train/.test(reason)
    || [
      'v7-acceptance',
      'v8-acceptance',
      'v9-acceptance',
      'v10-acceptance',
      'v11-acceptance',
    ].includes(String(row.samplingVersion || ''))
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
    const error = new Error(`${splitName} contains ${blocked.length} v7-v11 diagnostic rows`)
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
  return Math.sqrt(
    Math.log(targetArea / fitArea) ** 2
    + (0.65 * Math.log(numeric(target, 'quantity') / numeric(fit, 'quantity'))) ** 2,
  )
}

export function supportEnvelopeReport(fitRows, finalRows, {
  minNeighbors = 2,
  maxDistance = 0.75,
} = {}) {
  const fit = (fitRows || []).filter((row) => !isDiagnosticOnly(row))
  const rows = (finalRows || []).map((target) => {
    const nearest = fit
      .filter((row) => (
        (row.materialKey || row.material_key) === (target.materialKey || target.material_key)
        && Number(row.layers) === Number(target.layers)
      ))
      .map((row) => ({ id: row.id, distance: supportDistance(target, row) }))
      .sort((left, right) => left.distance - right.distance)
    return {
      id: target.id,
      materialKey: target.materialKey || target.material_key,
      layers: Number(target.layers),
      neighborCount: nearest.filter((item) => item.distance <= maxDistance).length,
      nearest: nearest.slice(0, 4),
      ok: nearest.filter((item) => item.distance <= maxDistance).length >= minNeighbors,
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

export function runtimePreflightReport(fitRows, estimator, finalRows, estimate) {
  if (!estimator || typeof estimate !== 'function') {
    return { ok: false, reason: 'candidate_estimator_not_available', rows: [] }
  }
  const rows = (finalRows || []).map((target) => {
    const result = estimate(fitRows, estimator, target)
    return {
      id: target.id,
      materialKey: target.materialKey || target.material_key,
      ok: Boolean(result && Number(result.jlcPriceCny) > 0),
      localCoverage: result?.localCoverage ?? 0,
      averageDistance: result?.averageDistance ?? null,
    }
  })
  return {
    ok: rows.length > 0 && rows.every((row) => row.ok),
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
    assertDisjoint('fit', collectKeys(fit, processKey), 'tuning', collectKeys(tuningHoldout, processKey), { hard: false }),
    assertDisjoint('fit', collectKeys(fit, processKey), 'process', collectKeys(processHoldout, processKey), { hard: false }),
    assertDisjoint('fit', collectKeys(fit, geometryKey), 'final', collectKeys(finalAcceptance, geometryKey), { hard: false }),
    assertDisjoint('tuning', collectKeys(tuningHoldout, processKey), 'final', collectKeys(finalAcceptance, processKey), { hard: false }),
    assertDisjoint('process', collectKeys(processHoldout, processKey), 'final', collectKeys(finalAcceptance, processKey), { hard: false }),
    assertDisjoint('diagnostic', collectKeys(diagnostic, geometryKey), 'final', collectKeys(finalAcceptance, geometryKey), { hard: false }),
    assertNeighborDisjoint('fit', fit, 'final', finalAcceptance, { hard: false }),
    assertNeighborDisjoint('tuning', tuningHoldout, 'final', finalAcceptance, { hard: false }),
    assertNeighborDisjoint('process', processHoldout, 'final', finalAcceptance, { hard: false }),
    assertNeighborDisjoint('diagnostic', diagnostic, 'final', finalAcceptance, { hard: false }),
  ]
  const supportEnvelope = supportEnvelopeReport(fit, finalAcceptance)
  return {
    ok: checks.every((check) => check.ok) && supportEnvelope.ok,
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
    throw new Error(`v12 acceptance fingerprint already consumed: ${fingerprint.hash}`)
  }
  return result
}

export function verifyFrozenFingerprint(current, frozen) {
  return assertFrozenFingerprint(current, frozen, { hard: true })
}
