/**
 * v7 防泄漏硬门：拟合 / 工艺 holdout / 最终验收规格键交集必须为 0。
 * 用法：
 *   node scripts/jlc-cn-pcb-v7-assert-split.mjs
 *   node scripts/jlc-cn-pcb-v7-assert-split.mjs --acceptance scripts/jlc-cn-pcb-v7-acceptance-live.json
 */
import fs from 'node:fs/promises'
import {
  geometryKey,
  processKey,
  collectKeys,
  assertDisjoint,
} from './jlc-cn-pcb-v7-spec-key.mjs'

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
  const args = { acceptance: 'scripts/jlc-cn-pcb-v7-acceptance-targets.json' }
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--acceptance') args.acceptance = argv[i + 1]
  }
  return args
}

const args = parseArgs(process.argv.slice(2))
const fitRows = [
  ...await readJson('scripts/jlc-cn-pcb-golden-v4-targets.json'),
  ...await readJson('scripts/jlc-cn-pcb-process-v7-targets.json'),
  ...await readJson('scripts/jlc-cn-pcb-process-v6-samples.json'),
]
const holdoutRows = [
  ...await readJson('scripts/jlc-cn-pcb-process-holdout-v7-targets.json'),
  ...await readJson('scripts/jlc-cn-pcb-process-holdout-v6-samples.json'),
]
const acceptanceRows = await readJson(args.acceptance)

const fitGeometry = collectKeys(fitRows, geometryKey)
const fitProcess = collectKeys(fitRows, processKey)
const holdoutProcess = collectKeys(holdoutRows, processKey)
const acceptanceGeometry = collectKeys(acceptanceRows, geometryKey)
const acceptanceProcess = collectKeys(acceptanceRows, processKey)

const checks = [
  assertDisjoint('fit_process', fitProcess, 'process_holdout', holdoutProcess),
  assertDisjoint('fit_geometry', fitGeometry, 'final_acceptance', acceptanceGeometry),
  assertDisjoint('process_holdout', holdoutProcess, 'final_acceptance', acceptanceProcess),
]

const report = {
  generatedAt: new Date().toISOString(),
  acceptancePath: args.acceptance,
  ok: checks.every((item) => item.ok),
  checks,
  counts: {
    fit: fitRows.length,
    holdout: holdoutRows.length,
    acceptance: acceptanceRows.length,
  },
}

await fs.writeFile('scripts/jlc-cn-pcb-v7-assert-split-report.json', JSON.stringify(report, null, 2), 'utf8')
console.log(JSON.stringify(report, null, 2))
if (!report.ok) process.exit(1)
