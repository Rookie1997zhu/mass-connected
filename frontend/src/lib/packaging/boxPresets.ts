import type { BoardType, DimensionType, Unit } from './types'
import type { BoxCode } from './fefcoCatalog'

export interface BoxPreset {
  length: number
  width: number
  height: number
  thickness: number
  unit: Unit
  dimensionType: DimensionType
  boardType: BoardType
}

/** FEFCO 0201 参考样例（制造尺寸 434×214×278 mm，B 楞 3mm） */
export const REFERENCE_0201: BoxPreset = {
  length: 434,
  width: 214,
  height: 278,
  thickness: 3,
  unit: 'mm',
  dimensionType: 'manufacturing',
  boardType: 'B',
}

export const BOX_PRESETS: Partial<Record<BoxCode, BoxPreset>> = {
  '0201': REFERENCE_0201,
}

export function getBoxPreset(code: string): BoxPreset | undefined {
  return BOX_PRESETS[code as BoxCode]
}
