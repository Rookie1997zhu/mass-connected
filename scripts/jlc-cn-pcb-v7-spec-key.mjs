/** Shared PCB quote sample identity helpers for v7 anti-leakage splits. */

export const PROCESS_FIELDS = [
  'boardThickness',
  'solderColor',
  'surfaceFinish',
  'copperThickness',
  'solderMaskCoverage',
  'panelDesignCount',
]

/** Geometry + qty identity used by exact/estimator tables. */
export function geometryKey(sample) {
  return [
    sample.materialKey || sample.material_key || 'fr4',
    Number(sample.layers),
    Number(sample.widthMm ?? sample.width_mm),
    Number(sample.heightMm ?? sample.height_mm),
    Number(sample.quantity),
  ].join('|')
}

/** Full process identity for fit/holdout/acceptance exclusion. */
export function processKey(sample) {
  return [
    geometryKey(sample),
    ...PROCESS_FIELDS.map((field) => String(sample[field] || '')),
  ].join('|')
}

export function collectKeys(rows, keyFn = geometryKey) {
  const keys = new Set()
  for (const row of rows || []) {
    if (!row) continue
    keys.add(keyFn(row))
  }
  return keys
}

export function intersectKeys(a, b) {
  const out = []
  for (const key of a) {
    if (b.has(key)) out.push(key)
  }
  return out.sort()
}

export function assertDisjoint(nameA, keysA, nameB, keysB, { hard = true } = {}) {
  const overlap = intersectKeys(keysA, keysB)
  const payload = {
    ok: overlap.length === 0,
    left: nameA,
    right: nameB,
    overlapCount: overlap.length,
    overlap: overlap.slice(0, 30),
  }
  if (!payload.ok && hard) {
    const error = new Error(
      `sample split leak: ${nameA} ∩ ${nameB} = ${overlap.length} keys`,
    )
    error.payload = payload
    throw error
  }
  return payload
}

export function areaBandMm2(widthMm, heightMm) {
  const area = Number(widthMm) * Number(heightMm)
  if (area <= 5000) return 'small'
  if (area <= 15000) return 'mid'
  return 'large'
}

export function quantityBand(quantity) {
  const qty = Number(quantity)
  if (qty <= 20) return 'low'
  if (qty <= 75) return 'mid'
  return 'high'
}
