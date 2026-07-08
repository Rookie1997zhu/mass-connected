import {
  addBleedRect,
  addHorizontalCutWithGaps,
  addSegment,
  addVerticalSlotRounded,
  slotWidthFromThickness,
} from './dielineUtils'
import type { DielineGeometry, LineSegment } from './types'

/** 折叠运输箱：开槽 RSC 顶盖 + 互锁底（交替竖槽） */
export function buildFoldingShippingSegments(geo: DielineGeometry): LineSegment[] {
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
  const topJointXs = [xW1, xL2, xW2]
  const topSlitGaps = topJointXs.map((x) => [x - half, x + half] as [number, number])

  const latchSlotW = Math.max(slotW, Math.min(W * 0.08, 32))
  const latchHalf = latchSlotW / 2
  const latchMidY = yBodyBot + W / 4

  const lFlapCenters = [xL1 + L / 2, xL2 + L / 2]
  const bottomGaps = lFlapCenters.map((xc) => [xc - latchHalf, xc + latchHalf] as [number, number])

  const segments: LineSegment[] = []

  addBleedRect(segments, xEnd, yBot)

  addHorizontalCutWithGaps(segments, yTop, xL1, xEnd, topSlitGaps)
  addSegment(segments, xEnd, yBot, xEnd, yTop, 'cut')
  addHorizontalCutWithGaps(segments, yBot, xL1, xEnd, bottomGaps)
  addSegment(segments, xL1, yTop, xL1, yBodyTop, 'cut')
  addSegment(segments, xL1, yBodyTop, xGlue, yBodyTop, 'cut')
  addSegment(segments, xGlue, yBodyTop, xGlue, yBodyBot, 'cut')
  addSegment(segments, xGlue, yBodyBot, xL1, yBodyBot, 'cut')
  addSegment(segments, xL1, yBodyBot, xL1, yBot, 'cut')

  for (const xi of topJointXs) {
    addVerticalSlotRounded(segments, xi, yTop, yBodyTop, slotW, geo.thicknessMm)
  }

  const bottomFlaps: Array<{ x: number; fromBottom: boolean }> = [
    { x: xL1 + L / 2, fromBottom: true },
    { x: xW1 + W / 2, fromBottom: false },
    { x: xL2 + L / 2, fromBottom: true },
    { x: xW2 + W / 2, fromBottom: false },
  ]
  for (const flap of bottomFlaps) {
    if (flap.fromBottom) {
      addVerticalSlotRounded(segments, flap.x, latchMidY, yBot, latchSlotW, geo.thicknessMm)
    } else {
      addVerticalSlotRounded(segments, flap.x, yBodyBot, latchMidY, latchSlotW, geo.thicknessMm)
    }
  }

  for (const xi of [xL1, xW1, xL2, xW2]) {
    addSegment(segments, xi, yBodyTop, xi, yBodyBot, 'crease')
  }
  addSegment(segments, xL1, yBodyTop, xEnd, yBodyTop, 'crease')
  addSegment(segments, xL1, yBodyBot, xEnd, yBodyBot, 'crease')

  return segments
}
