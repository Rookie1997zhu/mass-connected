import fs from 'node:fs/promises'

const outputPath = process.argv[2]
const inputPaths = process.argv.slice(3)
if (!outputPath || inputPaths.length < 2) {
  throw new Error('usage: node jlc-cn-pcb-merge-v4-samples.mjs <output> <input...>')
}

const samplesById = new Map()
for (const inputPath of inputPaths) {
  const samples = JSON.parse(await fs.readFile(inputPath, 'utf8'))
  for (const sample of samples) {
    if (!sample.id) continue
    samplesById.set(sample.id, sample)
  }
}

const merged = [...samplesById.values()].sort((a, b) => String(a.id).localeCompare(String(b.id)))
await fs.writeFile(outputPath, JSON.stringify(merged, null, 2), 'utf8')
console.log(JSON.stringify({
  inputs: inputPaths.length,
  samples: merged.length,
  outputPath,
}, null, 2))
