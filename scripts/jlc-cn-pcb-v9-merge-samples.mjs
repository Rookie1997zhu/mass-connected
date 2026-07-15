import fs from 'node:fs/promises'

const output = process.argv[2]
const inputs = process.argv.slice(3)
if (!output || !inputs.length) {
  throw new Error('usage: node jlc-cn-pcb-v9-merge-samples.mjs <output> <input...>')
}

const merged = new Map()
for (const input of inputs) {
  try {
    const rows = JSON.parse(await fs.readFile(input, 'utf8'))
    for (const row of rows) {
      if (!row?.id) continue
      const existing = merged.get(row.id)
      const rowIsUsable = row.priceSource === 'dom' && Number(row.domPriceCny) > 0 && !row.error
      const existingIsUsable = existing?.priceSource === 'dom'
        && Number(existing.domPriceCny) > 0
        && !existing.error
      if (!existing || rowIsUsable || !existingIsUsable) merged.set(row.id, row)
    }
  } catch (error) {
    if (error.code !== 'ENOENT') throw error
  }
}

const rows = [...merged.values()].sort((a, b) => String(a.id).localeCompare(String(b.id)))
const temp = `${output}.tmp`
await fs.writeFile(temp, `${JSON.stringify(rows, null, 2)}\n`, 'utf8')
await fs.rm(output, { force: true })
await fs.rename(temp, output)
console.log(JSON.stringify({
  output,
  rows: rows.length,
  byMaterial: rows.reduce((counts, row) => {
    const material = row.materialKey || row.material_key || 'unknown'
    counts[material] = (counts[material] || 0) + 1
    return counts
  }, {}),
}, null, 2))
