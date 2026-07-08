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
import { getBoxTemplate } from './fefcoCatalog'
import { buildParametricSegments, hasMappedParametricAsset, viewBoxFromSegments } from './parametricTemplate'
import type {
  BoxParams,
  DimAnnotation,
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
  const engineKey = template.engineKey

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
      }
    }
  }

  const viewBox = computePreviewViewBox(geometry)

  if (engineKey === 'slotted_rsc') {
    return {
      geometry,
      segments: build0201Segments(geometry),
      viewBox,
      previewMode: 'detailed',
    }
  }

  if (engineKey === 'folding_shipping') {
    return {
      geometry,
      segments: buildFoldingShippingSegments(geometry),
      viewBox,
      previewMode: 'detailed',
    }
  }

  if (engineKey === 'mailer_folder') {
    return {
      geometry,
      segments: build0427Segments(geometry),
      viewBox,
      previewMode: 'detailed',
    }
  }

  if (engineKey === 'tuck_end') {
    const flapGap = template.flapGapMm ?? 2
    return {
      geometry,
      segments: buildTuckEndSegments(geometry, flapGap),
      viewBox,
      previewMode: 'detailed',
    }
  }

  if (engineKey === 'auto_lock_bottom') {
    const flapGap = template.flapGapMm ?? 2
    return {
      geometry,
      segments: buildAutoLockBottomSegments(geometry, flapGap),
      viewBox,
      previewMode: 'detailed',
    }
  }

  return {
    geometry,
    segments: buildBlankOutlineSegments(geometry.blankWidthMm, geometry.blankHeightMm),
    viewBox,
    previewMode: 'blank',
  }
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

const DIM_LINE_BASE =
  `stroke="${DIM_COLOR}" stroke-width="1.5" vector-effect="non-scaling-stroke" shape-rendering="geometricPrecision"`

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
  const lArrow = buildHorizDimLine(lX1, lX2, lLineY, gapHalf)
  const horizontalLabelOffset = fontSize * 1.05

  const wX1 = xW1 + inset
  const wX2 = xL2 - inset
  const wLineY = yBodyBot - inset
  const wArrow = buildHorizDimLine(wX1, wX2, wLineY, gapHalf)

  const hY1 = yBodyTop + inset
  const hY2 = yBodyBot - inset
  const hLineX = xL2 + L * 0.5
  const hArrow = buildVertDimLine(hLineX, hY1, hY2, gapHalf)
  const hLabelOffset = fontSize * 2.5

  return [
    {
      field: 'length',
      axis: 'horizontal',
      labelX: (lX1 + lX2) / 2,
      labelY: lLineY - horizontalLabelOffset,
      lineX: (lX1 + lX2) / 2,
      lineY: lLineY,
      labelWidth,
      labelHeight,
      fontSize,
      arrowSvg: lArrow,
      displayValue: fromMm(dimValueFromGeometry(geometry, 'length', dimensionType), unit),
    },
    {
      field: 'width',
      axis: 'horizontal',
      labelX: (wX1 + wX2) / 2,
      labelY: wLineY - horizontalLabelOffset,
      lineX: (wX1 + wX2) / 2,
      lineY: wLineY,
      labelWidth,
      labelHeight,
      fontSize,
      arrowSvg: wArrow,
      displayValue: fromMm(dimValueFromGeometry(geometry, 'width', dimensionType), unit),
    },
    {
      field: 'height',
      axis: 'vertical',
      labelX: hLineX + hLabelOffset,
      labelY: (hY1 + hY2) / 2,
      lineX: hLineX,
      lineY: (hY1 + hY2) / 2,
      labelWidth,
      labelHeight,
      fontSize,
      arrowSvg: hArrow,
      displayValue: fromMm(dimValueFromGeometry(geometry, 'height', dimensionType), unit),
    },
  ]
}

/** 仅刀版线稿 SVG（不含尺寸标注） */
export function renderPreviewLinesSvg(preview: DielinePreview): string {
  const { segments, viewBox } = preview
  const lines = segments.map(renderLineSvg).join('')
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" style="background:#f8fafc">${lines}</svg>`
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
