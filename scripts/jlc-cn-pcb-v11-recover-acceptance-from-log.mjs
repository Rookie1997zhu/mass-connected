/**
 * Reconstruct v11 acceptance samples from the successful sampling terminal log,
 * merging with any current partial samples.
 */
import fs from 'node:fs/promises'

const LOG = process.argv[2]
  || 'C:/Users/ROG STRIX/.cursor/projects/c-Users-ROG-STRIX-Desktop-OEM-co/terminals/745548.txt'
const TARGETS = 'scripts/jlc-cn-pcb-v11-acceptance-targets.json'
const OUTPUT = 'scripts/jlc-cn-pcb-v11-acceptance-samples.json'

const targets = JSON.parse(await fs.readFile(TARGETS, 'utf8'))
const byId = new Map(targets.map((row) => [row.id, row]))
const log = await fs.readFile(LOG, 'utf8')
const recovered = new Map()

for (const line of log.split(/\r?\n/)) {
  if (!/"price"\s*:/.test(line) || !/JLC-CN-PCB-V11-ACC-/.test(line)) continue
  if (/status":"failed"|errorClass|"error":/.test(line) && !/"price":/.test(line)) continue
  let row
  try {
    row = JSON.parse(line)
  } catch {
    continue
  }
  if (!row?.id || !(Number(row.price) > 0)) continue
  if (row.status === 'failed' || row.error) continue
  const target = byId.get(row.id)
  if (!target) continue
  recovered.set(row.id, {
    ...target,
    id: row.id,
    baseSampleId: target.baseSampleId || String(row.id).replace(/-R\d+$/, ''),
    priceSource: 'dom',
    domPriceCny: Number(row.price),
    jlcPriceCny: Number(row.price),
    apiPriceCny: Number(row.price),
    quarantined: false,
    recoveredFromLog: true,
    recoveredAt: new Date().toISOString(),
  })
}

let existing = []
try {
  existing = JSON.parse(await fs.readFile(OUTPUT, 'utf8'))
} catch {
  existing = []
}
for (const row of existing) {
  if (row?.id && Number(row.domPriceCny || row.jlcPriceCny) > 0 && row.priceSource === 'dom') {
    if (!recovered.has(row.id) || !recovered.get(row.id).recoveredFromLog) {
      recovered.set(row.id, row)
    }
  }
}

const merged = [...recovered.values()].sort((left, right) => String(left.id).localeCompare(String(right.id)))
await fs.writeFile(OUTPUT, `${JSON.stringify(merged, null, 2)}\n`)
const byMaterial = {}
for (const row of merged) {
  const material = row.materialKey || row.material_key
  byMaterial[material] = (byMaterial[material] || 0) + 1
}
console.log(JSON.stringify({
  recoveredFromLog: [...recovered.values()].filter((row) => row.recoveredFromLog).length,
  merged: merged.length,
  byMaterial,
}, null, 2))
