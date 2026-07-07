/**
 * FEFCO 0427 — 翻盖自锁飞机盒（Tray with Self-Locking Walls & Hinged Lid）
 *
 * 参数化结构参考 FEFCO 0400 / 0427 标准及行业刀版惯例：
 * - 底板 L×W，前后墙各 H，盖板 W，插舌 tuckH≈H
 * - 左右各 W 宽侧墙组件（双壁自锁 + 角片）
 * - 盖板两侧防尘翼、顶部插舌圆角
 */
import type { DielineGeometry, LineSegment } from './types'
import { addBleedRect, addArcApprox, addSegment, addVerticalSlot } from './dielineUtils'

export interface Blank0427Size {
  blankWidthMm: number
  blankHeightMm: number
  tuckHeightMm: number
}

export function compute0427BlankSize(
  lengthMm: number,
  widthMm: number,
  heightMm: number,
  thicknessMm: number,
): Blank0427Size {
  const L = lengthMm
  const W = widthMm
  const H = heightMm
  const t = Math.max(0.1, thicknessMm)
  const tuckHeightMm = Math.max(H - t, H * 0.9, 12)
  const blankWidthMm = L + 2 * W
  const blankHeightMm = 2 * H + 2 * W + tuckHeightMm
  return { blankWidthMm, blankHeightMm, tuckHeightMm }
}

/** 竖向锁舌槽（底板两侧） */
function addLockSlots(
  segments: LineSegment[],
  x: number,
  yBase: number,
  slotH: number,
  slotW: number,
  gap: number,
) {
  const y1 = yBase + gap
  const y2 = y1 + slotH
  addVerticalSlot(segments, x, y1, y2, slotW)
}

/** 前墙顶部插舌耳槽 */
function addTuckEarSlots(
  segments: LineSegment[],
  cx: number,
  y: number,
  earW: number,
  earD: number,
  spacing: number,
) {
  const xL = cx - spacing / 2
  const xR = cx + spacing / 2
  addSegment(segments, xL - earW / 2, y, xL + earW / 2, y, 'cut')
  addSegment(segments, xL - earW / 2, y, xL - earW / 2, y + earD, 'cut')
  addSegment(segments, xL + earW / 2, y, xL + earW / 2, y + earD, 'cut')
  addSegment(segments, xR - earW / 2, y, xR + earW / 2, y, 'cut')
  addSegment(segments, xR - earW / 2, y, xR - earW / 2, y + earD, 'cut')
  addSegment(segments, xR + earW / 2, y, xR + earW / 2, y + earD, 'cut')
}

function buildLeftSideWall(
  segments: LineSegment[],
  W: number,
  H: number,
  yFront: number,
  yBot: number,
  yBack: number,
  cornerFlap: number,
  tabW: number,
  tabH: number,
) {
  const xOuter = 0
  const xCrease = W
  const yCornerBot = yFront
  const yCornerTop = yBot

  // 外轮廓 — 左侧墙组件
  addSegment(segments, xOuter, yCornerBot, xOuter, yCornerTop + cornerFlap, 'cut')
  addSegment(segments, xOuter, yCornerTop + cornerFlap, xCrease - tabW, yCornerTop + cornerFlap, 'cut')
  addSegment(segments, xCrease - tabW, yCornerTop + cornerFlap, xCrease - tabW, yCornerTop, 'cut')
  addSegment(segments, xCrease - tabW, yCornerTop, xCrease, yCornerTop, 'cut')

  // 顶角片
  addSegment(segments, xCrease, yCornerTop, xCrease, yCornerTop + cornerFlap, 'crease')
  addSegment(segments, xCrease, yCornerTop + cornerFlap, xOuter, yCornerTop + cornerFlap, 'crease')
  addSegment(segments, xOuter, yCornerTop + cornerFlap, xOuter, yBack, 'cut')

  // 后墙侧角片
  addSegment(segments, xOuter, yBack, xCrease, yBack, 'cut')
  addSegment(segments, xCrease, yBack, xCrease, yBack + H, 'crease')

  // 底角片
  addSegment(segments, xCrease, yCornerBot, xCrease, yCornerBot - cornerFlap, 'crease')
  addSegment(segments, xCrease, yCornerBot - cornerFlap, xOuter, yCornerBot - cornerFlap, 'cut')
  addSegment(segments, xOuter, yCornerBot - cornerFlap, xOuter, yCornerBot, 'cut')

  // 锁舌（内折侧墙）
  const tabY = yFront + (yBot - yFront) * 0.35
  addSegment(segments, xOuter, tabY, xOuter - tabW, tabY, 'cut')
  addSegment(segments, xOuter - tabW, tabY, xOuter - tabW, tabY + tabH, 'cut')
  addSegment(segments, xOuter - tabW, tabY + tabH, xOuter, tabY + tabH, 'cut')

  const tabY2 = yFront + (yBot - yFront) * 0.65
  addSegment(segments, xOuter, tabY2, xOuter - tabW, tabY2, 'cut')
  addSegment(segments, xOuter - tabW, tabY2, xOuter - tabW, tabY2 + tabH, 'cut')
  addSegment(segments, xOuter - tabW, tabY2 + tabH, xOuter, tabY2 + tabH, 'cut')

  // 侧墙折线
  addSegment(segments, xCrease, yFront, xCrease, yBot, 'crease')
  addSegment(segments, xOuter, yFront, xOuter, yBot, 'crease')
}

function buildRightSideWall(
  segments: LineSegment[],
  totalW: number,
  W: number,
  H: number,
  yFront: number,
  yBot: number,
  yBack: number,
  cornerFlap: number,
  tabW: number,
  tabH: number,
) {
  const xCrease = totalW - W
  const xOuter = totalW
  const yCornerBot = yFront
  const yCornerTop = yBot

  addSegment(segments, xOuter, yCornerBot, xOuter, yCornerTop + cornerFlap, 'cut')
  addSegment(segments, xOuter, yCornerTop + cornerFlap, xCrease + tabW, yCornerTop + cornerFlap, 'cut')
  addSegment(segments, xCrease + tabW, yCornerTop + cornerFlap, xCrease + tabW, yCornerTop, 'cut')
  addSegment(segments, xCrease + tabW, yCornerTop, xCrease, yCornerTop, 'cut')

  addSegment(segments, xCrease, yCornerTop, xCrease, yCornerTop + cornerFlap, 'crease')
  addSegment(segments, xCrease, yCornerTop + cornerFlap, xOuter, yCornerTop + cornerFlap, 'crease')
  addSegment(segments, xOuter, yCornerTop + cornerFlap, xOuter, yBack, 'cut')

  addSegment(segments, xOuter, yBack, xCrease, yBack, 'cut')
  addSegment(segments, xCrease, yBack, xCrease, yBack + H, 'crease')

  addSegment(segments, xCrease, yCornerBot, xCrease, yCornerBot - cornerFlap, 'crease')
  addSegment(segments, xCrease, yCornerBot - cornerFlap, xOuter, yCornerBot - cornerFlap, 'cut')
  addSegment(segments, xOuter, yCornerBot - cornerFlap, xOuter, yCornerBot, 'cut')

  const tabY = yFront + (yBot - yFront) * 0.35
  addSegment(segments, xOuter, tabY, xOuter + tabW, tabY, 'cut')
  addSegment(segments, xOuter + tabW, tabY, xOuter + tabW, tabY + tabH, 'cut')
  addSegment(segments, xOuter + tabW, tabY + tabH, xOuter, tabY + tabH, 'cut')

  const tabY2 = yFront + (yBot - yFront) * 0.65
  addSegment(segments, xOuter, tabY2, xOuter + tabW, tabY2, 'cut')
  addSegment(segments, xOuter + tabW, tabY2, xOuter + tabW, tabY2 + tabH, 'cut')
  addSegment(segments, xOuter + tabW, tabY2 + tabH, xOuter, tabY2 + tabH, 'cut')

  addSegment(segments, xCrease, yFront, xCrease, yBot, 'crease')
  addSegment(segments, xOuter, yFront, xOuter, yBot, 'crease')
}

function buildDustFlap(
  segments: LineSegment[],
  side: 'left' | 'right',
  xAttach: number,
  yLid0: number,
  yLid1: number,
  dustDepth: number,
  dustR: number,
) {
  const yMid = (yLid0 + yLid1) / 2
  if (side === 'left') {
    const xOuter = xAttach - dustDepth
    addSegment(segments, xAttach, yLid0, xAttach, yLid1, 'crease')
    addSegment(segments, xAttach, yLid1, xOuter + dustR, yLid1, 'cut')
    addArcApprox(segments, xOuter + dustR, yLid1 - dustR, dustR, 90, 180, 'cut')
    addSegment(segments, xOuter, yLid1 - dustR, xOuter, yLid0 + dustR, 'cut')
    addArcApprox(segments, xOuter + dustR, yLid0 + dustR, dustR, 180, 270, 'cut')
    addSegment(segments, xOuter + dustR, yLid0, xAttach, yLid0, 'cut')
    addSegment(segments, xAttach, yLid0, xAttach, yLid1, 'crease')
  } else {
    const xOuter = xAttach + dustDepth
    addSegment(segments, xAttach, yLid0, xAttach, yLid1, 'crease')
    addSegment(segments, xAttach, yLid0, xOuter - dustR, yLid0, 'cut')
    addArcApprox(segments, xOuter - dustR, yLid0 + dustR, dustR, 270, 360, 'cut')
    addSegment(segments, xOuter, yLid0 + dustR, xOuter, yLid1 - dustR, 'cut')
    addArcApprox(segments, xOuter - dustR, yLid1 - dustR, dustR, 0, 90, 'cut')
    addSegment(segments, xOuter - dustR, yLid1, xAttach, yLid1, 'cut')
  }
}

function buildTuckFlap(
  segments: LineSegment[],
  cx: number,
  yBase: number,
  tuckW: number,
  tuckH: number,
  tuckR: number,
  earW: number,
  earH: number,
) {
  const xL = cx - tuckW / 2
  const xR = cx + tuckW / 2
  const yTop = yBase + tuckH

  addSegment(segments, xL + tuckR, yBase, xR - tuckR, yBase, 'crease')
  addArcApprox(segments, xR - tuckR, yBase + tuckR, tuckR, 270, 0, 'cut')
  addSegment(segments, xR, yBase + tuckR, xR, yTop - tuckR, 'cut')
  addArcApprox(segments, xR - tuckR, yTop - tuckR, tuckR, 0, 90, 'cut')
  addSegment(segments, xR - tuckR, yTop, xL + tuckR, yTop, 'cut')
  addArcApprox(segments, xL + tuckR, yTop - tuckR, tuckR, 90, 180, 'cut')
  addSegment(segments, xL, yTop - tuckR, xL, yBase + tuckR, 'cut')
  addArcApprox(segments, xL + tuckR, yBase + tuckR, tuckR, 180, 270, 'cut')

  // 插舌侧耳
  const earXL = cx - tuckW * 0.35
  const earXR = cx + tuckW * 0.35
  addSegment(segments, earXL - earW / 2, yBase, earXL + earW / 2, yBase, 'cut')
  addSegment(segments, earXL - earW / 2, yBase, earXL - earW / 2, yBase - earH, 'cut')
  addSegment(segments, earXL + earW / 2, yBase, earXL + earW / 2, yBase - earH, 'cut')
  addSegment(segments, earXR - earW / 2, yBase, earXR + earW / 2, yBase, 'cut')
  addSegment(segments, earXR - earW / 2, yBase, earXR - earW / 2, yBase - earH, 'cut')
  addSegment(segments, earXR + earW / 2, yBase, earXR + earW / 2, yBase - earH, 'cut')
}

export function build0427Segments(geo: DielineGeometry): LineSegment[] {
  const L = geo.manufacturing.length
  const W = geo.manufacturing.width
  const H = geo.manufacturing.height
  const t = geo.thicknessMm

  const { blankWidthMm: totalW, blankHeightMm: totalH, tuckHeightMm: tuckH } = compute0427BlankSize(L, W, H, t)

  const xL = W
  const xR = W + L
  const cx = W + L / 2

  const yFront0 = 0
  const yFront1 = H
  const yBot0 = H
  const yBot1 = H + W
  const yBack0 = yBot1
  const yBack1 = yBot1 + H
  const yLid0 = yBack1
  const yLid1 = yBack1 + W
  const yTuck0 = yLid1
  const yTuck1 = yLid1 + tuckH

  const tuckR = Math.min(0.6 * H, 10, tuckH * 0.35)
  const dustDepth = Math.max(W * 0.42, H * 1.1)
  const dustR = Math.min(W * 0.12, H * 0.5, 15)
  const cornerFlap = Math.max(H * 0.85, H - t)
  const slotW = Math.max(6, W * 0.055)
  const slotH = Math.max(10, H * 0.55)
  const slotGap = Math.max(4, H * 0.12)
  const tabW = Math.max(5, W * 0.045)
  const tabH = Math.max(8, H * 0.45)
  const earW = Math.max(5, W * 0.04)
  const earH = Math.max(4, H * 0.2)
  const tuckW = L * 0.55
  const earSpacing = L * 0.38

  const segments: LineSegment[] = []
  addBleedRect(segments, totalW, totalH)

  // 前墙
  addSegment(segments, xL, yFront0, xR, yFront0, 'cut')
  addSegment(segments, xL, yFront0, xL, yFront1, 'crease')
  addSegment(segments, xR, yFront0, xR, yFront1, 'crease')
  addSegment(segments, xL, yFront1, xR, yFront1, 'crease')
  addTuckEarSlots(segments, cx, yFront1, earW, earH, earSpacing)

  // 底板
  addSegment(segments, xL, yBot0, xR, yBot0, 'crease')
  addSegment(segments, xL, yBot1, xR, yBot1, 'crease')
  addLockSlots(segments, xL + slotGap + slotW, yBot0, slotH, slotW, slotGap)
  addLockSlots(segments, xL + slotGap + slotW * 2.5, yBot0, slotH, slotW, slotGap * 2.5)
  addLockSlots(segments, xR - slotGap - slotW, yBot0, slotH, slotW, slotGap)
  addLockSlots(segments, xR - slotGap - slotW * 2.5, yBot0, slotH, slotW, slotGap * 2.5)

  // 后墙
  addSegment(segments, xL, yBack0, xR, yBack0, 'crease')
  addSegment(segments, xL, yBack1, xR, yBack1, 'crease')

  // 盖板主体
  addSegment(segments, xL, yLid0, xR, yLid0, 'crease')
  addSegment(segments, xL, yLid1, xR, yLid1, 'crease')

  // 防尘翼
  buildDustFlap(segments, 'left', xL, yLid0, yLid1, dustDepth, dustR)
  buildDustFlap(segments, 'right', xR, yLid0, yLid1, dustDepth, dustR)

  // 插舌
  buildTuckFlap(segments, cx, yTuck0, tuckW, tuckH, tuckR, earW, earH)

  // 侧墙组件
  buildLeftSideWall(segments, W, H, yBot0, yBot1, yBack0, cornerFlap, tabW, tabH)
  buildRightSideWall(segments, totalW, W, H, yBot0, yBot1, yBack0, cornerFlap, tabW, tabH)

  // 主折线（竖向）
  ;[xL, xR].forEach((x) => {
    addSegment(segments, x, yFront0, x, yTuck1, 'crease')
  })

  // 顶边外轮廓
  addSegment(segments, 0, yTuck1, totalW, yTuck1, 'cut')

  return segments
}
