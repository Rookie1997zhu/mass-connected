/**
 * 统计 v7 工艺矩阵覆盖：已填 DOM / pending_live_sample / 分材料分规模。
 * 不把验收集与拟合集混用；不修改样本。
 */
import fs from 'node:fs/promises'
import { processKey, areaBandMm2 } from './jlc-cn-pcb-v7-spec-key.mjs'

async function readJson(path) {
  try {
    return JSON.parse(await fs.readFile(path, 'utf8'))
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function summarize(targets, samples, label) {
  const byKey = new Map()
  for (const row of samples) {
    const key = processKey(row)
    if (!byKey.has(key)) byKey.set(key, [])
    byKey.get(key).push(row)
  }
  const uniqueTargets = [...new Map(targets.map((t) => [processKey(t), t])).values()]
  let filled = 0
  let pending = 0
  let bootstrapped = 0
  const byMaterial = {}
  const byBand = { small: { filled: 0, pending: 0 }, mid: { filled: 0, pending: 0 }, large: { filled: 0, pending: 0 } }
  for (const target of uniqueTargets) {
    const key = processKey(target)
    const rows = byKey.get(key) || []
    const ok = rows.filter((r) => r.priceSource === 'dom' && Number(r.domPriceCny) > 0 && !r.error)
    const mat = target.materialKey || target.material_key
    byMaterial[mat] ||= { filled: 0, pending: 0, unique: 0 }
    byMaterial[mat].unique += 1
    const band = areaBandMm2(target.widthMm ?? target.width_mm, target.heightMm ?? target.height_mm)
    if (ok.length >= 3) {
      filled += 1
      byMaterial[mat].filled += 1
      byBand[band].filled += 1
      if (ok.some((r) => String(r.notes || '').includes('bootstrapped') || r.pageFingerprint?.source === 'bootstrapped_from_v6_dom')) {
        bootstrapped += 1
      }
    } else {
      pending += 1
      byMaterial[mat].pending += 1
      byBand[band].pending += 1
    }
  }
  return {
    label,
    uniqueTargets: uniqueTargets.length,
    filledUnique: filled,
    pendingUnique: pending,
    bootstrappedUnique: bootstrapped,
    fillRate: Number((filled / Math.max(uniqueTargets.length, 1)).toFixed(4)),
    byMaterial,
    byBand,
    note: pending
      ? 'pending_live_sample rows remain; do not invent prices from acceptance or assemble historical unrelated specs'
      : 'matrix unique keys fully filled (may still need fresh triple resample)',
  }
}

const fit = summarize(
  await readJson('scripts/jlc-cn-pcb-process-v7-targets.json'),
  await readJson('scripts/jlc-cn-pcb-process-v7-samples.json'),
  'process_fit',
)
const holdout = summarize(
  await readJson('scripts/jlc-cn-pcb-process-holdout-v7-targets.json'),
  await readJson('scripts/jlc-cn-pcb-process-holdout-v7-samples.json'),
  'process_holdout',
)

const report = {
  generatedAt: new Date().toISOString(),
  samplingVersion: 'v7',
  fit,
  holdout,
  liveResampleCommand: 'node scripts/jlc-cn-browser-sample.mjs pcb-process-v7 scripts/jlc-cn-pcb-process-v7-samples.json',
  holdoutResampleCommand: 'node scripts/jlc-cn-browser-sample.mjs pcb-process-holdout-v7 scripts/jlc-cn-pcb-process-holdout-v7-samples.json',
  acceptanceCommand: 'node scripts/jlc-cn-browser-sample.mjs pcb-acceptance-v7 scripts/jlc-cn-pcb-v7-acceptance-samples.json',
}
await fs.writeFile('scripts/jlc-cn-pcb-v7-process-coverage.json', `${JSON.stringify(report, null, 2)}\n`, 'utf8')
console.log(JSON.stringify(report, null, 2))
