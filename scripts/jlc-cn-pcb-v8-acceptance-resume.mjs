import { spawnSync } from 'node:child_process'
import fs from 'node:fs/promises'

const TARGETS = 'scripts/jlc-cn-pcb-v8-acceptance-targets.json'
const OUTPUT = 'scripts/jlc-cn-pcb-v8-acceptance-samples.json'
const SAMPLER = 'scripts/jlc-cn-browser-sample.mjs'
const SPECS_PER_BATCH = Number(process.env.JLC_SPECS_PER_BATCH || 3)

function isOk(row) {
  return row?.priceSource === 'dom' && Number(row.domPriceCny) > 0 && !row.error
}

function isStableTriple(rows) {
  if (rows.length !== 3) return false
  const prices = rows.map((row) => Number(row.domPriceCny)).sort((a, b) => a - b)
  const median = prices[1]
  return prices.every((price) => Math.abs(price - median) / median <= 0.02)
}

const targets = JSON.parse(await fs.readFile(TARGETS, 'utf8'))
const existing = JSON.parse(await fs.readFile(OUTPUT, 'utf8').catch(() => '[]'))
const byId = new Map(existing.map((row) => [row.id, row]))

const groups = new Map()
for (const target of targets) {
  const key = target.baseSampleId || String(target.id).replace(/-R\d+$/, '')
  if (!groups.has(key)) groups.set(key, [])
  groups.get(key).push(target)
}

const incomplete = []
const keepRows = []
for (const [, rows] of groups) {
  const okRows = rows.map((row) => byId.get(row.id)).filter(isOk)
  if (isStableTriple(okRows)) {
    keepRows.push(...okRows)
    continue
  }
  incomplete.push(...rows)
}

await fs.writeFile(OUTPUT, `${JSON.stringify(keepRows, null, 2)}\n`, 'utf8')
console.log(JSON.stringify({
  status: 'acceptance_resume_prepared',
  completeSpecs: Math.floor(keepRows.length / 3),
  incompleteSpecs: incomplete.length / 3,
}))

if (!incomplete.length) {
  console.log(JSON.stringify({ status: 'acceptance_already_complete' }))
  process.exit(0)
}

const batchFiles = []
for (let offset = 0; offset < incomplete.length; offset += SPECS_PER_BATCH * 3) {
  const batch = incomplete.slice(offset, offset + SPECS_PER_BATCH * 3)
  const batchFile = `scripts/.jlc-v8-acceptance-resume-${String(offset / (SPECS_PER_BATCH * 3) + 1).padStart(2, '0')}.json`
  await fs.writeFile(batchFile, `${JSON.stringify(batch, null, 2)}\n`, 'utf8')
  batchFiles.push(batchFile)
}

try {
  for (let index = 0; index < batchFiles.length; index += 1) {
    console.log(JSON.stringify({
      status: 'acceptance_resume_batch_start',
      batch: index + 1,
      totalBatches: batchFiles.length,
      targetFile: batchFiles[index],
    }))
    const env = { ...process.env }
    delete env.JLC_CDP_URL
    env.JLC_HEADLESS = 'false'
    env.JLC_CONTEXT_SCOPE = 'shared'
    env.JLC_BROWSER_CHANNEL = env.JLC_BROWSER_CHANNEL || 'chrome'
    env.JLC_USER_DATA_DIR = env.JLC_USER_DATA_DIR
      || 'c:\\Users\\ROG STRIX\\Desktop\\OEM.co\\.jlc-playwright-profile'

    const child = spawnSync(process.execPath, [SAMPLER, batchFiles[index], OUTPUT], {
      cwd: process.cwd(),
      env,
      stdio: 'inherit',
    })
    if (child.status !== 0) {
      console.log(JSON.stringify({
        status: 'acceptance_resume_batch_failed',
        batch: index + 1,
        exitCode: child.status,
      }))
    }
  }
  console.log(JSON.stringify({ status: 'acceptance_resume_complete', batches: batchFiles.length }))
} finally {
  await Promise.all(batchFiles.map((path) => fs.rm(path, { force: true })))
}

process.exit(0)
