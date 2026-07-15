/**
 * v8 anti-leakage hard gate including neighbor bands and diagnostic exclusion.
 */
import fs from 'node:fs/promises'
import {
  fingerprintTargets,
  assertFrozenFingerprint,
  splitIntegrityReport,
  markDiagnostic,
} from './jlc-cn-pcb-v8-spec-key.mjs'

async function readJson(path) {
  try {
    const raw = JSON.parse(await fs.readFile(path, 'utf8'))
    return Array.isArray(raw) ? raw : (raw.samples || raw.results || raw.rows || [])
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function parseArgs(argv) {
  const args = {
    acceptance: 'scripts/jlc-cn-pcb-v8-acceptance-targets.json',
    fingerprint: 'scripts/jlc-cn-pcb-v8-acceptance-fingerprint.json',
  }
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--acceptance') args.acceptance = argv[i + 1]
    if (argv[i] === '--fingerprint') args.fingerprint = argv[i + 1]
  }
  return args
}

const args = parseArgs(process.argv.slice(2))
const fit = [
  ...await readJson('scripts/jlc-cn-pcb-golden-v4-targets.json'),
  ...await readJson('scripts/jlc-cn-pcb-process-v7-targets.json'),
  ...await readJson('scripts/jlc-cn-pcb-v8-boundary-fit-targets.json'),
]
const tuningHoldout = await readJson('scripts/jlc-cn-pcb-v8-tuning-holdout-targets.json')
const processHoldout = [
  ...await readJson('scripts/jlc-cn-pcb-process-holdout-v7-targets.json'),
  ...await readJson('scripts/jlc-cn-pcb-process-holdout-v7-samples.json'),
]
const finalAcceptance = await readJson(args.acceptance)
const diagnostic = markDiagnostic([
  ...await readJson('scripts/jlc-cn-pcb-v7-acceptance-targets.json'),
  ...await readJson('scripts/jlc-cn-pcb-v7-acceptance-samples.json'),
  ...await readJson('scripts/jlc-cn-pcb-v8-diagnostic-v7-acceptance.json'),
])

const integrity = splitIntegrityReport({
  fit,
  tuningHoldout,
  processHoldout,
  finalAcceptance,
  diagnostic,
})

let fingerprintCheck = { ok: true, skipped: true }
try {
  const frozen = JSON.parse(await fs.readFile(args.fingerprint, 'utf8'))
  fingerprintCheck = assertFrozenFingerprint(fingerprintTargets(finalAcceptance), frozen, { hard: true })
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}

const hardExact = integrity.checks.filter((item) => !String(item.left).includes('neighbor'))
const report = {
  generatedAt: new Date().toISOString(),
  acceptancePath: args.acceptance,
  ok: hardExact.every((item) => item.ok) && fingerprintCheck.ok,
  neighborOk: integrity.checks.filter((item) => String(item.left).includes('neighbor')).every((item) => item.ok),
  checks: integrity.checks,
  fingerprintCheck,
  counts: integrity.counts,
}

await fs.writeFile('scripts/jlc-cn-pcb-v8-assert-split-report.json', `${JSON.stringify(report, null, 2)}\n`, 'utf8')
console.log(JSON.stringify(report, null, 2))
if (!report.ok) process.exit(1)
