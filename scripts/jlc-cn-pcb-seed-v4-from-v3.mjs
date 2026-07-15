import fs from 'node:fs/promises'

const targetPath = process.argv[2]
const sourcePath = process.argv[3]
const outputPath = process.argv[4]

if (!targetPath || !sourcePath || !outputPath) {
  throw new Error('usage: node jlc-cn-pcb-seed-v4-from-v3.mjs <targets> <v3-samples> <v4-output>')
}

const targets = JSON.parse(await fs.readFile(targetPath, 'utf8'))
const source = JSON.parse(await fs.readFile(sourcePath, 'utf8'))

function specKey(sample) {
  return [
    sample.materialKey || 'fr4',
    Number(sample.layers),
    Number(sample.widthMm),
    Number(sample.heightMm),
    Number(sample.quantity),
    Number(sample.repeatIndex || 1),
  ].join('|')
}

const sourceBySpec = new Map(
  source
    .filter((sample) => sample.priceSource === 'dom' && Number(sample.domPriceCny) > 0 && !sample.error)
    .map((sample) => [specKey(sample), sample]),
)

const seeded = []
for (const target of targets) {
  const prior = sourceBySpec.get(specKey(target))
  if (!prior) continue
  seeded.push({
    ...prior,
    ...target,
    samplingVersion: 'v4',
    notes: [prior.notes, 'reused verified v3 live DOM sample for v4 incremental matrix']
      .filter(Boolean)
      .join('; '),
  })
}

await fs.writeFile(outputPath, JSON.stringify(seeded, null, 2), 'utf8')
console.log(JSON.stringify({
  targets: targets.length,
  source: source.length,
  seeded: seeded.length,
  remaining: targets.length - seeded.length,
  outputPath,
}, null, 2))
