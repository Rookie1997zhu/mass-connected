import { jsPDF } from 'jspdf'
import type { DielinePreview, LineKind, LineSegment } from './types'

const MARGIN_MM = 10

const STROKE: Record<LineKind, { r: number; g: number; b: number; width: number; dash?: number[] }> = {
  bleed: { r: 34, g: 197, b: 94, width: 0.15 },
  cut: { r: 37, g: 99, b: 235, width: 0.2 },
  crease: { r: 239, g: 68, b: 68, width: 0.15, dash: [2, 1.5] },
}

const DRAW_ORDER: LineKind[] = ['bleed', 'crease', 'cut']

function toPdfY(svgY: number, pageHeightMm: number): number {
  return pageHeightMm - MARGIN_MM - svgY
}

function drawSegment(doc: jsPDF, seg: LineSegment, pageHeightMm: number): void {
  const style = STROKE[seg.kind]
  doc.setDrawColor(style.r, style.g, style.b)
  doc.setLineWidth(style.width)
  if (style.dash) {
    doc.setLineDashPattern(style.dash, 0)
  } else {
    doc.setLineDashPattern([], 0)
  }
  doc.line(
    seg.x1 + MARGIN_MM,
    toPdfY(seg.y1, pageHeightMm),
    seg.x2 + MARGIN_MM,
    toPdfY(seg.y2, pageHeightMm),
  )
}

export function buildDielinePdfBytes(preview: DielinePreview): Uint8Array {
  const { geometry, segments } = preview
  const pageWidthMm = geometry.blankWidthMm + MARGIN_MM * 2
  const pageHeightMm = geometry.blankHeightMm + MARGIN_MM * 2

  const doc = new jsPDF({
    orientation: pageWidthMm >= pageHeightMm ? 'landscape' : 'portrait',
    unit: 'mm',
    format: [pageWidthMm, pageHeightMm],
  })

  doc.setProperties({
    title: `FEFCO ${geometry.boxCode} Dieline ${geometry.blankWidthMm.toFixed(1)}x${geometry.blankHeightMm.toFixed(1)}mm`,
    creator: 'MASS CONNECTED Box Generator',
    subject: 'Packaging dieline',
  })

  for (const kind of DRAW_ORDER) {
    segments.filter((seg) => seg.kind === kind).forEach((seg) => drawSegment(doc, seg, pageHeightMm))
  }

  return new Uint8Array(doc.output('arraybuffer'))
}

export function downloadBlobFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function exportDielinePdf(preview: DielinePreview): void {
  const bytes = buildDielinePdfBytes(preview)
  const code = preview.geometry.boxCode
  downloadBlobFile(new Blob([bytes], { type: 'application/pdf' }), `dieline-${code}.pdf`)
}

export function exportDielineAi(preview: DielinePreview): void {
  const bytes = buildDielinePdfBytes(preview)
  const code = preview.geometry.boxCode
  downloadBlobFile(new Blob([bytes], { type: 'application/pdf' }), `dieline-${code}.ai`)
}
