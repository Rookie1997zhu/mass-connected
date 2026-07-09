import makerjs from 'makerjs'
import { boardTypeToFlute, resolveBoardAllowances, validateTemplateLimits } from './boardAllowances'
import { build0427Segments, compute0427BlankSize } from './dieline0427'
import { buildTuckEndSegments } from './dieline0713'
import { buildAutoLockBottomSegments } from './dieline0716'
import { buildFoldingShippingSegments } from './dielineFoldingShipping'
import {
  addBleedRect,
  addHorizontalCutWithGaps,
  addSegment,
  addVerticalSlotRounded,
  slotWidthFromThickness,
} from './dielineUtils'
import { getBoxTemplate, type DielineTemplateAsset } from './fefcoCatalog'
import {
  buildParametricDimensionAnnotations,
  buildParametricSegments,
  hasMappedParametricAsset,
  viewBoxFromSegments,
} from './parametricTemplate'
import type {
  BoxParams,
  DimAnnotation,
  DimLine,
  DielineGeometry,
  DielinePreview,
  DimensionType,
  DimField,
  EngineKey,
  LineKind,
  LineSegment,
  SizeTriple,
  Unit,
} from './types'

export const PARAMETRIC_ASSET_REQUIRED = 'Parametric asset required for preview'

const MM_PER_IN = 25.4
const DEFAULT_GLUE_TAB_MM = 25
const MIN_DIM_MM = 10
const MAX_DIM_MM = 2000

export function toMm(value: number, unit: Unit): number {
  return unit === 'in' ? value * MM_PER_IN : value
}

export function fromMm(value: number, unit: Unit): number {
  return unit === 'in' ? value / MM_PER_IN : value
}

function boardAllowances(
  thicknessMm: number,
  template?: ReturnType<typeof getBoxTemplate>,
  boardType?: string,
) {
  const fluteType = boardType ? boardTypeToFlute(boardType) : template?.fluteType
  const materialType = template?.materialType
  return resolveBoardAllowances(thicknessMm, {
    fluteType,
    materialType,
    templateAllowances: template?.allowances,
  })
}

function toManufacturingMm(
  length: number,
  width: number,
  height: number,
  thicknessMm: number,
  dimensionType: DimensionType,
  template?: ReturnType<typeof getBoxTemplate>,
  boardType?: string,
): SizeTriple {
  const allow = boardAllowances(thicknessMm, template, boardType)
  if (dimensionType === 'manufacturing') {
    return { length, width, height }
  }
  if (dimensionType === 'internal') {
    return {
      length: length + allow.internalLw,
      width: width + allow.internalLw,
      height: height + allow.internalH,
    }
  }
  return {
    length: Math.max(MIN_DIM_MM, length - allow.externalLw),
    width: Math.max(MIN_DIM_MM, width - allow.externalLw),
    height: Math.max(MIN_DIM_MM, height - allow.externalH),
  }
}

function sizeTripleFromManufacturing(
  m: SizeTriple,
  thicknessMm: number,
  template?: ReturnType<typeof getBoxTemplate>,
  boardType?: string,
): { internal: SizeTriple; external: SizeTriple } {
  const allow = boardAllowances(thicknessMm, template, boardType)
  return {
    internal: {
      length: m.length - allow.internalLw,
      width: m.width - allow.internalLw,
      height: m.height - allow.internalH,
    },
    external: {
      length: m.length + allow.externalLw,
      width: m.width + allow.externalLw,
      height: m.height + allow.externalH,
    },
  }
}

function computeBlankSize(engineKey: EngineKey, m: SizeTriple, glueTab: number, thicknessMm = 1.5): { blankWidthMm: number; blankHeightMm: number } {
  const L = m.length
  const W = m.width
  const H = m.height
  switch (engineKey) {
    case 'slotted_rsc':
    case 'folding_shipping':
      return { blankWidthMm: 2 * (L + W) + glueTab, blankHeightMm: W + H }
    case 'mailer_folder': {
      const blank = compute0427BlankSize(L, W, H, thicknessMm)
      return { blankWidthMm: blank.blankWidthMm, blankHeightMm: blank.blankHeightMm }
    }
    case 'tuck_end':
      return { blankWidthMm: 2 * (L + W) + glueTab, blankHeightMm: 2 * H + W }
    case 'auto_lock_bottom':
      return { blankWidthMm: 2 * (L + W) + glueTab, blankHeightMm: 2 * H + 1.25 * W }
    default:
      throw new Error(`Unsupported engine: ${engineKey}`)
  }
}

export function computeGeometry(params: BoxParams, glueTabMm?: number): DielineGeometry {
  const template = getBoxTemplate(params.boxCode)
  if (!template?.previewEnabled) {
    throw new Error('Box type preview not available yet')
  }

  const limitError = validateTemplateLimits(params.length, params.width, params.height, {
    minLengthMm: template.minLengthMm,
    maxLengthMm: template.maxLengthMm,
    minWidthMm: template.minWidthMm,
    maxWidthMm: template.maxWidthMm,
    minHeightMm: template.minHeightMm,
    maxHeightMm: template.maxHeightMm,
  })
  if (limitError) {
    throw new Error(limitError)
  }

  const thicknessMm = Math.max(0.1, toMm(params.thickness, params.unit))
  const input = {
    length: toMm(params.length, params.unit),
    width: toMm(params.width, params.unit),
    height: toMm(params.height, params.unit),
  }

  if (input.length < MIN_DIM_MM || input.width < MIN_DIM_MM || input.height < MIN_DIM_MM) {
    throw new Error('Dimensions must be at least 10mm')
  }
  if (input.length > MAX_DIM_MM || input.width > MAX_DIM_MM || input.height > MAX_DIM_MM) {
    throw new Error('Dimensions cannot exceed 2000mm')
  }

  const manufacturing = toManufacturingMm(
    input.length,
    input.width,
    input.height,
    thicknessMm,
    params.dimensionType,
    template,
    params.boardType,
  )
  const { internal, external } = sizeTripleFromManufacturing(
    manufacturing,
    thicknessMm,
    template,
    params.boardType,
  )
  const glueTab = Math.max(15, glueTabMm ?? template.defaultGlueTabMm ?? DEFAULT_GLUE_TAB_MM)
  const { blankWidthMm, blankHeightMm } = computeBlankSize(template.engineKey, manufacturing, glueTab, thicknessMm)
  const unfoldAreaM2 = (blankWidthMm / 1000) * (blankHeightMm / 1000)

  return {
    boxCode: params.boxCode,
    manufacturing,
    internal,
    external,
    thicknessMm,
    glueTabMm: glueTab,
    blankWidthMm,
    blankHeightMm,
    unfoldAreaM2,
  }
}

export function build0201Segments(geo: DielineGeometry): LineSegment[] {
  const L = geo.manufacturing.length
  const W = geo.manufacturing.width
  const H = geo.manufacturing.height
  const glue = geo.glueTabMm

  const xGlue = 0
  const xL1 = glue
  const xW1 = glue + L
  const xL2 = glue + L + W
  const xW2 = glue + L + W + L
  const xEnd = glue + 2 * L + 2 * W

  const yTop = 0
  const yBodyTop = W / 2
  const yBodyBot = W / 2 + H
  const yBot = W + H

  const slotW = slotWidthFromThickness(geo.thicknessMm)
  const half = slotW / 2
  const slitXs = [xW1, xL2, xW2]
  const slitGaps = slitXs.map((x) => [x - half, x + half] as [number, number])

  const segments: LineSegment[] = []

  addBleedRect(segments, xEnd, yBot)

  // 外轮廓 cut（顶底边在槽位留缝）
  addHorizontalCutWithGaps(segments, yBot, xL1, xEnd, slitGaps)
  addSegment(segments, xEnd, yBot, xEnd, yTop, 'cut')
  addHorizontalCutWithGaps(segments, yTop, xL1, xEnd, slitGaps)
  addSegment(segments, xL1, yTop, xL1, yBodyTop, 'cut')
  addSegment(segments, xL1, yBodyTop, xGlue, yBodyTop, 'cut')
  addSegment(segments, xGlue, yBodyTop, xGlue, yBodyBot, 'cut')
  addSegment(segments, xGlue, yBodyBot, xL1, yBodyBot, 'cut')
  addSegment(segments, xL1, yBodyBot, xL1, yBot, 'cut')

  // 摇盖开槽（圆角竖槽，宽约板厚）
  for (const xi of slitXs) {
    addVerticalSlotRounded(segments, xi, yTop, yBodyTop, slotW, geo.thicknessMm)
    addVerticalSlotRounded(segments, xi, yBodyBot, yBot, slotW, geo.thicknessMm)
  }

  // 竖向压线（4 面板折痕）
  for (const xi of [xL1, xW1, xL2, xW2]) {
    addSegment(segments, xi, yBodyTop, xi, yBodyBot, 'crease')
  }

  // 横向压线（body 与摇盖分界）
  addSegment(segments, xL1, yBodyTop, xEnd, yBodyTop, 'crease')
  addSegment(segments, xL1, yBodyBot, xEnd, yBodyBot, 'crease')

  return segments
}

function buildBlankOutlineSegments(totalW: number, totalH: number): LineSegment[] {
  const segments: LineSegment[] = []
  addBleedRect(segments, totalW, totalH)
  addSegment(segments, 0, 0, totalW, 0, 'cut')
  addSegment(segments, totalW, 0, totalW, totalH, 'cut')
  addSegment(segments, totalW, totalH, 0, totalH, 'cut')
  addSegment(segments, 0, totalH, 0, 0, 'cut')
  addSegment(segments, totalW / 2, 0, totalW / 2, totalH, 'crease')
  addSegment(segments, 0, totalH / 2, totalW, totalH / 2, 'crease')
  return segments
}

export function buildPreview(params: BoxParams): DielinePreview {
  const template = getBoxTemplate(params.boxCode)
  if (!template) {
    throw new Error(`Unknown FEFCO box: ${params.boxCode}`)
  }
  if (!template.previewEnabled) {
    throw new Error('Box type preview not available yet')
  }

  const geometry = computeGeometry(params)

  if (hasMappedParametricAsset(template.activeParametricAsset)) {
    const segments = buildParametricSegments(template.activeParametricAsset, geometry)
    if (segments.length) {
      const xs = segments.flatMap((seg) => [seg.x1, seg.x2])
      const ys = segments.flatMap((seg) => [seg.y1, seg.y2])
      const blankWidthMm = Math.max(...xs) - Math.min(...xs)
      const blankHeightMm = Math.max(...ys) - Math.min(...ys)
      return {
        geometry: {
          ...geometry,
          blankWidthMm,
          blankHeightMm,
          unfoldAreaM2: (blankWidthMm * blankHeightMm) / 1_000_000,
        },
        segments,
        viewBox: viewBoxFromSegments(segments),
        previewMode: 'detailed',
        source: 'parametric',
      }
    }
  }

  throw new Error(PARAMETRIC_ASSET_REQUIRED)
}

function computePreviewViewBox(geometry: DielineGeometry): string {
  const padSide = Math.max(30, geometry.blankWidthMm * 0.03)
  const padTop = Math.max(24, geometry.blankHeightMm * 0.03)
  const padBottom = Math.max(36, geometry.blankHeightMm * 0.05)
  const w = geometry.blankWidthMm + padSide * 2
  const h = geometry.blankHeightMm + padTop + padBottom
  return `${-padSide} ${-padTop} ${w} ${h}`
}

/** 屏幕像素线宽（配合 vector-effect=non-scaling-stroke） */
const STROKE_PX: Record<LineKind, { color: string; dash?: string; width: number; linecap: 'butt' | 'square' }> = {
  bleed: { color: '#22c55e', width: 1, linecap: 'butt' },
  cut: { color: '#2563eb', width: 1.2, linecap: 'butt' },
  crease: { color: '#ef4444', dash: '6 4', width: 1, linecap: 'butt' },
}

const DIM_COLOR = '#2563eb'
const PARAM_DIM_COLOR = '#f59e0b'

const DIM_LINE_BASE =
  `stroke="${DIM_COLOR}" stroke-width="1.5" vector-effect="non-scaling-stroke" shape-rendering="geometricPrecision"`

const PARAM_DIM_LINE_BASE =
  `stroke="${PARAM_DIM_COLOR}" stroke-width="1.5" vector-effect="non-scaling-stroke" shape-rendering="geometricPrecision"`

const PARAM_DIM_EXT_LINE_BASE =
  `stroke="${PARAM_DIM_COLOR}" stroke-width="1" vector-effect="non-scaling-stroke" shape-rendering="geometricPrecision"`

export interface ContentBbox {
  minX: number
  minY: number
  maxX: number
  maxY: number
}

function roundCoord(value: number): number {
  return Math.round(value * 10000) / 10000
}

export function parseViewBoxString(viewBox: string): ContentBbox {
  const parts = String(viewBox).trim().split(/\s+/).map(Number)
  if (parts.length !== 4 || parts.some((value) => !Number.isFinite(value))) {
    return { minX: 0, minY: 0, maxX: 100, maxY: 100 }
  }
  return {
    minX: parts[0],
    minY: parts[1],
    maxX: parts[0] + parts[2],
    maxY: parts[1] + parts[3],
  }
}

export function contentBboxFromSegments(segments: LineSegment[]): ContentBbox {
  if (!segments.length) return { minX: 0, minY: 0, maxX: 100, maxY: 100 }
  const xs = segments.flatMap((seg) => [seg.x1, seg.x2])
  const ys = segments.flatMap((seg) => [seg.y1, seg.y2])
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  }
}

function mergeExtents(...boxes: ContentBbox[]): ContentBbox {
  if (!boxes.length) return { minX: 0, minY: 0, maxX: 100, maxY: 100 }
  return {
    minX: Math.min(...boxes.map((box) => box.minX)),
    minY: Math.min(...boxes.map((box) => box.minY)),
    maxX: Math.max(...boxes.map((box) => box.maxX)),
    maxY: Math.max(...boxes.map((box) => box.maxY)),
  }
}

function labelExtents(ann: Pick<DimAnnotation, 'labelX' | 'labelY' | 'labelWidth' | 'labelHeight'>): ContentBbox {
  return {
    minX: ann.labelX - ann.labelWidth / 2,
    minY: ann.labelY - ann.labelHeight / 2,
    maxX: ann.labelX + ann.labelWidth / 2,
    maxY: ann.labelY + ann.labelHeight / 2,
  }
}

export function formatViewBox(box: ContentBbox, pad = 0): string {
  const width = Math.max(10, box.maxX - box.minX + pad * 2)
  const height = Math.max(10, box.maxY - box.minY + pad * 2)
  return `${roundCoord(box.minX - pad)} ${roundCoord(box.minY - pad)} ${roundCoord(width)} ${roundCoord(height)}`
}

export function computeDimViewBox(preview: DielinePreview, annotations: DimAnnotation[]): string {
  const base = parseViewBoxString(preview.viewBox)
  if (!annotations.length) return preview.viewBox
  const merged = mergeExtents(base, ...annotations.map((ann) => ann.extents))
  const span = Math.max(merged.maxX - merged.minX, merged.maxY - merged.minY)
  const pad = Math.max(12, span * 0.02)
  return formatViewBox(merged, pad)
}

function buildParamDimLine(x1: number, y1: number, x2: number, y2: number, withArrows = true): string {
  const markers = withArrows ? ' marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"' : ''
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" ${PARAM_DIM_LINE_BASE}${markers} />`
}

function buildParamExtLine(x1: number, y1: number, x2: number, y2: number): string {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" ${PARAM_DIM_EXT_LINE_BASE} />`
}

function buildHorizDimLine(x1: number, x2: number, y: number, gapHalf: number): string {
  void gapHalf
  return `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" ${DIM_LINE_BASE} marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)" />`
}

function buildVertDimLine(x: number, y1: number, y2: number, gapHalf: number): string {
  void gapHalf
  return `<line x1="${x}" y1="${y1}" x2="${x}" y2="${y2}" ${DIM_LINE_BASE} marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)" />`
}

function dimTextGapHalf(fontSize: number, labelWidth: number): number {
  return Math.max(fontSize * 0.9, labelWidth * 0.42)
}

function renderLineSvg(seg: LineSegment): string {
  const style = STROKE_PX[seg.kind]
  const dash = style.dash ? ` stroke-dasharray="${style.dash}"` : ''
  return `<line x1="${seg.x1}" y1="${seg.y1}" x2="${seg.x2}" y2="${seg.y2}" stroke="${style.color}" stroke-width="${style.width}" vector-effect="non-scaling-stroke" shape-rendering="geometricPrecision" stroke-linecap="${style.linecap}"${dash} />`
}

function dimLabelFontSize(geometry: DielineGeometry): number {
  return Math.max(12, geometry.blankWidthMm * 0.011)
}

function dimValueFromGeometry(
  geometry: DielineGeometry,
  field: DimField,
  dimensionType: DimensionType,
): number {
  const triple =
    dimensionType === 'internal'
      ? geometry.internal
      : dimensionType === 'external'
        ? geometry.external
        : geometry.manufacturing
  return triple[field]
}

function dimLabelSize(fontSize: number): { labelWidth: number; labelHeight: number } {
  return { labelWidth: fontSize * 4.8, labelHeight: fontSize * 1.35 }
}

function dimLine(x1: number, y1: number, x2: number, y2: number, role: DimLine['role']): DimLine {
  return { x1, y1, x2, y2, role }
}

function makeHorizontalDimAnnotation(
  field: DimField,
  geometry: DielineGeometry,
  unit: Unit,
  dimensionType: DimensionType,
  x1: number,
  x2: number,
  y: number,
  labelY: number,
  labelWidth: number,
  labelHeight: number,
  fontSize: number,
  gapHalf: number,
): DimAnnotation {
  const ann = {
    field,
    axis: 'horizontal' as const,
    labelX: (x1 + x2) / 2,
    labelY,
    lineX: (x1 + x2) / 2,
    lineY: y,
    labelWidth,
    labelHeight,
    fontSize,
    arrowSvg: buildHorizDimLine(x1, x2, y, gapHalf),
    dimLines: [dimLine(x1, y, x2, y, 'dimension')],
    displayValue: fromMm(dimValueFromGeometry(geometry, field, dimensionType), unit),
    extents: { minX: Math.min(x1, x2), minY: Math.min(y, labelY) - labelHeight / 2, maxX: Math.max(x1, x2), maxY: Math.max(y, labelY) + labelHeight / 2 },
  }
  ann.extents = mergeExtents({ minX: Math.min(x1, x2), minY: y, maxX: Math.max(x1, x2), maxY: y }, labelExtents(ann))
  return ann
}

function makeVerticalDimAnnotation(
  field: DimField,
  geometry: DielineGeometry,
  unit: Unit,
  dimensionType: DimensionType,
  x: number,
  y1: number,
  y2: number,
  labelX: number,
  labelWidth: number,
  labelHeight: number,
  fontSize: number,
  gapHalf: number,
): DimAnnotation {
  const ann = {
    field,
    axis: 'vertical' as const,
    labelX,
    labelY: (y1 + y2) / 2,
    lineX: x,
    lineY: (y1 + y2) / 2,
    labelWidth,
    labelHeight,
    fontSize,
    arrowSvg: buildVertDimLine(x, y1, y2, gapHalf),
    dimLines: [dimLine(x, y1, x, y2, 'dimension')],
    displayValue: fromMm(dimValueFromGeometry(geometry, field, dimensionType), unit),
    extents: { minX: Math.min(x, labelX) - labelWidth / 2, minY: Math.min(y1, y2), maxX: Math.max(x, labelX) + labelWidth / 2, maxY: Math.max(y1, y2) },
  }
  ann.extents = mergeExtents({ minX: x, minY: Math.min(y1, y2), maxX: x, maxY: Math.max(y1, y2) }, labelExtents(ann))
  return ann
}

function parametricDimOffset(fontSize: number, contentBbox: ContentBbox): number {
  const span = Math.max(contentBbox.maxX - contentBbox.minX, contentBbox.maxY - contentBbox.minY)
  return Math.max(12, fontSize * 1.15, span * 0.03)
}

function makeConfiguredDimAnnotation(
  ann: ReturnType<typeof buildParametricDimensionAnnotations>[number],
  geometry: DielineGeometry,
  unit: Unit,
  dimensionType: DimensionType,
  contentBbox: ContentBbox,
): DimAnnotation {
  const fontSize = dimLabelFontSize(geometry)
  const { labelWidth, labelHeight } = dimLabelSize(fontSize)
  const offset = parametricDimOffset(fontSize, contentBbox)
  const anchorX1 = ann.x1
  const anchorY1 = ann.y1
  const anchorX2 = ann.x2
  const anchorY2 = ann.y2

  if (ann.axis === 'horizontal') {
    const anchorY = (anchorY1 + anchorY2) / 2
    const centerY = (contentBbox.minY + contentBbox.maxY) / 2
    const outward = anchorY <= centerY ? -1 : 1
    const dimLineY = anchorY + outward * offset
    const labelOffset = outward * (fontSize * 0.95 + labelHeight * 0.35)
    const labelY = dimLineY + labelOffset
    const dimLines: DimLine[] = [
      dimLine(anchorX1, anchorY1, anchorX1, dimLineY, 'extension'),
      dimLine(anchorX2, anchorY2, anchorX2, dimLineY, 'extension'),
      dimLine(anchorX1, dimLineY, anchorX2, dimLineY, 'dimension'),
    ]
    const arrowSvg = [
      buildParamExtLine(anchorX1, anchorY1, anchorX1, dimLineY),
      buildParamExtLine(anchorX2, anchorY2, anchorX2, dimLineY),
      buildParamDimLine(anchorX1, dimLineY, anchorX2, dimLineY),
    ].join('')
    const result: DimAnnotation = {
      field: ann.field,
      axis: 'horizontal',
      labelX: (anchorX1 + anchorX2) / 2,
      labelY,
      lineX: (anchorX1 + anchorX2) / 2,
      lineY: dimLineY,
      labelWidth,
      labelHeight,
      fontSize,
      arrowSvg,
      dimLines,
      displayValue: fromMm(dimValueFromGeometry(geometry, ann.field, dimensionType), unit),
      extents: { minX: 0, minY: 0, maxX: 0, maxY: 0 },
    }
    result.extents = mergeExtents(
      { minX: Math.min(anchorX1, anchorX2), minY: Math.min(anchorY1, anchorY2, dimLineY), maxX: Math.max(anchorX1, anchorX2), maxY: Math.max(anchorY1, anchorY2, dimLineY) },
      labelExtents(result),
    )
    return result
  }

  const anchorX = (anchorX1 + anchorX2) / 2
  const centerX = (contentBbox.minX + contentBbox.maxX) / 2
  const outward = anchorX <= centerX ? -1 : 1
  const dimLineX = anchorX + outward * offset
  const labelOffset = outward * (fontSize * 0.95 + labelWidth * 0.18)
  const labelX = dimLineX + labelOffset
  const dimLines: DimLine[] = [
    dimLine(anchorX1, anchorY1, dimLineX, anchorY1, 'extension'),
    dimLine(anchorX2, anchorY2, dimLineX, anchorY2, 'extension'),
    dimLine(dimLineX, anchorY1, dimLineX, anchorY2, 'dimension'),
  ]
  const arrowSvg = [
    buildParamExtLine(anchorX1, anchorY1, dimLineX, anchorY1),
    buildParamExtLine(anchorX2, anchorY2, dimLineX, anchorY2),
    buildParamDimLine(dimLineX, anchorY1, dimLineX, anchorY2),
  ].join('')
  const result: DimAnnotation = {
    field: ann.field,
    axis: 'vertical',
    labelX,
    labelY: (anchorY1 + anchorY2) / 2,
    lineX: dimLineX,
    lineY: (anchorY1 + anchorY2) / 2,
    labelWidth,
    labelHeight,
    fontSize,
    arrowSvg,
    dimLines,
    displayValue: fromMm(dimValueFromGeometry(geometry, ann.field, dimensionType), unit),
    extents: { minX: 0, minY: 0, maxX: 0, maxY: 0 },
  }
  result.extents = mergeExtents(
    { minX: Math.min(anchorX1, anchorX2, dimLineX), minY: Math.min(anchorY1, anchorY2), maxX: Math.max(anchorX1, anchorX2, dimLineX), maxY: Math.max(anchorY1, anchorY2) },
    labelExtents(result),
  )
  return result
}

/** 0201 尺寸箭头（无文字），供标注层叠加 */
export function renderDimensionArrowsOnly0201(geometry: DielineGeometry): string {
  return get0201DimAnnotations(geometry, 'mm', 'manufacturing')
    .map((ann) => ann.arrowSvg)
    .join('')
}

/** 0201 可编辑标注元数据（防重叠布局） */
export function get0201DimAnnotations(
  geometry: DielineGeometry,
  unit: Unit,
  dimensionType: DimensionType,
): DimAnnotation[] {
  const L = geometry.manufacturing.length
  const W = geometry.manufacturing.width
  const H = geometry.manufacturing.height
  const glue = geometry.glueTabMm
  const yBodyTop = W / 2
  const yBodyBot = W / 2 + H
  const xL1 = glue
  const xW1 = glue + L
  const xL2 = glue + L + W
  const yMid = (yBodyTop + yBodyBot) / 2
  const inset = Math.max(10, L * 0.02)
  const fontSize = dimLabelFontSize(geometry)
  const { labelWidth, labelHeight } = dimLabelSize(fontSize)
  const gapHalf = dimTextGapHalf(fontSize, labelWidth)

  const lX1 = xL1 + inset
  const lX2 = xW1 - inset
  const lLineY = yMid
  const horizontalLabelOffset = fontSize * 1.05

  const wX1 = xW1 + inset
  const wX2 = xL2 - inset
  const wLineY = yBodyBot - inset

  const hY1 = yBodyTop + inset
  const hY2 = yBodyBot - inset
  const hLineX = xL2 + L * 0.5
  const hLabelOffset = fontSize * 2.5

  return [
    makeHorizontalDimAnnotation(
      'length',
      geometry,
      unit,
      dimensionType,
      lX1,
      lX2,
      lLineY,
      lLineY - horizontalLabelOffset,
      labelWidth,
      labelHeight,
      fontSize,
      gapHalf,
    ),
    makeHorizontalDimAnnotation(
      'width',
      geometry,
      unit,
      dimensionType,
      wX1,
      wX2,
      wLineY,
      wLineY - horizontalLabelOffset,
      labelWidth,
      labelHeight,
      fontSize,
      gapHalf,
    ),
    makeVerticalDimAnnotation(
      'height',
      geometry,
      unit,
      dimensionType,
      hLineX,
      hY1,
      hY2,
      hLineX + hLabelOffset,
      labelWidth,
      labelHeight,
      fontSize,
      gapHalf,
    ),
  ]
}

export function getDimAnnotations(
  preview: DielinePreview,
  unit: Unit,
  dimensionType: DimensionType,
  engineKey?: EngineKey,
  asset?: DielineTemplateAsset | null,
): DimAnnotation[] {
  if (preview.source === 'parametric') {
    if (!asset) return []
    const contentBbox = contentBboxFromSegments(preview.segments)
    return buildParametricDimensionAnnotations(asset, preview.geometry)
      .map((ann) => makeConfiguredDimAnnotation(ann, preview.geometry, unit, dimensionType, contentBbox))
  }
  if (engineKey === 'slotted_rsc' || engineKey === 'folding_shipping') {
    return get0201DimAnnotations(preview.geometry, unit, dimensionType)
  }
  return []
}

/** 仅刀版线稿 SVG（不含尺寸标注） */
export function renderPreviewLinesSvg(preview: DielinePreview, overrideViewBox?: string): string {
  const { segments, viewBox } = preview
  const effectiveViewBox = overrideViewBox || viewBox
  const lines = segments.map(renderLineSvg).join('')
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${effectiveViewBox}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" style="background:#f8fafc">${lines}</svg>`
}

export function renderPreviewSvg(preview: DielinePreview, unit: Unit): string {
  return renderPreviewLinesSvg(preview)
}

function segmentsToMakerModel(segments: LineSegment[], kinds: LineKind[]): makerjs.IModel {
  const paths: makerjs.IPathMap = {}
  segments
    .filter((seg) => kinds.includes(seg.kind))
    .forEach((seg, index) => {
      paths[`line${index}`] = new makerjs.paths.Line([seg.x1, seg.y1], [seg.x2, seg.y2])
    })
  return { paths }
}

export function exportDxf(preview: DielinePreview): string {
  const cutModel = segmentsToMakerModel(preview.segments, ['cut'])
  const creaseModel = segmentsToMakerModel(preview.segments, ['crease'])
  const model: makerjs.IModel = {
    models: {
      cut: cutModel,
      crease: creaseModel,
    },
  }
  return makerjs.exporter.toDXF(model)
}

export function unfoldAreaM2(params: BoxParams): number {
  const template = getBoxTemplate(params.boxCode)
  if (hasMappedParametricAsset(template?.activeParametricAsset)) {
    return buildPreview(params).geometry.unfoldAreaM2
  }
  return computeGeometry(params).unfoldAreaM2
}

export function buildQuoteInputs(params: BoxParams) {
  return {
    box_code: params.boxCode,
    length_mm: toMm(params.length, params.unit),
    width_mm: toMm(params.width, params.unit),
    height_mm: toMm(params.height, params.unit),
    thickness_mm: toMm(params.thickness, params.unit),
    dimension_type: params.dimensionType,
    board_type: params.boardType,
    quantity: params.quantity,
    print_colors: params.printColors,
  }
}

export function downloadTextFile(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}
