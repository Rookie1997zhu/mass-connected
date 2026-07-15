import fs from 'node:fs/promises'

const materials = ['fr4', 'fpc', 'aluminum']
const merged = []
for (const material of materials) {
  const path = `scripts/jlc-cn-pcb-v10-acceptance-samples-${material}.json`
  const rows = JSON.parse(await fs.readFile(path, 'utf8'))
  merged.push(...rows)
}
await fs.writeFile(
  'scripts/jlc-cn-pcb-v10-acceptance-samples.json',
  `${JSON.stringify(merged, null, 2)}\n`,
)
console.log(JSON.stringify({ merged: merged.length, byMaterial: Object.fromEntries(
  materials.map((material) => [
    material,
    merged.filter((row) => (row.materialKey || row.material_key) === material).length,
  ]),
) }))
