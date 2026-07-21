import fs from 'node:fs/promises'
import {
  assertUnconsumedFingerprint,
  fingerprintTargets,
  markDiagnostic,
  runtimePreflightReport,
  splitIntegrityReport,
  verifyFrozenFingerprint,
} from './jlc-cn-pcb-v12-spec-key.mjs'
import { estimateV12 } from './jlc-cn-pcb-v12-model.mjs'

async function readJson(pathname, fallback = []) {
  try {
    const raw = JSON.parse(await fs.readFile(pathname, 'utf8'))
    if (Array.isArray(fallback)) return Array.isArray(raw) ? raw : (raw.rows || raw.samples || [])
    return raw
  } catch (error) {
    if (error.code === 'ENOENT') return fallback
    throw error
  }
}

function uniqueTargets(rows) {
  return [...new Map(rows.map((row) => [
    row.baseSampleId || row.id.replace(/-R\d+$/, ''),
    { ...row, id: row.baseSampleId || row.id.replace(/-R\d+$/, '') },
  ])).values()]
}

const historicalFit = uniqueTargets(
  await readJson('scripts/jlc-cn-pcb-v9-boundary-fit-targets.json'),
)
const fr4Fit = uniqueTargets(await readJson('scripts/jlc-cn-pcb-v12-fr4-fit-targets.json'))
const fpcFit = uniqueTargets(await readJson('scripts/jlc-cn-pcb-v12-fpc-fit-targets.json'))
const aluminumFit = uniqueTargets(await readJson('scripts/jlc-cn-pcb-v12-aluminum-fit-targets.json'))
const tuning = uniqueTargets(await readJson('scripts/jlc-cn-pcb-v12-tuning-holdout-targets.json'))
const processHoldout = uniqueTargets(
  await readJson('scripts/jlc-cn-pcb-v12-process-holdout-targets.json'),
)
const finalAcceptance = uniqueTargets(await readJson('scripts/jlc-cn-pcb-v12-acceptance-targets.json'))
const diagnostic = [
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v7-acceptance-targets.json'), 'v7_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v8-acceptance-targets.json'), 'v8_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v9-acceptance-targets.json'), 'v9_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v10-diagnostic-v9-acceptance.json'), 'v9_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v10-acceptance-targets.json'), 'v10_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v11-acceptance-targets.json'), 'v11_final_acceptance_do_not_train'),
  ...markDiagnostic(await readJson('scripts/jlc-cn-pcb-v12-diagnostic-v11-acceptance.json'), 'v11_final_acceptance_do_not_train'),
]
const integrity = splitIntegrityReport({
  fit: [...historicalFit, ...fr4Fit, ...fpcFit, ...aluminumFit],
  tuningHoldout: tuning,
  processHoldout,
  finalAcceptance,
  diagnostic,
})
const frozen = await readJson('scripts/jlc-cn-pcb-v12-acceptance-fingerprint.json', {})
const fingerprintCheck = verifyFrozenFingerprint(fingerprintTargets(finalAcceptance), frozen)
const consumption = await readJson('scripts/jlc-cn-pcb-v12-acceptance-consumption.json', {})
const consumptionCheck = assertUnconsumedFingerprint(frozen, consumption, { hard: false })
const candidate = await readJson('scripts/jlc-cn-pcb-v12-candidate-price-list.json', {})
const runtimePreflight = runtimePreflightReport(
  candidate.rows || [],
  candidate.estimator,
  finalAcceptance,
  estimateV12,
)
const requireRuntime = process.env.JLC_REQUIRE_RUNTIME_PREFLIGHT === '1'
const report = {
  generatedAt: new Date().toISOString(),
  ok: integrity.ok
    && fingerprintCheck.ok
    && consumptionCheck.ok
    && (!requireRuntime || runtimePreflight.ok),
  readyForFinalAcceptance: integrity.ok
    && fingerprintCheck.ok
    && consumptionCheck.ok
    && candidate.validationStatus === 'passed'
    && runtimePreflight.ok,
  ...integrity,
  fingerprintCheck,
  consumptionCheck,
  runtimePreflight,
}
await fs.writeFile(
  'scripts/jlc-cn-pcb-v12-assert-split-report.json',
  `${JSON.stringify(report, null, 2)}\n`,
)
console.log(JSON.stringify(report, null, 2))
if (!report.ok) process.exit(1)
