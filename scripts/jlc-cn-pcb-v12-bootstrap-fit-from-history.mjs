/**
 * Seed v12 fit sample files from historical non-ACC samples that pass SAFE quantity whitelist.
 * Does not touch acceptance; only fills missing fit rows so build-model can start earlier.
 */
import fs from 'node:fs/promises'
import { isDiagnosticOnly } from './jlc-cn-pcb-v12-spec-key.mjs'

const SAFE = {
  fr4: new Set([5, 10, 15, 20, 30, 100, 150, 200]),
  fpc: new Set([5, 10, 15, 20, 50, 100]),
  aluminum: new Set([5, 10, 15, 20, 30, 50, 150, 200]),
}

const SOURCES = [
  'scripts/jlc-cn-pcb-v11-fr4-fit-samples.json',
  'scripts/jlc-cn-pcb-v11-fpc-fit-samples.json',
  'scripts/jlc-cn-pcb-v11-tuning-holdout-samples.json',
  'scripts/jlc-cn-pcb-v11-process-holdout-samples.json',
  'scripts/jlc-cn-pcb-v10-acceptance-samples-fr4.json',
  'scripts/jlc-cn-pcb-v10-acceptance-samples-fpc.json',
  'scripts/jlc-cn-pcb-v10-acceptance-samples-aluminum.json',
  'scripts/jlc-cn-pcb-v9-boundary-fit-samples.json',
]

const OUT = {
  fr4: 'scripts/jlc-cn-pcb-v12-fr4-fit-samples.json',
  fpc: 'scripts/jlc-cn-pcb-v12-fpc-fit-samples.json',
  aluminum: 'scripts/jlc-cn-pcb-v12-aluminum-fit-samples.json',
}

async function readRows(pathname) {
  try {
    const raw = JSON.parse(await fs.readFile(pathname, 'utf8'))
    return Array.isArray(raw) ? raw : (raw.rows || raw.samples || [])
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function priceOk(row) {
  const price = Number(row.domPriceCny ?? row.jlcPriceCny ?? row.jlc_price_cny)
  return row.priceSource === 'dom' && price > 0 && !row.error
}

function materialOf(row) {
  return row.materialKey || row.material_key
}

function geoKey(row) {
  return [
    materialOf(row),
    Number(row.layers),
    Number(row.widthMm ?? row.width_mm),
    Number(row.heightMm ?? row.height_mm),
    Number(row.quantity),
  ].join('|')
}

const buckets = { fr4: new Map(), fpc: new Map(), aluminum: new Map() }

for (const source of SOURCES) {
  const rows = await readRows(source)
  for (const row of rows) {
    if (isDiagnosticOnly(row) || !priceOk(row)) continue
    // Never bootstrap from final acceptance IDs.
    if (/V(?:7|8|9|10|11)-ACC/.test(String(row.id || ''))) continue
    const material = materialOf(row)
    if (!SAFE[material]?.has(Number(row.quantity))) continue
    const key = geoKey(row)
    const bucket = buckets[material]
    if (!bucket.has(key)) bucket.set(key, [])
    bucket.get(key).push({
      ...row,
      samplingVersion: 'v12-bootstrap',
      sampleRole: 'fit_bootstrap',
      jlcPriceCny: Number(row.domPriceCny ?? row.jlcPriceCny ?? row.jlc_price_cny),
    })
  }
}

const summary = {}
for (const [material, map] of Object.entries(buckets)) {
  const existing = await readRows(OUT[material])
  const byId = new Map(existing.map((row) => [row.id, row]))
  let added = 0
  let index = existing.length
  for (const group of map.values()) {
    // Prefer up to 3 repeats if available; otherwise single seeded row with synthetic repeats.
    const priced = group.slice(0, 3)
    const baseId = `JLC-CN-PCB-V12-BOOT-${material.toUpperCase()}-${String(++index).padStart(3, '0')}`
    for (let i = 0; i < Math.max(1, priced.length); i += 1) {
      const src = priced[i] || priced[0]
      const id = `${baseId}-R${i + 1}`
      if (byId.has(id)) continue
      byId.set(id, {
        ...src,
        id,
        baseSampleId: baseId,
        repeatIndex: i + 1,
        materialKey: material,
      })
      added += 1
    }
  }
  const outRows = [...byId.values()]
  await fs.writeFile(OUT[material], `${JSON.stringify(outRows, null, 2)}\n`, 'utf8')
  summary[material] = { total: outRows.length, added }
}

console.log(JSON.stringify({ ok: true, summary }, null, 2))
