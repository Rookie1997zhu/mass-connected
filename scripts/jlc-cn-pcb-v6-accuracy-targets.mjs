import fs from 'node:fs/promises'

// v6 独立大型验收：≥120 规格，不参与拟合；数量使用 JLC 有效档位。
const sizes = [
  [55, 65], [65, 95], [75, 115], [85, 125], [95, 140],
  [105, 135], [115, 160], [125, 155], [135, 190], [145, 165],
  [155, 185], [165, 195], [175, 185], [185, 200], [70, 145],
]
const quantities = [5, 10, 15, 20, 30, 50, 75, 100, 150]

function pick(list, index) {
  return list[index % list.length]
}

function baseSample(id, materialKey, materialLabel, layers, widthMm, heightMm, quantity, process) {
  return {
    id,
    samplingVersion: 'v6-accuracy',
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

// FR-4: 48 条（2/4层）
for (let i = 0; i < 48; i += 1) {
  const [widthMm, heightMm] = pick(sizes, i)
  const quantity = pick(quantities, i + 1)
  const layers = i % 2 === 0 ? 2 : 4
  const processVariants = [
    { boardThickness: '1.6', solderColor: '绿色', surfaceFinish: '有铅喷锡', copperThickness: '1oz', solderMaskCoverage: '过孔盖油', panelDesignCount: '1' },
    { boardThickness: '1.0', solderColor: '红色', surfaceFinish: 'OSP', copperThickness: '1oz', solderMaskCoverage: '过孔开窗', panelDesignCount: '1' },
    { boardThickness: '1.2', solderColor: '黄色', surfaceFinish: '沉金', copperThickness: '1oz', solderMaskCoverage: '过孔塞油', panelDesignCount: '2' },
    { boardThickness: '1.6', solderColor: '白色', surfaceFinish: '无铅喷锡', copperThickness: '1oz', solderMaskCoverage: '过孔盖油', panelDesignCount: '1' },
  ]
  targets.push(baseSample(
    `JLC-CN-PCB-V6-ACC-FR4-${String(i + 1).padStart(3, '0')}`,
    'fr4',
    'FR-4',
    layers,
    widthMm,
    heightMm,
    quantity,
    pick(processVariants, i),
  ))
}

// FPC: 36 条
for (let i = 0; i < 36; i += 1) {
  const [widthMm, heightMm] = pick(sizes, i + 3)
  const quantity = pick(quantities, i + 2)
  const layers = i % 2 === 0 ? 1 : 2
  const thickness = layers === 1 ? '0.11' : pick(['0.11', '0.12', '0.20'], i)
  targets.push(baseSample(
    `JLC-CN-PCB-V6-ACC-FPC-${String(i + 1).padStart(3, '0')}`,
    'fpc',
    'FPC软板',
    layers,
    widthMm,
    heightMm,
    quantity,
    {
      boardThickness: thickness,
      solderColor: '页面默认',
      surfaceFinish: '沉金',
      copperThickness: '1oz',
      solderMaskCoverage: '页面默认',
      panelDesignCount: pick(['1', '2'], i),
    },
  ))
}

// Aluminum: 36 条
for (let i = 0; i < 36; i += 1) {
  const [widthMm, heightMm] = pick(sizes, i + 5)
  const quantity = pick(quantities, i + 4)
  const processVariants = [
    { boardThickness: '1.6', solderColor: '绿色', surfaceFinish: '无铅喷锡', copperThickness: '1oz', solderMaskCoverage: '页面默认', panelDesignCount: '1' },
    { boardThickness: '1.0', solderColor: '红色', surfaceFinish: '无铅喷锡', copperThickness: '1oz', solderMaskCoverage: '页面默认', panelDesignCount: '1' },
    { boardThickness: '1.2', solderColor: '黄色', surfaceFinish: '无铅喷锡', copperThickness: '1oz', solderMaskCoverage: '页面默认', panelDesignCount: '2' },
    { boardThickness: '1.6', solderColor: '哑黑色', surfaceFinish: '无铅喷锡', copperThickness: '1oz', solderMaskCoverage: '页面默认', panelDesignCount: '1' },
  ]
  targets.push(baseSample(
    `JLC-CN-PCB-V6-ACC-ALU-${String(i + 1).padStart(3, '0')}`,
    'aluminum',
    '铝基板',
    1,
    widthMm,
    heightMm,
    quantity,
    pick(processVariants, i),
  ))
}

await fs.writeFile('scripts/jlc-cn-pcb-v6-accuracy-targets.json', JSON.stringify(targets, null, 2), 'utf8')
console.log(JSON.stringify({
  total: targets.length,
  fr4: targets.filter((row) => row.materialKey === 'fr4').length,
  fpc: targets.filter((row) => row.materialKey === 'fpc').length,
  aluminum: targets.filter((row) => row.materialKey === 'aluminum').length,
}, null, 2))
