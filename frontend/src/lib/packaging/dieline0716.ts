import {
  addBleedRect,
  addHorizontalCutWithGaps,
  addSegment,
  addVerticalSlotRounded,
  slotWidthFromThickness,
} from './dielineUtils'
import type { DielineGeometry, LineSegment } from './types'

/** FEFCO 0716 自锁底盒：底锁结构 1.25W + 盒身 H + 顶插舌 H */
export function buildAutoLockBottomSegments(geo: DielineGeometry, flapGapMm = 2): LineSegment[] {
  const L = geo.manufacturing.length
  const W = geo.manufacturing.width
  const H = geo.manufacturing.height
  const glue = geo.glueTabMm
  const gap = Math.max(0, flapGapMm)
  const lockExtra = W * 0.25

  const xGlue = 0
  const xL1 = glue
  const xW1 = glue + L
  const xL2 = glue + L + W
  const xW2 = glue + L + W + L
  const xEnd = glue + 2 * L + 2 * W

  const yTop = 0
  const yBodyTop = W + lockExtra
  const yBodyBot = W + lockExtra + H
  const yBot = W + lockExtra + 2 * H

  const slotW = slotWidthFromThickness(geo.thicknessMm)
  const half = slotW / 2
  const jointXs = [xW1, xL2, xW2]
  const jointGaps = jointXs.map((x) => [x - half, x + half] as [number, number])

  const dustW = Math.max(W * 0.35, 20)
  const tuckDepth = Math.max(H * 0.85, 12)
  const latchSlotW = Math.max(slotW, Math.min(W * 0.08, 32))
  const latchHalf = latchSlotW / 2

  const segments: LineSegment[] = []
  addBleedRect(segments, xEnd, yBot)

  addHorizontalCutWithGaps(segments, yBot, xL1, xEnd, jointGaps)
  addSegment(segments, xEnd, yBot, xEnd, yTop, 'cut')
  addHorizontalCutWithGaps(segments, yTop, xL1, xEnd, jointGaps)

  addSegment(segments, xL1, yTop, xL1, yBodyTop, 'cut')
  addSegment(segments, xL1, yBodyTop, xGlue, yBodyTop, 'cut')
  addSegment(segments, xGlue, yBodyTop, xGlue, yBodyBot, 'cut')
  addSegment(segments, xGlue, yBodyBot, xL1, yBodyBot, 'cut')
  addSegment(segments, xL1, yBodyBot, xL1, yBot, 'cut')

  for (const xi of jointXs) {
    addVerticalSlotRounded(segments, xi, yTop, yBodyTop, slotW, geo.thicknessMm)
    addVerticalSlotRounded(segments, xi, yBodyBot, yBot, slotW, geo.thicknessMm)
  }

  for (const xi of [xL1, xW1, xL2, xW2]) {
    addSegment(segments, xi, yBodyTop, xi, yBodyBot, 'crease')
  }
  addSegment(segments, xL1, yBodyTop, xEnd, yBodyTop, 'crease')
  addSegment(segments, xL1, yBodyBot, xEnd, yBodyBot, 'crease')
  addSegment(segments, xL1, yBodyTop - lockExtra, xEnd, yBodyTop - lockExtra, 'crease')

  const lockMidY = yBodyTop - lockExtra / 2
  const lFlapCenters = [xL1 + L / 2, xL2 + L / 2]
  for (const xc of lFlapCenters) {
    addVerticalSlotRounded(segments, xc, yTop, yBodyTop - lockExtra, latchSlotW, geo.thicknessMm)
    addSegment(segments, xc - latchHalf, lockMidY, xc + latchHalf, lockMidY, 'cut')
  }

  const topTuckY = yBodyTop - tuckDepth
  for (const xc of [xL1 + L / 2, xL2 + L / 2]) {
    addSegment(segments, xc - dustW / 2, yTop, xc + dustW / 2, yTop, 'cut')
    addSegment(segments, xc - dustW / 2, yTop, xc - dustW / 2, topTuckY, 'cut')
    addSegment(segments, xc + dustW / 2, yTop, xc + dustW / 2, topTuckY, 'cut')
  }

  for (const xc of [xW1 + W / 2, xW2 + W / 2]) {
    const tuckHalf = Math.min(W * 0.4, 40)
    addSegment(segments, xc - tuckHalf, yTop, xc + tuckHalf, yTop, 'cut')
    addSegment(segments, xc - tuckHalf, yTop, xc, topTuckY - gap, 'cut')
    addSegment(segments, xc + tuckHalf, yTop, xc, topTuckY - gap, 'cut')
  }

  return segments
}
