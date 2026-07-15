import fs from 'node:fs/promises'

const cases = [
  [55, 65, 15],
  [65, 95, 30],
  [75, 115, 15],
  [90, 130, 150],
  [105, 135, 30],
  [115, 175, 75],
  [125, 155, 150],
  [135, 190, 75],
  [145, 165, 15],
  [155, 185, 30],
  [165, 195, 75],
  [175, 185, 150],
  [185, 200, 15],
  [195, 170, 30],
  [70, 145, 75],
]

const configurations = [
  {
    key: 'fr4-2',
    materialKey: 'fr4',
    materialLabel: 'FR-4',
    layers: 2,
    defaults: ['1.6', '绿色', '有铅喷锡', '1oz'],
  },
  {
    key: 'fr4-4',
    materialKey: 'fr4',
    materialLabel: 'FR-4',
    layers: 4,
    defaults: ['1.6', '绿色', '有铅喷锡', '1oz'],
  },
  {
    key: 'fpc-1',
    materialKey: 'fpc',
    materialLabel: 'FPC软板',
    layers: 1,
    defaults: ['0.11', '页面默认', '沉金', '1oz'],
  },
  {
    key: 'fpc-2',
    materialKey: 'fpc',
    materialLabel: 'FPC软板',
    layers: 2,
    defaults: ['0.11', '页面默认', '沉金', '1oz'],
    processValues: ['0.11', '0.12', '0.20'],
    changedField: 'boardThickness',
  },
  {
    key: 'aluminum-1',
    materialKey: 'aluminum',
    materialLabel: '铝基板',
    layers: 1,
    defaults: ['1.6', '绿色', '无铅喷锡', '1oz'],
    processValues: ['绿色', '红色', '蓝色', '白色', '哑黑色'],
    changedField: 'solderColor',
  },
]

function buildTargets(config) {
  return cases.map(([widthMm, heightMm, quantity], index) => {
    const [defaultThickness, defaultColor, surfaceFinish, copperThickness] = config.defaults
    const processValue = config.processValues?.[index % config.processValues.length]
    const boardThickness = config.changedField === 'boardThickness' ? processValue : defaultThickness
    const solderColor = config.changedField === 'solderColor' ? processValue : defaultColor
    const processChangedFields = []
    if (boardThickness !== defaultThickness) processChangedFields.push('boardThickness')
    if (solderColor !== defaultColor) processChangedFields.push('solderColor')
    return {
      id: `JLC-CN-PCB-LARGE-${config.key.toUpperCase()}-${String(index + 1).padStart(3, '0')}`,
      materialKey: config.materialKey,
      materialLabel: config.materialLabel,
      layers: config.layers,
      widthMm,
      heightMm,
      quantity,
      boardThickness,
      solderColor,
      surfaceFinish,
      copperThickness,
      processChangedFields,
      sampleRole: processChangedFields.length ? 'large_estimator_process' : 'large_estimator_base',
      samplingVersion: 'v5-large-accuracy',
    }
  })
}

const allTargets = configurations.flatMap(buildTargets)
await fs.writeFile(
  'scripts/jlc-cn-pcb-large-accuracy-targets.json',
  `${JSON.stringify(allTargets, null, 2)}\n`,
  'utf8',
)
for (const config of configurations) {
  const targets = buildTargets(config)
  await fs.writeFile(
    `scripts/jlc-cn-pcb-large-accuracy-${config.key}-targets.json`,
    `${JSON.stringify(targets, null, 2)}\n`,
    'utf8',
  )
}
console.log(JSON.stringify({
  total: allTargets.length,
  byGroup: Object.fromEntries(configurations.map((config) => [config.key, cases.length])),
  processCases: allTargets.filter((row) => row.processChangedFields.length).length,
}, null, 2))
