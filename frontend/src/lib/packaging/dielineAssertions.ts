import { build0201Segments, buildPreview, computeGeometry, exportDxf } from './boxEngine'
import { buildDielinePdfBytes } from './dielineExport'
import { build0427Segments } from './dieline0427'
import { REFERENCE_0201 } from './boxPresets'
import type { BoxParams, LineSegment } from './types'

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`)
  }
}

function horizontalCutsAt(segments: LineSegment[], y: number, tolerance = 0.01): LineSegment[] {
  return segments.filter(
    (seg) =>
      seg.kind === 'cut' &&
      Math.abs(seg.y1 - y) < tolerance &&
      Math.abs(seg.y2 - y) < tolerance &&
      Math.abs(seg.x1 - seg.x2) > tolerance,
  )
}

function verticalCutsAt(segments: LineSegment[], x: number, tolerance = 0.01): LineSegment[] {
  return segments.filter(
    (seg) =>
      seg.kind === 'cut' &&
      Math.abs(seg.x1 - x) < tolerance &&
      Math.abs(seg.x2 - x) < tolerance &&
      Math.abs(seg.y1 - seg.y2) > tolerance,
  )
}

function countByKind(segments: LineSegment[], kind: LineSegment['kind']): number {
  return segments.filter((seg) => seg.kind === kind).length
}

function to0201Params(): BoxParams {
  const preset = REFERENCE_0201
  return {
    boxCode: '0201',
    length: preset.length,
    width: preset.width,
    height: preset.height,
    thickness: preset.thickness,
    unit: preset.unit,
    dimensionType: preset.dimensionType,
    boardType: preset.boardType,
    quantity: 1,
    printColors: 0,
  }
}

export function runDielineAssertions(): void {
  const params = to0201Params()
  const geometry = computeGeometry(params)
  const preview = buildPreview(params)
  const segments = build0201Segments(geometry)

  const L = geometry.manufacturing.length
  const W = geometry.manufacturing.width
  const glue = geometry.glueTabMm
  const xW1 = glue + L
  const xL2 = glue + L + W
  const xW2 = glue + L + W + L
  const slotW = geometry.thicknessMm
  const half = slotW / 2

  assert(geometry.blankWidthMm === 2 * (L + W) + glue, '0201 blank width unchanged')
  assert(geometry.blankHeightMm === W + geometry.manufacturing.height, '0201 blank height unchanged')

  const cutCount = countByKind(segments, 'cut')
  const creaseCount = countByKind(segments, 'crease')
  assert(cutCount > 80, `0201 rounded-slot cut segments should exceed rect slots, got ${cutCount}`)
  assert(creaseCount === 6, `0201 crease segments should be 6, got ${creaseCount}`)

  const topCuts = horizontalCutsAt(segments, 0)
  const bottomCuts = horizontalCutsAt(segments, W + geometry.manufacturing.height)
  assert(topCuts.length >= 4, `top edge should be split into >=4 segments, got ${topCuts.length}`)
  assert(bottomCuts.length >= 4, `bottom edge should be split into >=4 segments, got ${bottomCuts.length}`)

  for (const xi of [xW1, xL2, xW2]) {
    const leftVerts = verticalCutsAt(segments, xi - half)
    const rightVerts = verticalCutsAt(segments, xi + half)
    assert(leftVerts.length >= 2, `slot left edge expected at x=${xi - half}`)
    assert(rightVerts.length >= 2, `slot right edge expected at x=${xi + half}`)
    assert(verticalCutsAt(segments, xi).length === 0, `zero-width center slit should be removed at x=${xi}`)
  }

  assert(preview.segments.length === segments.length, 'buildPreview segments should match build0201Segments')

  const dxf = exportDxf(preview)
  assert(dxf.length > 500, 'DXF export should produce line entities')
  assert(dxf.includes('LINE'), 'DXF export should include LINE entities')

  const pdfBytes = buildDielinePdfBytes(preview)
  assert(pdfBytes.length > 1024, 'PDF export should exceed 1KB')
  const pdfHeader = String.fromCharCode(...pdfBytes.slice(0, 4))
  assert(pdfHeader === '%PDF', `PDF export should start with %PDF, got ${pdfHeader}`)
  const pdfBytesAgain = buildDielinePdfBytes(preview)
  assert(pdfBytesAgain.length === pdfBytes.length, 'PDF and AI should share the same byte length')

  const params0427: BoxParams = {
    ...params,
    boxCode: '0427',
    length: 200,
    width: 150,
    height: 100,
    thickness: 3,
  }
  const geo0427 = computeGeometry(params0427)
  const seg0427 = build0427Segments(geo0427)
  assert(countByKind(seg0427, 'cut') > 0, '0427 should still produce cut segments')
  assert(countByKind(seg0427, 'crease') > 0, '0427 should still produce crease segments')
}
