import makerjs from 'makerjs'
import { getBoxTemplate } from './fefcoCatalog'
import type {
  BoxParams,
  BoxCode,
  DielineGeometry,
  DielinePreview,
  DimensionType,
  LineKind,
  LineSegment,
  SizeTriple,
  Unit,
} from './types'

const MM_PER_IN = 25.4
const DEFAULT_GLUE_TAB_MM = 25
const MIN_DIM_MM = 10
const MAX_DIM_MM = 2000
const BLEED_MM = 3

export function toMm(value: number, unit: Unit): number {
  return unit === 'in' ? value * MM_PER_IN : value
}

export function fromMm(value: number, unit: Unit): number {
  return unit === 'in' ? value / MM_PER_IN : value
}

function toManufacturingMm(
  length: number,
  width: number,
  height: number,
  thicknessMm: number,
  dimensionType: DimensionType,
): SizeTriple {
  const t = Math.max(0.1, thicknessMm)
  if (dimensionType === 'manufacturing') {
    return { length, width, height }
  }
  if (dimensionType === 'external') {
    return {
      length: Math.max(MIN_DIM_MM, length - 2 * t),
      width: Math.max(MIN_DIM_MM, width - 2 * t),
      height: Math.max(MIN_DIM_MM, height - 2 * t),
    }
  }
  return { length, width, height }
}

function sizeTripleFromManufacturing(m: SizeTriple, thicknessMm: number): { internal: SizeTriple; external: SizeTriple } {
  const t = thicknessMm
  return {
    internal: { ...m },
    external: {
      length: m.length + 2 * t,
      width: m.width + 2 * t,
      height: m.height + 2 * t,
    },
  }
}

function computeBlankSize(code: BoxCode, m: SizeTriple, glueTab: number): { blankWidthMm: number; blankHeightMm: number } {
  const L = m.length
  const W = m.width
  const H = m.height
  switch (code) {
    case '0201':
      return { blankWidthMm: 2 * (L + W) + glueTab, blankHeightMm: W + 2 * H }
    case '0427':
      return { blankWidthMm: 2 * (L + W) + glueTab, blankHeightMm: H + W + Math.max(10, W * 0.5) }
    case '0713':
      return { blankWidthMm: 2 * (L + W) + glueTab, blankHeightMm: 2 * H + W }
    case '0716':
      return { blankWidthMm: 2 * (L + W) + glueTab, blankHeightMm: 2 * H + 1.25 * W }
    default:
      throw new Error(`Unsupported box code: ${code}`)
  }
}

export function computeGeometry(params: BoxParams, glueTabMm = DEFAULT_GLUE_TAB_MM): DielineGeometry {
  const template = getBoxTemplate(params.boxCode)
  if (!template?.previewEnabled) {
    throw new Error('Box type preview not available yet')
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
  )
  const { internal, external } = sizeTripleFromManufacturing(manufacturing, thicknessMm)
  const glueTab = Math.max(15, glueTabMm)
  const { blankWidthMm, blankHeightMm } = computeBlankSize(params.boxCode, manufacturing, glueTab)
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

function addSegment(segments: LineSegment[], x1: number, y1: number, x2: number, y2: number, kind: LineKind) {
  segments.push({ x1, y1, x2, y2, kind })
}

function build0201Segments(geo: DielineGeometry): LineSegment[] {
  const L = geo.manufacturing.length
  const W = geo.manufacturing.width
  const H = geo.manufacturing.height
  const glue = geo.glueTabMm
  const flap = W / 2
  const bodyTop = flap
  const bodyBottom = flap + H
  const totalW = glue + 2 * L + 2 * W
  const totalH = W + 2 * H

  const xGlue = 0
  const xL1 = glue
  const xW1 = glue + L
  const xL2 = glue + L + W
  const xW2 = glue + L + W + L
  const xEnd = totalW

  const segments: LineSegment[] = []

  // bleed（外扩参考框）
  addSegment(segments, -BLEED_MM, -BLEED_MM, totalW + BLEED_MM, -BLEED_MM, 'bleed')
  addSegment(segments, totalW + BLEED_MM, -BLEED_MM, totalW + BLEED_MM, totalH + BLEED_MM, 'bleed')
  addSegment(segments, totalW + BLEED_MM, totalH + BLEED_MM, -BLEED_MM, totalH + BLEED_MM, 'bleed')
  addSegment(segments, -BLEED_MM, totalH + BLEED_MM, -BLEED_MM, -BLEED_MM, 'bleed')

  // 外轮廓 cut
  addSegment(segments, xGlue, bodyTop, xGlue, bodyBottom, 'cut')
  addSegment(segments, xGlue, bodyTop, xL1, bodyTop, 'cut')
  addSegment(segments, xGlue, bodyBottom, xL1, bodyBottom, 'cut')
  addSegment(segments, xL1, bodyTop, xL1, 0, 'cut')
  addSegment(segments, xL1, 0, xW1, 0, 'cut')
  addSegment(segments, xW1, 0, xW1, totalH, 'cut')
  addSegment(segments, xW1, totalH, xL2, totalH, 'cut')
  addSegment(segments, xL2, totalH, xL2, bodyBottom, 'cut')
  addSegment(segments, xL2, bodyBottom, xW2, bodyBottom, 'cut')
  addSegment(segments, xL2, bodyTop, xW2, bodyTop, 'cut')
  addSegment(segments, xW2, bodyTop, xW2, 0, 'cut')
  addSegment(segments, xW2, 0, xEnd, 0, 'cut')
  addSegment(segments, xEnd, 0, xEnd, totalH, 'cut')
  addSegment(segments, xEnd, totalH, xW2 + W, totalH, 'cut')
  addSegment(segments, xL2, bodyTop, xL2, 0, 'cut')
  addSegment(segments, xL2, 0, xW2, 0, 'cut')

  // 竖向压线
  ;[xGlue, xL1, xW1, xL2, xW2, xEnd].forEach((x) => {
    addSegment(segments, x, 0, x, totalH, 'crease')
  })

  // 横向压线（W 面板折线）
  addSegment(segments, xW1, bodyTop, xW1 + W, bodyTop, 'crease')
  addSegment(segments, xW1, bodyBottom, xW1 + W, bodyBottom, 'crease')
  addSegment(segments, xW2, bodyTop, xW2 + W, bodyTop, 'crease')
  addSegment(segments, xW2, bodyBottom, xW2 + W, bodyBottom, 'crease')

  return segments
}

function buildBlankOutlineSegments(totalW: number, totalH: number): LineSegment[] {
  const segments: LineSegment[] = []
  addSegment(segments, -BLEED_MM, -BLEED_MM, totalW + BLEED_MM, -BLEED_MM, 'bleed')
  addSegment(segments, totalW + BLEED_MM, -BLEED_MM, totalW + BLEED_MM, totalH + BLEED_MM, 'bleed')
  addSegment(segments, totalW + BLEED_MM, totalH + BLEED_MM, -BLEED_MM, totalH + BLEED_MM, 'bleed')
  addSegment(segments, -BLEED_MM, totalH + BLEED_MM, -BLEED_MM, -BLEED_MM, 'bleed')
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
  const pad = 40
  const viewBox = `${-pad} ${-pad} ${geometry.blankWidthMm + pad * 2} ${geometry.blankHeightMm + pad * 2}`

  if (params.boxCode === '0201') {
    return {
      geometry,
      segments: build0201Segments(geometry),
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

const STROKE: Record<LineKind, { color: string; dash?: string; width: number }> = {
  bleed: { color: '#22c55e', width: 0.8 },
  cut: { color: '#2563eb', width: 1.2 },
  crease: { color: '#ef4444', dash: '6 4', width: 1 },
}

function escapeXml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;')
}

export function renderPreviewSvg(preview: DielinePreview, unit: Unit): string {
  const { geometry, segments, viewBox } = preview
  const lines = segments
    .map((seg) => {
      const style = STROKE[seg.kind]
      const dash = style.dash ? ` stroke-dasharray="${style.dash}"` : ''
      return `<line x1="${seg.x1}" y1="${seg.y1}" x2="${seg.x2}" y2="${seg.y2}" stroke="${style.color}" stroke-width="${style.width}"${dash} />`
    })
    .join('')

  const lDisp = fromMm(geometry.manufacturing.length, unit).toFixed(unit === 'in' ? 4 : 1)
  const wDisp = fromMm(geometry.manufacturing.width, unit).toFixed(unit === 'in' ? 4 : 1)
  const hDisp = fromMm(geometry.manufacturing.height, unit).toFixed(unit === 'in' ? 4 : 1)
  const unitLabel = unit === 'in' ? 'in' : 'mm'

  const dimL = `<text x="${geometry.glueTabMm + geometry.manufacturing.length / 2}" y="${geometry.blankHeightMm + 24}" text-anchor="middle" font-size="11" fill="#64748b">${lDisp} ${unitLabel}</text>`
  const dimW = `<text x="${geometry.blankWidthMm + 20}" y="${geometry.manufacturing.width / 2 + geometry.manufacturing.height}" text-anchor="middle" font-size="11" fill="#64748b" transform="rotate(90 ${geometry.blankWidthMm + 20} ${geometry.manufacturing.width / 2 + geometry.manufacturing.height})">${wDisp} ${unitLabel}</text>`

  const summary = [
    `M ${lDisp} x ${wDisp} x ${hDisp} ${unitLabel}`,
    `Blank ${geometry.blankWidthMm.toFixed(1)} x ${geometry.blankHeightMm.toFixed(1)} mm`,
    `Area ${geometry.unfoldAreaM2.toFixed(4)} m²`,
  ]
    .map((line, i) => `<text x="8" y="${16 + i * 14}" font-size="11" fill="#334155">${escapeXml(line)}</text>`)
    .join('')

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="100%" height="100%" style="background:#f8fafc">${summary}${lines}${dimL}${dimW}</svg>`
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

export function exportSvg(preview: DielinePreview): string {
  const model = segmentsToMakerModel(preview.segments, ['cut', 'crease'])
  return makerjs.exporter.toSVG(model, { units: makerjs.unitType.Millimeter })
}

export function unfoldAreaM2(params: BoxParams): number {
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
