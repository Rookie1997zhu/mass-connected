import crypto from 'node:crypto'
import fs from 'node:fs/promises'

const candidatePath = 'scripts/jlc-cn-pcb-v9-candidate-price-list.json'
const frozenPath = 'scripts/jlc-cn-pcb-v9-model-fingerprint.json'
const candidateBytes = await fs.readFile(candidatePath)
const candidate = JSON.parse(candidateBytes.toString('utf8'))
if (
  candidate.validationStatus !== 'passed'
  || !['fr4', 'fpc', 'aluminum'].every(
    (material) => candidate.estimatorEnabledMaterials?.includes(material),
  )
) {
  throw new Error('refusing to freeze incomplete v9 candidate model')
}
const hash = `sha256_${crypto.createHash('sha256').update(candidateBytes).digest('hex')}`
try {
  const frozen = JSON.parse(await fs.readFile(frozenPath, 'utf8'))
  if (frozen.hash !== hash) {
    throw new Error('v9 candidate changed after model freeze; generate a new version and acceptance set')
  }
  console.log(JSON.stringify({ status: 'already_frozen', ...frozen }, null, 2))
} catch (error) {
  if (error.code !== 'ENOENT') throw error
  const frozen = {
    frozenAt: new Date().toISOString(),
    hash,
    candidatePath,
    acceptanceFingerprint: JSON.parse(
      await fs.readFile('scripts/jlc-cn-pcb-v9-acceptance-fingerprint.json', 'utf8'),
    ).hash,
    note: 'Do not rebuild or retune after final acceptance sampling starts.',
  }
  await fs.writeFile(frozenPath, `${JSON.stringify(frozen, null, 2)}\n`, 'utf8')
  console.log(JSON.stringify({ status: 'frozen', ...frozen }, null, 2))
}
