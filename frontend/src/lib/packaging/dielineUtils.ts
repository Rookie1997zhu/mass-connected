import type { LineKind, LineSegment } from './types'

export function addSegment(
  segments: LineSegment[],
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  kind: LineKind,
): void {
  segments.push({ x1, y1, x2, y2, kind })
}

export function addBleedRect(segments: LineSegment[], w: number, h: number, bleedMm = 3): void {
  addSegment(segments, -bleedMm, -bleedMm, w + bleedMm, -bleedMm, 'bleed')
  addSegment(segments, w + bleedMm, -bleedMm, w + bleedMm, h + bleedMm, 'bleed')
  addSegment(segments, w + bleedMm, h + bleedMm, -bleedMm, h + bleedMm, 'bleed')
  addSegment(segments, -bleedMm, h + bleedMm, -bleedMm, -bleedMm, 'bleed')
}

export function slotWidthFromThickness(thicknessMm: number): number {
  return Math.max(0.1, thicknessMm)
}

export function slotCornerRadius(thicknessMm: number, slotW: number): number {
  return Math.min(slotW / 2, thicknessMm * 0.6, 2)
}

export function addArcApprox(
  segments: LineSegment[],
  cx: number,
  cy: number,
  r: number,
  startDeg: number,
  endDeg: number,
  kind: LineKind,
  steps = 6,
): void {
  if (r <= 0.01) return
  const start = (startDeg * Math.PI) / 180
  const end = (endDeg * Math.PI) / 180
  const step = (end - start) / steps
  for (let i = 0; i < steps; i++) {
    const a1 = start + step * i
    const a2 = start + step * (i + 1)
    addSegment(
      segments,
      cx + r * Math.cos(a1),
      cy + r * Math.sin(a1),
      cx + r * Math.cos(a2),
      cy + r * Math.sin(a2),
      kind,
    )
  }
}

/** 以 xCenter 为中心的矩形竖槽：左右竖线 + 上下封口 */
export function addVerticalSlot(
  segments: LineSegment[],
  xCenter: number,
  y1: number,
  y2: number,
  slotW: number,
  kind: LineKind = 'cut',
): void {
  const half = slotW / 2
  const xLeft = xCenter - half
  const xRight = xCenter + half
  addSegment(segments, xLeft, y1, xLeft, y2, kind)
  addSegment(segments, xRight, y1, xRight, y2, kind)
  addSegment(segments, xLeft, y1, xRight, y1, kind)
  addSegment(segments, xLeft, y2, xRight, y2, kind)
}

/** 圆角竖槽：四角小圆角，交界更自然 */
export function addVerticalSlotRounded(
  segments: LineSegment[],
  xCenter: number,
  y1: number,
  y2: number,
  slotW: number,
  thicknessMm: number,
  kind: LineKind = 'cut',
): void {
  const half = slotW / 2
  const xLeft = xCenter - half
  const xRight = xCenter + half
  const r = slotCornerRadius(thicknessMm, slotW)

  if (r < 0.2 || y2 - y1 < r * 2) {
    addVerticalSlot(segments, xCenter, y1, y2, slotW, kind)
    return
  }

  addSegment(segments, xLeft + r, y1, xRight - r, y1, kind)
  addArcApprox(segments, xRight - r, y1 + r, r, 270, 360, kind)
  addSegment(segments, xRight, y1 + r, xRight, y2 - r, kind)
  addArcApprox(segments, xRight - r, y2 - r, r, 0, 90, kind)
  addSegment(segments, xRight - r, y2, xLeft + r, y2, kind)
  addArcApprox(segments, xLeft + r, y2 - r, r, 90, 180, kind)
  addSegment(segments, xLeft, y2 - r, xLeft, y1 + r, kind)
  addArcApprox(segments, xLeft + r, y1 + r, r, 180, 270, kind)
}

/** 在 y 高度画水平割线，按 gaps 列表断开（每 gap 为 [xLeft, xRight]） */
export function addHorizontalCutWithGaps(
  segments: LineSegment[],
  y: number,
  xStart: number,
  xEnd: number,
  gaps: [number, number][],
): void {
  const sorted = [...gaps].sort((a, b) => a[0] - b[0])
  let cursor = Math.min(xStart, xEnd)
  const end = Math.max(xStart, xEnd)

  for (const [gLeft, gRight] of sorted) {
    if (cursor < gLeft) {
      addSegment(segments, cursor, y, gLeft, y, 'cut')
    }
    cursor = Math.max(cursor, gRight)
  }

  if (cursor < end) {
    addSegment(segments, cursor, y, end, y, 'cut')
  }
}
