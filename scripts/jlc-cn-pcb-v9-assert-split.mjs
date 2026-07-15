import fs from 'node:fs/promises'
import {
  assertUnconsumedFingerprint,
  fingerprintTargets,
  markDiagnostic,
  splitIntegrityReport,
  verifyFrozenFingerprint,
} from './jlc-cn-pcb-v9-spec-key.mjs'

async function readJson(path, fallback = []) {
  try {
    const raw = JSON.parse(await fs.readFile(path, 'utf8'))
    if (Array.isArray(fallback)) return Array.isArray(raw) ? raw : (raw.rows || raw.samples || [])
    return raw
  } catch (error) {
    if (error.code === 'ENOENT') return fallback
    throw error
  }
}

const fit = await readJson('scripts/jlc-cn-pcb-v9-boundary-fit-targets.json')
const tuningHoldout = await readJson('scripts/jlc-cn-pcb-v9-tuning-holdout-targets.json')
const processHoldout = await readJson('scripts/jlc-cn-pcb-v9-process-holdout-targets.json')
const finalAcceptance = await readJson('scripts/jlc-cn-pcb-v9-acceptance-targets.json')
const diagnostic = [
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v7-acceptance-targets.json'), 'v7_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v7-acceptance-samples.json'), 'v7_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v8-acceptance-targets.json'), 'v8_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v8-acceptance-samples.json'), 'v8_final_acceptance_do_not_train'),
]

const integrity = splitIntegrityReport({
  fit,
  tuningHoldout,
  processHoldout,
  finalAcceptance,
  diagnostic,
})
const frozen = await readJson('scripts/jlc-cn-pcb-v9-acceptance-fingerprint.json', {})
const currentFingerprint = fingerprintTargets(finalAcceptance)
const fingerprintCheck = verifyFrozenFingerprint(currentFingerprint, frozen)
const consumption = await readJson('scripts/jlc-cn-pcb-v9-acceptance-consumption.json', {})
const consumptionCheck = assertUnconsumedFingerprint(frozen, consumption, { hard: false })
const report = {
  generatedAt: new Date().toISOString(),
  ok: integrity.ok && fingerprintCheck.ok && consumptionCheck.ok,
  ...integrity,
  fingerprintCheck,
  consumptionCheck,
}

await fs.writeFile(
  'scripts/jlc-cn-pcb-v9-assert-split-report.json',
  `${JSON.stringify(report, null, 2)}\n`,
  'utf8',
)
console.log(JSON.stringify(report, null, 2))
if (!report.ok) process.exit(1)
