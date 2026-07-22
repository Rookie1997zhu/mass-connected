import { spawnSync } from 'node:child_process'
import fs from 'node:fs/promises'

const STAGES = {
  fr4_fit: {
    targets: 'scripts/jlc-cn-pcb-v13-fr4-fit-targets.json',
    output: 'scripts/jlc-cn-pcb-v13-fr4-fit-samples.json',
  },
  aluminum_fit: {
    targets: 'scripts/jlc-cn-pcb-v13-aluminum-fit-targets.json',
    output: 'scripts/jlc-cn-pcb-v13-aluminum-fit-samples.json',
  },
  fit: {
    targets: 'scripts/jlc-cn-pcb-v13-fpc-fit-targets.json',
    output: 'scripts/jlc-cn-pcb-v13-fpc-fit-samples.json',
  },
  tuning: {
    targets: 'scripts/jlc-cn-pcb-v13-tuning-holdout-targets.json',
    output: 'scripts/jlc-cn-pcb-v13-tuning-holdout-samples.json',
  },
  process: {
    targets: 'scripts/jlc-cn-pcb-v13-process-holdout-targets.json',
    output: 'scripts/jlc-cn-pcb-v13-process-holdout-samples.json',
  },
  acceptance: {
    targets: 'scripts/jlc-cn-pcb-v13-acceptance-targets.json',
    output: 'scripts/jlc-cn-pcb-v13-acceptance-samples.json',
  },
}

const stageName = process.argv[2]
const stageConfig = STAGES[stageName]
if (!stageConfig) throw new Error(`stage must be one of: ${Object.keys(STAGES).join(', ')}`)
if (stageName === 'acceptance') {
  await fs.access('scripts/jlc-cn-pcb-v13-model-fingerprint.json')
  const gate = spawnSync(
    process.execPath,
    ['scripts/jlc-cn-pcb-v13-assert-split.mjs'],
    {
      cwd: process.cwd(),
      env: { ...process.env, JLC_REQUIRE_RUNTIME_PREFLIGHT: '1' },
      stdio: 'inherit',
    },
  )
  if (gate.status !== 0) throw new Error('v13 final acceptance preflight failed')
}

const materialFilter = process.env.JLC_MATERIAL || null
const requestedOutput = String(process.env.JLC_STAGE_OUTPUT || '')
const stage = {
  ...stageConfig,
  output: /jlc-cn-pcb-v13-/.test(requestedOutput) ? requestedOutput : stageConfig.output,
}
const specsPerBatch = Number(process.env.JLC_SPECS_PER_BATCH || 3)
const maxBatchAttempts = Number(process.env.JLC_BATCH_ATTEMPTS || 3)

function isOk(row) {
  return row?.priceSource === 'dom'
    && Number(row.domPriceCny) > 0
    && !row.error
    && row.quarantined !== true
}

function isStableTriple(rows) {
  if (rows.length !== 3 || !rows.every(isOk)) return false
  const prices = rows.map((row) => Number(row.domPriceCny))
  const mean = prices.reduce((sum, price) => sum + price, 0) / prices.length
  const variance = prices.reduce((sum, price) => sum + ((price - mean) ** 2), 0) / prices.length
  return mean > 0 && Math.sqrt(variance) / mean <= 0.02
}

const allTargets = JSON.parse(await fs.readFile(stage.targets, 'utf8'))
const targets = materialFilter
  ? allTargets.filter((row) => (row.materialKey || row.material_key) === materialFilter)
  : allTargets
const existing = JSON.parse(await fs.readFile(stage.output, 'utf8').catch(() => '[]'))
const byId = new Map(existing.map((row) => [row.id, row]))
const groups = new Map()
for (const target of targets) {
  const key = target.baseSampleId || String(target.id).replace(/-R\d+$/, '')
  if (!groups.has(key)) groups.set(key, [])
  groups.get(key).push(target)
}

const keep = []
const incomplete = []
for (const rows of groups.values()) {
  const sampled = rows.map((row) => byId.get(row.id)).filter(Boolean)
  if (isStableTriple(sampled)) keep.push(...sampled)
  else incomplete.push(...rows)
}
// 材料过滤时保留其他材料已有样本，避免覆盖整份输出文件。
const preservedOtherMaterials = materialFilter
  ? existing.filter((row) => (row.materialKey || row.material_key) !== materialFilter)
  : []
await fs.writeFile(
  stage.output,
  `${JSON.stringify([...preservedOtherMaterials, ...keep], null, 2)}\n`,
)
console.log(JSON.stringify({
  status: 'v13_stage_resume_prepared',
  stage: stageName,
  material: materialFilter,
  stableSpecs: keep.length / 3,
  incompleteSpecs: incomplete.length / 3,
  preservedOtherRows: preservedOtherMaterials.length,
  quarantinedRows: existing.filter((row) => row.quarantined === true).length,
  failedRows: existing.filter((row) => row.error).length,
}))
if (!incomplete.length) process.exit(0)

const batches = []
const namespace = `${materialFilter || 'all'}-${process.pid}`
for (let offset = 0; offset < incomplete.length; offset += specsPerBatch * 3) {
  const batchPath = `scripts/.jlc-v13-${stageName}-${namespace}-${String(
    (offset / (specsPerBatch * 3)) + 1,
  ).padStart(3, '0')}.json`
  await fs.writeFile(
    batchPath,
    `${JSON.stringify(incomplete.slice(offset, offset + specsPerBatch * 3), null, 2)}\n`,
  )
  batches.push(batchPath)
}

try {
  for (let index = 0; index < batches.length; index += 1) {
    let succeeded = false
    for (let attempt = 1; attempt <= maxBatchAttempts; attempt += 1) {
      console.log(JSON.stringify({
        status: 'v13_stage_batch_start',
        stage: stageName,
        batch: index + 1,
        totalBatches: batches.length,
        attempt,
      }))
      const env = { ...process.env }
      delete env.JLC_CDP_URL
      env.JLC_HEADLESS = env.JLC_HEADLESS || 'false'
      env.JLC_CONTEXT_SCOPE = 'shared'
      env.JLC_BROWSER_CHANNEL = env.JLC_BROWSER_CHANNEL || 'chrome'
      const requestedProfile = String(env.JLC_USER_DATA_DIR || '')
      env.JLC_USER_DATA_DIR = requestedProfile && !/profile-v(?:7|8|9|10)/i.test(requestedProfile)
        ? requestedProfile
        : `c:\\Users\\ROG STRIX\\Desktop\\OEM.co\\.jlc-playwright-profile-v12-${stageName}`
      env.JLC_SAMPLE_ATTEMPTS = env.JLC_SAMPLE_ATTEMPTS || '3'
      const child = spawnSync(
        process.execPath,
        ['scripts/jlc-cn-browser-sample.mjs', batches[index], stage.output],
        { cwd: process.cwd(), env, stdio: 'inherit' },
      )
      if (child.status === 0) {
        succeeded = true
        break
      }
      await new Promise(
        (resolve) => setTimeout(resolve, Math.min(15000, 2000 * (2 ** (attempt - 1)))),
      )
    }
    if (!succeeded) {
      console.log(JSON.stringify({
        status: 'v13_stage_batch_failed',
        stage: stageName,
        batch: index + 1,
      }))
    }
  }
} finally {
  await Promise.all(batches.map((batch) => fs.rm(batch, { force: true })))
}
console.log(JSON.stringify({ status: 'v13_stage_complete', stage: stageName }))
