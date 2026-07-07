import type { BoxCode } from './fefcoCatalog'
export type { BoxCode } from './fefcoCatalog'

export type Unit = 'mm' | 'in'
export type DimensionType = 'internal' | 'external' | 'manufacturing'
export type BoardType = 'E' | 'B' | 'C' | '白卡'

export interface BoxParams {
  boxCode: BoxCode
  length: number
  width: number
  height: number
  thickness: number
  unit: Unit
  dimensionType: DimensionType
  boardType: BoardType
  quantity: number
  printColors: number
}

export interface SizeTriple {
  length: number
  width: number
  height: number
}

export interface DielineGeometry {
  boxCode: BoxCode
  manufacturing: SizeTriple
  internal: SizeTriple
  external: SizeTriple
  thicknessMm: number
  glueTabMm: number
  blankWidthMm: number
  blankHeightMm: number
  unfoldAreaM2: number
}

export type LineKind = 'cut' | 'crease' | 'bleed'

export interface LineSegment {
  x1: number
  y1: number
  x2: number
  y2: number
  kind: LineKind
}

export interface DielinePreview {
  geometry: DielineGeometry
  segments: LineSegment[]
  viewBox: string
  previewMode?: 'detailed' | 'blank'
}

export type DimField = 'length' | 'width' | 'height'

export interface DimAnnotation {
  field: DimField
  axis: 'horizontal' | 'vertical'
  labelX: number
  labelY: number
  labelWidth: number
  labelHeight: number
  fontSize: number
  arrowSvg: string
  displayValue: number
  /** 标尺线中心（与 label 对齐） */
  lineX: number
  lineY: number
}
