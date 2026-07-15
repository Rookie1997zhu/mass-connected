import fs from 'node:fs/promises'

/**
 * 大型材料验收：三种材料各 30 条，共 90 条。
 * 尺寸/数量刻意避开 exact 价表网格，优先覆盖 verified_estimate。
 * 工艺取各材料标准默认，便于对比「纯估算」准确度。
 */
const sizes = [
  [55, 65], [62, 88], [67, 93], [72, 108], [78, 118],
  [83, 127], [88, 112], [93, 138], [98, 142], [103, 133],
  [108, 158], [113, 147], [118, 163], [123, 152], [128, 178],
  [133, 168], [138, 183], [143, 172], [148, 188], [153, 177],
  [58, 97], [73, 131], [87, 149], [96, 161], [111, 174],
  [126, 159], [141, 186], [156, 169], [69, 124], [81, 146],
]

// JLC 公开页稳定数量档（非法档会导致 quantity mismatch）
const quantities = [15, 30, 50, 75, 100, 150, 20, 10, 5, 200]

function pick(list, index) {
  return list[index % list.length]
}

function baseSample(id, materialKey, materialLabel, layers, widthMm, heightMm, quantity, process) {
  return {
    id,
    samplingVersion: 'v6-large-material-30x3',
    sampleRole: 'large_estimator_focus',
    // 空数组：不强制点击工艺控件，依赖材料默认态，降低 DOM 抖动失败率
    processChangedFields: [],
    materialKey,
    materialLabel,
    layers,
    widthMm,
    heightMm,
    quantity,
    ...process,
  }
}

const targets = []

for (let i = 0; i < 30; i += 1) {
  const [widthMm, heightMm] = pick(sizes, i)
  const quantity = pick(quantities, i + 1)
  const layers = i % 2 === 0 ? 2 : 4
  targets.push(baseSample(
    `JLC-CN-PCB-V6-LM-FR4-${String(i + 1).padStart(3, '0')}`,
    'fr4',
    'FR-4',
    layers,
    widthMm,
    heightMm,
    quantity,
    {
      boardThickness: '1.6',
      solderColor: '绿色',
      surfaceFinish: '有铅喷锡',
      copperThickness: '1oz',
      solderMaskCoverage: '过孔盖油',
      panelDesignCount: '1',
    },
  ))
}

for (let i = 0; i < 30; i += 1) {
  const [widthMm, heightMm] = pick(sizes, i + 7)
  const quantity = pick(quantities, i + 3)
  const layers = i % 2 === 0 ? 1 : 2
  targets.push(baseSample(
    `JLC-CN-PCB-V6-LM-FPC-${String(i + 1).padStart(3, '0')}`,
    'fpc',
    'FPC软板',
    layers,
    widthMm,
    heightMm,
    quantity,
    {
      boardThickness: '0.11',
      solderColor: '页面默认',
      surfaceFinish: '沉金',
      copperThickness: '1oz',
      solderMaskCoverage: '页面默认',
      panelDesignCount: '1',
    },
  ))
}

for (let i = 0; i < 30; i += 1) {
  const [widthMm, heightMm] = pick(sizes, i + 13)
  const quantity = pick(quantities, i + 5)
  targets.push(baseSample(
    `JLC-CN-PCB-V6-LM-ALU-${String(i + 1).padStart(3, '0')}`,
    'aluminum',
    '铝基板',
    1,
    widthMm,
    heightMm,
    quantity,
    {
      boardThickness: '1.6',
      solderColor: '绿色',
      surfaceFinish: '无铅喷锡',
      copperThickness: '1oz',
      solderMaskCoverage: '页面默认',
      panelDesignCount: '1',
    },
  ))
}

const outPath = 'scripts/jlc-cn-pcb-v6-large-material-targets.json'
await fs.writeFile(outPath, `${JSON.stringify(targets, null, 2)}\n`, 'utf8')

for (const material of ['fr4', 'fpc', 'aluminum']) {
  const subset = targets.filter((row) => row.materialKey === material)
  const tag = material === 'aluminum' ? 'alu' : material
  await fs.writeFile(
    `scripts/jlc-cn-pcb-v6-large-material-${tag}-targets.json`,
    `${JSON.stringify(subset, null, 2)}\n`,
    'utf8',
  )
}

console.log(JSON.stringify({
  total: targets.length,
  fr4: targets.filter((row) => row.materialKey === 'fr4').length,
  fpc: targets.filter((row) => row.materialKey === 'fpc').length,
  aluminum: targets.filter((row) => row.materialKey === 'aluminum').length,
  outPath,
}, null, 2))
