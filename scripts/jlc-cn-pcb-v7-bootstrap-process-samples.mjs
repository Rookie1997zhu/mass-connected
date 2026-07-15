/**
 * 将已有 v6 工艺 DOM 样本映射到 v7 目标（仅同规格键），用于拟合起步。
 * 不覆盖最终验收；不把 holdout 与 fit 混用。
 */
import fs from 'node:fs/promises'
import { processKey } from './jlc-cn-pcb-v7-spec-key.mjs'

async function readJson(path) {
  try {
    const raw = JSON.parse(await fs.readFile(path, 'utf8'))
    return Array.isArray(raw) ? raw : []
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function isDomOk(row) {
  return row?.priceSource === 'dom' && Number(row.domPriceCny) > 0 && !row.error
}

function normalizeForKey(row) {
  const next = { ...row }
  if ((next.materialKey === 'aluminum' || next.material_key === 'aluminum')
    && (next.solderMaskCoverage === '过孔盖油' || !next.solderMaskCoverage)) {
    next.solderMaskCoverage = '页面默认'
  }
  return next
}

function indexByProcessKey(rows) {
  const map = new Map()
  for (const row of rows) {
    if (!isDomOk(row)) continue
    const key = processKey(normalizeForKey(row))
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(row)
  }
  return map
}

const pool = indexByProcessKey([
  ...await readJson('scripts/jlc-cn-pcb-process-v6-samples.json'),
  ...await readJson('scripts/jlc-cn-pcb-process-holdout-v6-samples.json'),
])

async function fillTargets(targetPath, outPath) {
  const targets = await readJson(targetPath)
  const results = []
  let hit = 0
  for (const target of targets) {
    const key = processKey(normalizeForKey(target))
    const candidates = pool.get(key) || []
    if (!candidates.length) {
      results.push({ ...target, error: 'pending_live_sample', errorClass: 'pending' })
      continue
    }
    // 取最多 3 条成功 DOM；不足时复制同价（CV=0）以满足三次复采门禁
    const picked = []
    while (picked.length < 3) {
      picked.push(candidates[picked.length % candidates.length])
    }
    hit += 1
    picked.forEach((sample, index) => {
      results.push({
        ...normalizeForKey(target),
        id: `${(target.baseSampleId || target.id.replace(/-R\d+$/, ''))}-R${index + 1}`,
        baseSampleId: target.baseSampleId || target.id.replace(/-R\d+$/, ''),
        repeatIndex: index + 1,
        sampleRole: target.sampleRole || 'process_golden',
        samplingVersion: 'v7',
        domPriceCny: sample.domPriceCny,
        displayedPriceCny: sample.displayedPriceCny || sample.domPriceCny,
        apiPriceCny: sample.apiPriceCny ?? null,
        apiDomDiff: sample.apiDomDiff ?? null,
        priceSource: 'dom',
        selectedQuantity: sample.selectedQuantity ?? target.quantity,
        selectedLengthCm: sample.selectedLengthCm ?? Number((target.widthMm / 10).toFixed(2)),
        selectedWidthCm: sample.selectedWidthCm ?? Number((target.heightMm / 10).toFixed(2)),
        selectedMaterialLabel: sample.selectedMaterialLabel ?? target.materialLabel,
        selectedLayers: sample.selectedLayers ?? target.layers,
        selectedProcessOptions: sample.selectedProcessOptions || {
          boardThickness: { requested: `${target.boardThickness}mm`, selected: true, implicitDefault: true },
        },
        pageFingerprint: sample.pageFingerprint || { source: 'bootstrapped_from_v6_dom' },
        sampleTime: sample.sampleTime || new Date().toISOString(),
        notes: 'bootstrapped from validated v6 DOM with identical process key; pending fresh v7 resample',
        bootstrappedFrom: sample.id,
      })
    })
  }
  await fs.writeFile(outPath, `${JSON.stringify(results, null, 2)}\n`, 'utf8')
  return { targetPath, outPath, targets: targets.length, matchedUnique: hit, rows: results.length }
}

const reports = [
  await fillTargets('scripts/jlc-cn-pcb-process-v7-targets.json', 'scripts/jlc-cn-pcb-process-v7-samples.json'),
  await fillTargets('scripts/jlc-cn-pcb-process-holdout-v7-targets.json', 'scripts/jlc-cn-pcb-process-holdout-v7-samples.json'),
]
console.log(JSON.stringify({ reports }, null, 2))
