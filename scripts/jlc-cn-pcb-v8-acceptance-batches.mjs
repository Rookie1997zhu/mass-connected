import { spawnSync } from 'node:child_process'
import fs from 'node:fs/promises'
import { chromium } from 'playwright'

const TARGETS = 'scripts/jlc-cn-pcb-v8-acceptance-targets.json'
const OUTPUT = 'scripts/jlc-cn-pcb-v8-acceptance-samples.json'
const SAMPLER = 'scripts/jlc-cn-browser-sample.mjs'
const CDP_URL = process.env.JLC_CDP_URL || 'http://127.0.0.1:9222'
const SOURCE_URL = 'https://www.jlc.com/newOrder/#/pcb/pcbPlaceOrder?spm=PCB.Homepage.functionbar.1002'
const SPECS_PER_BATCH = Number(process.env.JLC_SPECS_PER_BATCH || 5)
const ROWS_PER_BATCH = SPECS_PER_BATCH * 3

async function preheatDefaultPage() {
  const browser = await chromium.connectOverCDP(CDP_URL)
  const context = browser.contexts()[0]
  if (!context) throw new Error('CDP default context unavailable')
  let page = context.pages().find((candidate) => /pcbPlaceOrder|jlc\.com/.test(candidate.url()))
  if (!page) page = await context.newPage()
  await page.goto(SOURCE_URL, { waitUntil: 'commit', timeout: 60_000 }).catch(() => {})
  await page.waitForLoadState('domcontentloaded', { timeout: 30_000 }).catch(() => {})
  await page.getByRole('button', { name: 'FR-4', exact: true }).waitFor({
    state: 'visible',
    timeout: 60_000,
  })
}

const targets = JSON.parse(await fs.readFile(TARGETS, 'utf8'))
const batchFiles = []
for (let offset = 0; offset < targets.length; offset += ROWS_PER_BATCH) {
  const batch = targets.slice(offset, offset + ROWS_PER_BATCH)
  const batchFile = `scripts/.jlc-v8-acceptance-batch-${String(offset / ROWS_PER_BATCH + 1).padStart(2, '0')}.json`
  await fs.writeFile(batchFile, `${JSON.stringify(batch, null, 2)}\n`, 'utf8')
  batchFiles.push(batchFile)
}

try {
  for (let index = 0; index < batchFiles.length; index += 1) {
    await preheatDefaultPage()
    console.log(JSON.stringify({
      status: 'acceptance_batch_start',
      batch: index + 1,
      totalBatches: batchFiles.length,
      targetFile: batchFiles[index],
    }))
    const child = spawnSync(process.execPath, [SAMPLER, batchFiles[index], OUTPUT], {
      cwd: process.cwd(),
      env: {
        ...process.env,
        JLC_CDP_URL: CDP_URL,
        JLC_CONTEXT_SCOPE: 'shared',
      },
      stdio: 'inherit',
    })
    if (child.status !== 0) {
      throw new Error(`acceptance batch ${index + 1} exited with ${child.status}`)
    }
  }
  console.log(JSON.stringify({ status: 'acceptance_batches_complete', batches: batchFiles.length }))
} finally {
  await Promise.all(batchFiles.map((path) => fs.rm(path, { force: true })))
}

process.exit(0)
