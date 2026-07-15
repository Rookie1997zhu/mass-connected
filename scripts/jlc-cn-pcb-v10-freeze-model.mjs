import crypto from 'node:crypto'
import fs from 'node:fs/promises'
import { runtimePreflightReport } from './jlc-cn-pcb-v10-spec-key.mjs'
import { estimateV10 } from './jlc-cn-pcb-v10-model.mjs'

const candidatePath = 'scripts/jlc-cn-pcb-v10-candidate-price-list.json'
const frozenPath = 'scripts/jlc-cn-pcb-v10-model-fingerprint.json'
const candidateBytes = await fs.readFile(candidatePath)
const candidate = JSON.parse(candidateBytes.toString('utf8'))
const targets = JSON.parse(await fs.readFile('scripts/jlc-cn-pcb-v10-acceptance-targets.json', 'utf8'))
const uniqueTargets = [...new Map(targets.map((row) => [
  row.baseSampleId,
  { ...row, id: row.baseSampleId },
])).values()]
const runtimePreflight = runtimePreflightReport(
  candidate.rows || [],
  candidate.estimator,
  uniqueTargets,
  estimateV10,
)
if (
  candidate.validationStatus !== 'passed'
  || !['fr4', 'fpc', 'aluminum'].every(
    (material) => candidate.estimatorEnabledMaterials?.includes(material),
  )
  || !runtimePreflight.ok
) {
  await fs.writeFile(
    'scripts/jlc-cn-pcb-v10-runtime-preflight-report.json',
    `${JSON.stringify(runtimePreflight, null, 2)}\n`,
  )
  throw new Error('refusing to freeze v10 model before all materials and final targets are runnable')
}
const hash = `sha256_${crypto.createHash('sha256').update(candidateBytes).digest('hex')}`
const acceptanceFingerprint = JSON.parse(
  await fs.readFile('scripts/jlc-cn-pcb-v10-acceptance-fingerprint.json', 'utf8'),
).hash
try {
  const frozen = JSON.parse(await fs.readFile(frozenPath, 'utf8'))
  if (frozen.hash !== hash || frozen.acceptanceFingerprint !== acceptanceFingerprint) {
    throw new Error('v10 candidate or acceptance target changed after freeze')
  }
  console.log(JSON.stringify({ status: 'already_frozen', ...frozen }, null, 2))
} catch (error) {
  if (error.code !== 'ENOENT') throw error
  const frozen = {
    frozenAt: new Date().toISOString(),
    hash,
    candidatePath,
    acceptanceFingerprint,
    runtimePreflight: {
      ok: runtimePreflight.ok,
      targetCount: runtimePreflight.rows.length,
      failedCount: runtimePreflight.failed.length,
    },
    note: 'Do not rebuild or retune after final acceptance sampling starts.',
  }
  await fs.writeFile(frozenPath, `${JSON.stringify(frozen, null, 2)}\n`)
  await fs.writeFile(
    'scripts/jlc-cn-pcb-v10-runtime-preflight-report.json',
    `${JSON.stringify(runtimePreflight, null, 2)}\n`,
  )
  console.log(JSON.stringify({ status: 'frozen', ...frozen }, null, 2))
}
