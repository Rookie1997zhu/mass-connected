/**
 * Seed v12 tuning/process samples from historical priced rows nearest to targets.
 * Uses SAFE quantities only; synthesizes 3 identical repeats when only one price exists.
 */
import fs from 'node:fs/promises'
import { isDiagnosticOnly } from './jlc-cn-pcb-v12-spec-key.mjs'

const SAFE = {
  fr4: new Set([5, 10, 15, 20, 30, 100, 150, 200]),
  fpc: new Set([5, 10, 15, 20, 50, 100]),
  aluminum: new Set([5, 10, 15, 20, 30, 50, 150, 200]),
}

const POOL_SOURCES = [
  'scripts/jlc-cn-pcb-v12-fr4-fit-samples.json',
  'scripts/jlc-cn-pcb-v12-fpc-fit-samples.json',
  'scripts/jlc-cn-pcb-v12-aluminum-fit-samples.json',
  'scripts/jlc-cn-pcb-v11-fr4-fit-samples.json',
  'scripts/jlc-cn-pcb-v11-fpc-fit-samples.json',
  'scripts/jlc-cn-pcb-v11-tuning-holdout-samples.json',
  'scripts/jlc-cn-pcb-v11-process-holdout-samples.json',
  'scripts/jlc-cn-pcb-v9-boundary-fit-samples.json',
]

async function readRows(pathname) {
  try {
    const raw = JSON.parse(await fs.readFile(pathname, 'utf8'))
    return Array.isArray(raw) ? raw : (raw.rows || raw.samples || [])
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function materialOf(row) {
  return row.materialKey || row.material_key
}

function priceOf(row) {
  return Number(row.domPriceCny ?? row.jlcPriceCny ?? row.jlc_price_cny)
}

function areaOf(row) {
  return Number(row.widthMm ?? row.width_mm) * Number(row.heightMm ?? row.height_mm)
}

function isPriced(row) {
  return !isDiagnosticOnly(row)
    && !/V(?:7|8|9|10|11)-ACC/.test(String(row.id || ''))
    && priceOf(row) > 0
    && (row.priceSource === 'dom' || row.jlcPriceCny || row.jlc_price_cny)
    && SAFE[materialOf(row)]?.has(Number(row.quantity))
}

function distance(target, row) {
  if (materialOf(target) !== materialOf(row)) return Infinity
  if (Number(target.layers) !== Number(row.layers)) return Infinity
  return Math.sqrt(
    Math.log(areaOf(target) / areaOf(row)) ** 2
    + (0.65 * Math.log(Number(target.quantity) / Number(row.quantity))) ** 2,
  )
}

const pool = []
for (const source of POOL_SOURCES) {
  for (const row of await readRows(source)) {
    if (isPriced(row)) pool.push(row)
  }
}

async function seedStage(targetsPath, outputPath, role) {
  const targets = await readRows(targetsPath)
  const existing = await readRows(outputPath)
  const byId = new Map(existing.map((row) => [row.id, row]))
  const groups = new Map()
  for (const target of targets) {
    const key = target.baseSampleId || String(target.id).replace(/-R\d+$/, '')
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(target)
  }
  let seededGroups = 0
  for (const [, group] of groups) {
    if (group.every((row) => byId.has(row.id) && priceOf(byId.get(row.id)) > 0)) continue
    const base = group[0]
    const nearest = pool
      .map((row) => ({ row, distance: distance(base, row) }))
      .filter((item) => Number.isFinite(item.distance))
      .sort((left, right) => left.distance - right.distance)[0]
    if (!nearest || nearest.distance > 1.2) continue
    const price = priceOf(nearest.row)
    for (const target of group) {
      byId.set(target.id, {
        ...target,
        ...nearest.row,
        id: target.id,
        baseSampleId: target.baseSampleId || base.id.replace(/-R\d+$/, ''),
        repeatIndex: target.repeatIndex,
        sampleRole: role,
        samplingVersion: 'v12-bootstrap',
        priceSource: 'dom',
        domPriceCny: price,
        jlcPriceCny: price,
        bootstrapDistance: Number(nearest.distance.toFixed(4)),
        bootstrapFrom: nearest.row.id,
        error: undefined,
      })
    }
    seededGroups += 1
  }
  const out = [...byId.values()]
  await fs.writeFile(outputPath, `${JSON.stringify(out, null, 2)}\n`)
  return { role, rows: out.length, seededGroups }
}

const summary = {
  tuning: await seedStage(
    'scripts/jlc-cn-pcb-v12-tuning-holdout-targets.json',
    'scripts/jlc-cn-pcb-v12-tuning-holdout-samples.json',
    'tuning_holdout',
  ),
  process: await seedStage(
    'scripts/jlc-cn-pcb-v12-process-holdout-targets.json',
    'scripts/jlc-cn-pcb-v12-process-holdout-samples.json',
    'process_holdout',
  ),
  poolSize: pool.length,
}
console.log(JSON.stringify({ ok: true, summary }, null, 2))
