/**
 * @deprecated v7 起禁止使用本脚本拼装验收样本。
 * 本脚本会把拟合样本（process/golden）回收进“验收”，造成数据泄漏。
 * 请改用 scripts/jlc-cn-pcb-v7-acceptance-targets.json 的独立新采，
 * 并用 scripts/jlc-cn-pcb-v7-assert-split.mjs 做硬门校验。
 *
 * 组装大型材料验收 live：三种材料各 30 条，优先估算规格。
 * 实价来源为既有三次 DOM/稳定采样产物（同管道），用当前 v6 计算器重评。
 */
import fs from 'node:fs/promises'

console.warn('[DEPRECATED] jlc-cn-pcb-v6-large-material-assemble.mjs is forbidden for v7 acceptance. Prefer independent v7 acceptance sampling + assert-split.')
if (process.env.ALLOW_V6_ASSEMBLE !== 'true') {
  console.error('Refusing to assemble leaked acceptance set. Set ALLOW_V6_ASSEMBLE=true only for historical reproduction.')
  process.exit(1)
}

function keyOf(row) {
  return [
    row.materialKey,
    row.layers,
    row.widthMm,
    row.heightMm,
    row.quantity,
    row.boardThickness || '',
    row.solderColor || '',
    row.surfaceFinish || '',
  ].join('|')
}

function isDomOk(row) {
  return row?.priceSource === 'dom' && Number(row.domPriceCny) > 0 && !row.error
}

function isExactGrid(row) {
  const size = `${row.widthMm}x${row.heightMm}`
  return ['50x50', '80x80', '100x100', '100x150', '120x120'].includes(size)
    && [5, 10, 20, 50, 100, 200].includes(Number(row.quantity))
}

async function loadRows(path) {
  try {
    const raw = JSON.parse(await fs.readFile(path, 'utf8'))
    return Array.isArray(raw) ? raw : (raw.samples || raw.results || [])
  } catch {
    return []
  }
}

function normalize(row, materialKey, id) {
  return {
    id,
    samplingVersion: 'v6-large-material-30x3',
    sampleRole: 'large_estimator_focus',
    materialKey,
    materialLabel: materialKey === 'fr4' ? 'FR-4' : materialKey === 'fpc' ? 'FPC软板' : '铝基板',
    layers: row.layers,
    widthMm: row.widthMm,
    heightMm: row.heightMm,
    quantity: row.quantity,
    boardThickness: row.boardThickness || (materialKey === 'fpc' ? '0.11' : '1.6'),
    solderColor: row.solderColor || (materialKey === 'fpc' ? '页面默认' : '绿色'),
    surfaceFinish: row.surfaceFinish || (materialKey === 'fr4' ? '有铅喷锡' : materialKey === 'fpc' ? '沉金' : '无铅喷锡'),
    copperThickness: row.copperThickness || '1oz',
    solderMaskCoverage: materialKey === 'aluminum'
      ? '页面默认'
      : (row.solderMaskCoverage || (materialKey === 'fr4' ? '过孔盖油' : '页面默认')),
    panelDesignCount: String(row.panelDesignCount || '1'),
    processChangedFields: [],
    domPriceCny: Number(row.domPriceCny),
    displayedPriceCny: Number(row.displayedPriceCny || row.domPriceCny),
    priceSource: 'dom',
    sourceSampleId: row.id,
    sourceNote: row.sourceFile || null,
    sampledAt: row.sampledAt || row.sampleTime || null,
  }
}

const sourceFiles = [
  'scripts/jlc-cn-pcb-large-accuracy-live.json',
  'scripts/jlc-cn-pcb-large-accuracy-aluminum-1-final-live.json',
  'scripts/jlc-cn-pcb-v6-accuracy-merged.json',
  'scripts/jlc-cn-pcb-v6-accuracy-live.json',
  'scripts/jlc-cn-pcb-process-v6-aluminum-samples.json',
  'scripts/jlc-cn-pcb-process-v6-fr4-samples.json',
  'scripts/jlc-cn-pcb-process-v6-fpc-samples.json',
]

const pool = []
for (const file of sourceFiles) {
  const rows = await loadRows(file)
  for (const row of rows) {
    if (!isDomOk(row)) continue
    pool.push({ ...row, sourceFile: file })
  }
}

function isStandardProcess(row) {
  const material = row.materialKey
  const thickness = String(row.boardThickness || '')
  const color = String(row.solderColor || '')
  const finish = String(row.surfaceFinish || '')
  const copper = String(row.copperThickness || '1oz')
  const coverage = String(row.solderMaskCoverage || '')
  const panel = String(row.panelDesignCount || '1')
  if (copper && copper !== '1oz') return false
  if (panel && panel !== '1') return false
  if (material === 'fr4') {
    return (!thickness || thickness === '1.6')
      && (!color || color === '绿色')
      && (!finish || finish === '有铅喷锡')
      && (!coverage || coverage === '过孔盖油' || coverage === '页面默认')
  }
  if (material === 'fpc') {
    return (!thickness || thickness === '0.11')
      && (!color || color === '页面默认')
      && (!finish || finish === '沉金')
      && (!coverage || coverage === '页面默认')
  }
  // aluminum：标准绿油无铅即可；颜色变体也允许进入（工艺已启用）
  return (!finish || finish === '无铅喷锡')
}

function pickMaterial(materialKey, limit) {
  const candidates = pool.filter((row) => row.materialKey === materialKey)
  const buckets = [
    candidates.filter((row) => !isExactGrid(row) && isStandardProcess(row)),
    candidates.filter((row) => !isExactGrid(row)),
    candidates.filter((row) => isStandardProcess(row)),
    candidates,
  ]
  const selected = []
  const seen = new Set()
  for (const bucket of buckets) {
    const ordered = [...bucket].sort((a, b) => (
      Number(b.widthMm * b.heightMm * b.quantity) - Number(a.widthMm * a.heightMm * a.quantity)
    ))
    for (const row of ordered) {
      const k = keyOf(row)
      if (seen.has(k)) continue
      seen.add(k)
      selected.push(row)
      if (selected.length >= limit) return selected
    }
  }
  return selected
}

const selected = {
  fr4: pickMaterial('fr4', 30),
  fpc: pickMaterial('fpc', 30),
  aluminum: pickMaterial('aluminum', 30),
}

const live = []
for (const [materialKey, rows] of Object.entries(selected)) {
  const tag = materialKey === 'aluminum' ? 'ALU' : materialKey.toUpperCase()
  rows.forEach((row, index) => {
    live.push(normalize(row, materialKey, `JLC-CN-PCB-V6-LM-${tag}-${String(index + 1).padStart(3, '0')}`))
  })
}

const outLive = 'scripts/jlc-cn-pcb-v6-large-material-live.json'
const outTargets = 'scripts/jlc-cn-pcb-v6-large-material-scored-targets.json'
await fs.writeFile(outLive, `${JSON.stringify(live, null, 2)}\n`, 'utf8')
await fs.writeFile(outTargets, `${JSON.stringify(live.map(({
  id, samplingVersion, sampleRole, materialKey, materialLabel, layers, widthMm, heightMm, quantity,
  boardThickness, solderColor, surfaceFinish, copperThickness, solderMaskCoverage, panelDesignCount, processChangedFields,
}) => ({
  id, samplingVersion, sampleRole, materialKey, materialLabel, layers, widthMm, heightMm, quantity,
  boardThickness, solderColor, surfaceFinish, copperThickness, solderMaskCoverage, panelDesignCount, processChangedFields,
})), null, 2)}\n`, 'utf8')

console.log(JSON.stringify({
  total: live.length,
  fr4: selected.fr4.length,
  fpc: selected.fpc.length,
  aluminum: selected.aluminum.length,
  estimatePreferred: live.filter((row) => !isExactGrid(row)).length,
  outLive,
}, null, 2))
