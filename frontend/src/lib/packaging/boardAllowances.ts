export type FluteType = 'e' | 'b' | 'c' | 'bc' | 'none'
export type MaterialType = 'corrugated' | 'white_card' | 'kraft' | 'coated'

export interface BoardAllowances {
  internalLw: number
  internalH: number
  externalLw: number
  externalH: number
}

const FLUTE_TABLE: Record<
  FluteType,
  { refThickness: number; internalLw: number; internalH: number; externalLw: number; externalH: number }
> = {
  e: { refThickness: 1.5, internalLw: 2, internalH: 4, externalLw: 1, externalH: 2 },
  b: { refThickness: 3, internalLw: 4, internalH: 8, externalLw: 2, externalH: 4 },
  c: { refThickness: 4, internalLw: 5, internalH: 10, externalLw: 3, externalH: 5 },
  bc: { refThickness: 7, internalLw: 8, internalH: 16, externalLw: 4, externalH: 8 },
  none: { refThickness: 0.5, internalLw: 0.5, internalH: 1, externalLw: 0.25, externalH: 0.5 },
}

const MATERIAL_DEFAULT_FLUTE: Record<MaterialType, FluteType> = {
  corrugated: 'b',
  white_card: 'none',
  kraft: 'none',
  coated: 'none',
}

function scaleAllowance(base: number, refThickness: number, actualThickness: number): number {
  const ref = Math.max(0.1, refThickness)
  const actual = Math.max(0.1, actualThickness)
  return base * (actual / ref)
}

export function normalizeFluteType(fluteType?: string | null, materialType?: string | null): FluteType {
  const flute = String(fluteType || '').toLowerCase()
  if (flute in FLUTE_TABLE) return flute as FluteType
  const material = String(materialType || '').toLowerCase() as MaterialType
  return MATERIAL_DEFAULT_FLUTE[material] || 'b'
}

export function boardTypeToFlute(boardType: string): FluteType {
  const map: Record<string, FluteType> = { E: 'e', B: 'b', C: 'c', 白卡: 'none' }
  return map[boardType] || 'b'
}

export function resolveBoardAllowances(
  thicknessMm: number,
  options?: {
    fluteType?: string | null
    materialType?: string | null
    templateAllowances?: Record<string, number> | null
  },
): BoardAllowances {
  const overrides = options?.templateAllowances || {}
  if (
    overrides.internal_lw != null &&
    overrides.internal_h != null &&
    overrides.external_lw != null &&
    overrides.external_h != null
  ) {
    return {
      internalLw: Number(overrides.internal_lw),
      internalH: Number(overrides.internal_h),
      externalLw: Number(overrides.external_lw),
      externalH: Number(overrides.external_h),
    }
  }

  const flute = normalizeFluteType(options?.fluteType, options?.materialType)
  const base = FLUTE_TABLE[flute]
  const t = Math.max(0.1, thicknessMm)
  const result: BoardAllowances = {
    internalLw: scaleAllowance(base.internalLw, base.refThickness, t),
    internalH: scaleAllowance(base.internalH, base.refThickness, t),
    externalLw: scaleAllowance(base.externalLw, base.refThickness, t),
    externalH: scaleAllowance(base.externalH, base.refThickness, t),
  }

  if (overrides.internal_lw != null) result.internalLw = Number(overrides.internal_lw)
  if (overrides.internal_h != null) result.internalH = Number(overrides.internal_h)
  if (overrides.external_lw != null) result.externalLw = Number(overrides.external_lw)
  if (overrides.external_h != null) result.externalH = Number(overrides.external_h)
  return result
}

export function validateTemplateLimits(
  length: number,
  width: number,
  height: number,
  limits?: {
    minLengthMm?: number | null
    maxLengthMm?: number | null
    minWidthMm?: number | null
    maxWidthMm?: number | null
    minHeightMm?: number | null
    maxHeightMm?: number | null
  },
): string | null {
  if (!limits) return null
  const checks: Array<[number, number | null | undefined, number | null | undefined, string]> = [
    [length, limits.minLengthMm, limits.maxLengthMm, '长'],
    [width, limits.minWidthMm, limits.maxWidthMm, '宽'],
    [height, limits.minHeightMm, limits.maxHeightMm, '高'],
  ]
  for (const [value, min, max, label] of checks) {
    if (min != null && value < min) return `${label}不能小于 ${min}mm`
    if (max != null && value > max) return `${label}不能超过 ${max}mm`
  }
  return null
}
