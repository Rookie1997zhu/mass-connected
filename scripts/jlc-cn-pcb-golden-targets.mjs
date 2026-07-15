import fs from 'node:fs/promises'
import { geometryKey, processKey, collectKeys, assertDisjoint } from './jlc-cn-pcb-v7-spec-key.mjs'

const SAMPLING_VERSION = 'v4'
const PROCESS_SAMPLING_VERSION = 'v7'
const PROCESS_FIELDS = [
  'boardThickness',
  'solderColor',
  'surfaceFinish',
  'copperThickness',
  'solderMaskCoverage',
  'panelDesignCount',
]
const fr4Sizes = [[50, 50], [80, 80], [80, 120], [100, 100], [100, 150], [120, 120], [150, 150], [200, 200]]
const materialSizes = [[50, 50], [80, 80], [100, 100], [100, 150], [120, 120], [150, 150], [200, 200]]
const fr4Quantities = [5, 10, 20, 50, 100, 200]
const fpcQuantities = [5, 10, 20, 50, 100, 200]
const aluminumQuantities = [5, 10, 20, 50, 100, 200]

const materialConfigs = [
  {
    materialKey: 'fpc',
    materialLabel: 'FPC软板',
    prefix: 'FPC',
    layers: [1, 2],
    sizes: materialSizes,
    quantities: fpcQuantities,
  },
  {
    materialKey: 'aluminum',
    materialLabel: '铝基板',
    prefix: 'ALU',
    layers: [1],
    sizes: materialSizes,
    quantities: aluminumQuantities,
  },
]

const processOptions = {
  fr4: {
    defaults: {
      boardThickness: '1.6',
      solderColor: '绿色',
      surfaceFinish: '有铅喷锡',
      copperThickness: '1oz',
      solderMaskCoverage: '过孔盖油',
      panelDesignCount: '1',
    },
    options: {
      boardThickness: ['1.0', '1.2', '1.6', '2.0'],
      solderColor: ['绿色', '红色', '黄色', '蓝色', '白色', '哑黑色'],
      surfaceFinish: ['OSP', '有铅喷锡', '无铅喷锡', '沉金'],
      copperThickness: ['1oz'],
      solderMaskCoverage: ['过孔盖油', '过孔开窗', '过孔塞油', '过孔塞树脂+过孔电镀盖帽'],
      panelDesignCount: ['1', '2'],
    },
  },
  fpc: {
    defaults: {
      boardThickness: '0.11',
      solderColor: '页面默认',
      surfaceFinish: '沉金',
      copperThickness: '1oz',
      solderMaskCoverage: '页面默认',
      panelDesignCount: '1',
    },
    options: {
      boardThickness: ['0.11', '0.12', '0.20'],
      solderColor: ['页面默认'],
      surfaceFinish: ['沉金'],
      copperThickness: ['1oz'],
      solderMaskCoverage: ['页面默认'],
      panelDesignCount: ['1', '2'],
    },
  },
  aluminum: {
    defaults: {
      boardThickness: '1.6',
      solderColor: '绿色',
      surfaceFinish: '无铅喷锡',
      copperThickness: '1oz',
      solderMaskCoverage: '页面默认',
      panelDesignCount: '1',
    },
    options: {
      boardThickness: ['1.0', '1.2', '1.6'],
      solderColor: ['绿色', '红色', '黄色', '蓝色', '白色', '哑黑色'],
      surfaceFinish: ['无铅喷锡'],
      copperThickness: ['1oz'],
      solderMaskCoverage: ['页面默认'],
      panelDesignCount: ['1', '2'],
    },
  },
}

function repeatSamples(samples, repeats, role) {
  return samples.flatMap((sample) => Array.from({ length: repeats }, (_, index) => ({
    ...sample,
    samplingVersion: SAMPLING_VERSION,
    id: `${sample.id}-R${index + 1}`,
    baseSampleId: sample.id,
    repeatIndex: index + 1,
    sampleRole: role,
    estimatorGroup: role,
  })))
}

function buildGoldenBase() {
  const samples = []
  let fr4Index = 1
  for (const layers of [2, 4]) {
    for (const [widthMm, heightMm] of fr4Sizes) {
      for (const quantity of fr4Quantities) {
        samples.push({
          id: `JLC-CN-PCB-GOLDEN-FR4-${String(fr4Index++).padStart(3, '0')}`,
          materialKey: 'fr4',
          materialLabel: 'FR-4',
          layers,
          widthMm,
          heightMm,
          quantity,
          boardThickness: '1.6',
          solderColor: '绿色',
          surfaceFinish: '有铅喷锡',
        })
      }
    }
  }

  for (const config of materialConfigs) {
    let materialIndex = 1
    for (const layers of config.layers) {
      for (const [widthMm, heightMm] of config.sizes) {
        for (const quantity of config.quantities) {
          samples.push({
            id: `JLC-CN-PCB-GOLDEN-${config.prefix}-${String(materialIndex++).padStart(3, '0')}`,
            materialKey: config.materialKey,
            materialLabel: config.materialLabel,
            layers,
            widthMm,
            heightMm,
            quantity,
          })
        }
      }
    }
  }

  return samples
}

function buildHoldoutBase() {
  const fr4Holdout = [
    [2, 50, 50, 5], [2, 80, 120, 50], [2, 100, 100, 100], [2, 150, 150, 200],
    [2, 200, 200, 20], [2, 200, 200, 200], [4, 50, 50, 10], [4, 80, 80, 20],
    [4, 100, 150, 50], [4, 150, 150, 100], [4, 200, 200, 5], [4, 200, 200, 200],
  ].map(([layers, widthMm, heightMm, quantity], index) => ({
    id: `JLC-CN-PCB-HOLDOUT-FR4-${String(index + 1).padStart(3, '0')}`,
    materialKey: 'fr4',
    materialLabel: 'FR-4',
    layers,
    widthMm,
    heightMm,
    quantity,
    boardThickness: '1.6',
    solderColor: '绿色',
    surfaceFinish: '有铅喷锡',
  }))

  const fpcHoldout = [
    [1, 50, 50, 5], [1, 80, 80, 20], [1, 100, 150, 100], [1, 200, 200, 200],
    [2, 50, 50, 20], [2, 100, 100, 5], [2, 150, 150, 100], [2, 200, 200, 200],
  ].map(([layers, widthMm, heightMm, quantity], index) => ({
    id: `JLC-CN-PCB-HOLDOUT-FPC-${String(index + 1).padStart(3, '0')}`,
    materialKey: 'fpc',
    materialLabel: 'FPC软板',
    layers,
    widthMm,
    heightMm,
    quantity,
  }))

  const aluminumHoldout = [
    [50, 50, 5], [80, 80, 10], [100, 100, 100], [100, 150, 20],
    [150, 150, 200], [200, 200, 5], [200, 200, 50], [200, 200, 200],
  ].map(([widthMm, heightMm, quantity], index) => ({
    id: `JLC-CN-PCB-HOLDOUT-ALU-${String(index + 1).padStart(3, '0')}`,
    materialKey: 'aluminum',
    materialLabel: '铝基板',
    layers: 1,
    widthMm,
    heightMm,
    quantity,
  }))

  return [...fr4Holdout, ...fpcHoldout, ...aluminumHoldout]
}

function buildEstimatorHoldoutBase() {
  const fr4 = [
    [2, 60, 70, 15], [2, 90, 110, 30], [2, 130, 160, 75], [2, 175, 200, 150],
    [4, 70, 60, 15], [4, 110, 90, 30], [4, 160, 130, 75], [4, 200, 175, 150],
  ].map(([layers, widthMm, heightMm, quantity], index) => ({
    id: `JLC-CN-PCB-ESTIMATOR-HOLDOUT-FR4-${String(index + 1).padStart(3, '0')}`,
    materialKey: 'fr4',
    materialLabel: 'FR-4',
    layers,
    widthMm,
    heightMm,
    quantity,
    boardThickness: '1.6',
    solderColor: '绿色',
    surfaceFinish: '有铅喷锡',
  }))
  const fpc = [
    [1, 60, 70, 15], [1, 90, 110, 30], [1, 130, 160, 75], [1, 175, 200, 150],
    [2, 70, 60, 15], [2, 110, 90, 30], [2, 160, 130, 75], [2, 200, 175, 150],
  ].map(([layers, widthMm, heightMm, quantity], index) => ({
    id: `JLC-CN-PCB-ESTIMATOR-HOLDOUT-FPC-${String(index + 1).padStart(3, '0')}`,
    materialKey: 'fpc',
    materialLabel: 'FPC软板',
    layers,
    widthMm,
    heightMm,
    quantity,
  }))
  const aluminum = [
    [60, 70, 15], [70, 60, 30], [90, 110, 75], [110, 90, 150],
    [130, 160, 15], [160, 130, 30], [175, 200, 75], [200, 175, 150],
  ].map(([widthMm, heightMm, quantity], index) => ({
    id: `JLC-CN-PCB-ESTIMATOR-HOLDOUT-ALU-${String(index + 1).padStart(3, '0')}`,
    materialKey: 'aluminum',
    materialLabel: '铝基板',
    layers: 1,
    widthMm,
    heightMm,
    quantity,
  }))
  return [...fr4, ...fpc, ...aluminum]
}

function processSample(materialKey, id, anchor, overrides = {}) {
  const labels = { fr4: 'FR-4', fpc: 'FPC软板', aluminum: '铝基板' }
  const defaults = processOptions[materialKey].defaults
  const merged = { ...defaults, ...overrides }
  return {
    id,
    samplingVersion: PROCESS_SAMPLING_VERSION,
    materialKey,
    materialLabel: labels[materialKey],
    ...anchor,
    ...merged,
    processChangedFields: PROCESS_FIELDS.filter(
      (field) => String(merged[field]) !== String(defaults[field]),
    ),
  }
}

function buildProcessGoldenBase() {
  // v7：小/中/大面积 × 低/中/高数量锚点，支撑分段工艺系数
  const anchors = {
    fr4: [
      { layers: 2, widthMm: 50, heightMm: 50, quantity: 5 },
      { layers: 2, widthMm: 100, heightMm: 100, quantity: 50 },
      { layers: 4, widthMm: 150, heightMm: 150, quantity: 100 },
      { layers: 2, widthMm: 80, heightMm: 120, quantity: 20 },
      { layers: 4, widthMm: 200, heightMm: 200, quantity: 50 },
      { layers: 2, widthMm: 120, heightMm: 120, quantity: 100 },
    ],
    fpc: [
      { layers: 1, widthMm: 50, heightMm: 50, quantity: 5 },
      { layers: 2, widthMm: 100, heightMm: 100, quantity: 50 },
      { layers: 2, widthMm: 150, heightMm: 150, quantity: 100 },
      { layers: 1, widthMm: 80, heightMm: 80, quantity: 20 },
      { layers: 2, widthMm: 120, heightMm: 120, quantity: 30 },
      { layers: 1, widthMm: 200, heightMm: 200, quantity: 50 },
    ],
    aluminum: [
      { layers: 1, widthMm: 50, heightMm: 50, quantity: 5 },
      { layers: 1, widthMm: 100, heightMm: 100, quantity: 50 },
      { layers: 1, widthMm: 150, heightMm: 150, quantity: 100 },
      { layers: 1, widthMm: 80, heightMm: 120, quantity: 20 },
      { layers: 1, widthMm: 200, heightMm: 200, quantity: 50 },
      { layers: 1, widthMm: 120, heightMm: 120, quantity: 100 },
    ],
  }
  const rows = []
  for (const [materialKey, config] of Object.entries(processOptions)) {
    anchors[materialKey].forEach((anchor, anchorIndex) => {
      rows.push(processSample(
        materialKey,
        `JLC-CN-PCB-V7-PROCESS-${materialKey.toUpperCase()}-BASE-A${anchorIndex + 1}`,
        anchor,
      ))
      for (const [field, values] of Object.entries(config.options)) {
        values.filter((value) => value !== config.defaults[field]).forEach((value, valueIndex) => {
          rows.push(processSample(
            materialKey,
            `JLC-CN-PCB-V7-PROCESS-${materialKey.toUpperCase()}-${field.toUpperCase()}-${valueIndex + 1}-A${anchorIndex + 1}`,
            anchor,
            { [field]: value },
          ))
        })
      }
    })
  }
  return rows
}

function buildProcessInteractionBase() {
  const rows = []
  const push = (materialKey, id, anchor, overrides) => {
    rows.push(processSample(materialKey, id, anchor, overrides))
  }

  push('fr4', 'JLC-CN-PCB-V7-INTERACT-FR4-COPPER-LAYER-2L', { layers: 2, widthMm: 100, heightMm: 100, quantity: 50 }, { copperThickness: '1oz' })
  push('fr4', 'JLC-CN-PCB-V7-INTERACT-FR4-COPPER-LAYER-4L', { layers: 4, widthMm: 100, heightMm: 100, quantity: 50 }, { copperThickness: '1oz' })

  ;[
    { surfaceFinish: 'OSP', solderMaskCoverage: '过孔盖油' },
    { surfaceFinish: 'OSP', solderMaskCoverage: '过孔开窗' },
    { surfaceFinish: '沉金', solderMaskCoverage: '过孔塞油' },
    { surfaceFinish: '无铅喷锡', solderMaskCoverage: '过孔塞树脂+过孔电镀盖帽' },
  ].forEach((overrides, index) => {
    push(
      'fr4',
      `JLC-CN-PCB-V7-INTERACT-FR4-COVER-FINISH-${index + 1}`,
      { layers: 2, widthMm: 100, heightMm: 100, quantity: 50 },
      overrides,
    )
  })

  ;[
    { widthMm: 50, heightMm: 50, quantity: 5, panelDesignCount: '2' },
    { widthMm: 100, heightMm: 100, quantity: 50, panelDesignCount: '2' },
    { widthMm: 150, heightMm: 150, quantity: 100, panelDesignCount: '2' },
  ].forEach((anchor, index) => {
    push('fr4', `JLC-CN-PCB-V7-INTERACT-FR4-PANEL-AREA-${index + 1}`, { layers: 2, ...anchor }, { panelDesignCount: '2' })
    push('fpc', `JLC-CN-PCB-V7-INTERACT-FPC-PANEL-AREA-${index + 1}`, { layers: 2, ...anchor }, { panelDesignCount: '2' })
    push('aluminum', `JLC-CN-PCB-V7-INTERACT-ALU-PANEL-AREA-${index + 1}`, { layers: 1, ...anchor }, { panelDesignCount: '2' })
  })

  ;['黄色', '红色', '哑黑色'].forEach((solderColor, index) => {
    push('fr4', `JLC-CN-PCB-V7-INTERACT-FR4-COLOR-${index + 1}`, { layers: 2, widthMm: 80, heightMm: 80, quantity: 20 }, { solderColor })
    push('aluminum', `JLC-CN-PCB-V7-INTERACT-ALU-COLOR-${index + 1}`, { layers: 1, widthMm: 80, heightMm: 80, quantity: 20 }, { solderColor })
  })

  return rows
}

function buildProcessHoldoutBase() {
  // 每材料 ≥12 独立工艺组合 holdout（不参与 OFAT 拟合）
  return [
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-001', { layers: 2, widthMm: 80, heightMm: 120, quantity: 20 }, {
      boardThickness: '1.0', solderColor: '红色', surfaceFinish: 'OSP', solderMaskCoverage: '过孔开窗', panelDesignCount: '1',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-002', { layers: 2, widthMm: 120, heightMm: 120, quantity: 50 }, {
      boardThickness: '1.2', solderColor: '黄色', surfaceFinish: '沉金', solderMaskCoverage: '过孔塞油', panelDesignCount: '2',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-003', { layers: 4, widthMm: 100, heightMm: 150, quantity: 100 }, {
      boardThickness: '1.6', solderColor: '白色', surfaceFinish: '无铅喷锡', solderMaskCoverage: '过孔盖油', panelDesignCount: '1',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-004', { layers: 4, widthMm: 55, heightMm: 65, quantity: 15 }, {
      boardThickness: '1.6', solderColor: '绿色', surfaceFinish: '有铅喷锡', solderMaskCoverage: '过孔盖油', panelDesignCount: '1',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-005', { layers: 2, widthMm: 150, heightMm: 150, quantity: 20 }, {
      boardThickness: '1.0', solderColor: '哑黑色', surfaceFinish: 'OSP', solderMaskCoverage: '过孔塞树脂+过孔电镀盖帽', panelDesignCount: '2',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-006', { layers: 2, widthMm: 90, heightMm: 110, quantity: 30 }, {
      boardThickness: '2.0', solderColor: '蓝色', surfaceFinish: '沉金', solderMaskCoverage: '过孔盖油', panelDesignCount: '1',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-007', { layers: 4, widthMm: 70, heightMm: 90, quantity: 50 }, {
      boardThickness: '1.2', solderColor: '红色', surfaceFinish: '无铅喷锡', solderMaskCoverage: '过孔开窗', panelDesignCount: '1',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-008', { layers: 2, widthMm: 160, heightMm: 180, quantity: 75 }, {
      boardThickness: '1.6', solderColor: '黄色', surfaceFinish: 'OSP', solderMaskCoverage: '过孔塞油', panelDesignCount: '2',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-009', { layers: 4, widthMm: 130, heightMm: 140, quantity: 10 }, {
      boardThickness: '1.0', solderColor: '白色', surfaceFinish: '沉金', solderMaskCoverage: '过孔盖油', panelDesignCount: '1',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-010', { layers: 2, widthMm: 95, heightMm: 105, quantity: 150 }, {
      boardThickness: '1.6', solderColor: '哑黑色', surfaceFinish: '无铅喷锡', solderMaskCoverage: '过孔塞树脂+过孔电镀盖帽', panelDesignCount: '1',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-011', { layers: 4, widthMm: 110, heightMm: 125, quantity: 30 }, {
      boardThickness: '2.0', solderColor: '绿色', surfaceFinish: '有铅喷锡', solderMaskCoverage: '过孔开窗', panelDesignCount: '2',
    }),
    processSample('fr4', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FR4-012', { layers: 2, widthMm: 85, heightMm: 95, quantity: 100 }, {
      boardThickness: '1.2', solderColor: '蓝色', surfaceFinish: '沉金', solderMaskCoverage: '过孔塞油', panelDesignCount: '1',
    }),

    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-001', { layers: 2, widthMm: 80, heightMm: 80, quantity: 20 }, {
      boardThickness: '0.12', panelDesignCount: '2',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-002', { layers: 2, widthMm: 100, heightMm: 150, quantity: 50 }, {
      boardThickness: '0.20', panelDesignCount: '1',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-003', { layers: 2, widthMm: 65, heightMm: 95, quantity: 30 }, {
      boardThickness: '0.12', panelDesignCount: '1',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-004', { layers: 1, widthMm: 90, heightMm: 110, quantity: 15 }, {
      boardThickness: '0.20', panelDesignCount: '2',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-005', { layers: 1, widthMm: 120, heightMm: 140, quantity: 75 }, {
      boardThickness: '0.12', panelDesignCount: '1',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-006', { layers: 2, widthMm: 55, heightMm: 70, quantity: 100 }, {
      boardThickness: '0.20', panelDesignCount: '2',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-007', { layers: 1, widthMm: 160, heightMm: 170, quantity: 10 }, {
      boardThickness: '0.12', panelDesignCount: '1',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-008', { layers: 2, widthMm: 140, heightMm: 155, quantity: 50 }, {
      boardThickness: '0.11', panelDesignCount: '2',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-009', { layers: 1, widthMm: 75, heightMm: 85, quantity: 45 }, {
      boardThickness: '0.20', panelDesignCount: '1',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-010', { layers: 2, widthMm: 105, heightMm: 115, quantity: 20 }, {
      boardThickness: '0.12', panelDesignCount: '2',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-011', { layers: 1, widthMm: 180, heightMm: 190, quantity: 30 }, {
      boardThickness: '0.11', panelDesignCount: '1',
    }),
    processSample('fpc', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-FPC-012', { layers: 2, widthMm: 95, heightMm: 125, quantity: 150 }, {
      boardThickness: '0.20', panelDesignCount: '1',
    }),

    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-001', { layers: 1, widthMm: 80, heightMm: 80, quantity: 20 }, {
      boardThickness: '1.0', solderColor: '红色', panelDesignCount: '2',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-002', { layers: 1, widthMm: 100, heightMm: 150, quantity: 50 }, {
      boardThickness: '1.2', solderColor: '黄色', panelDesignCount: '2',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-003', { layers: 1, widthMm: 150, heightMm: 150, quantity: 100 }, {
      boardThickness: '1.0', solderColor: '白色', panelDesignCount: '1',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-004', { layers: 1, widthMm: 55, heightMm: 65, quantity: 15 }, {
      boardThickness: '1.6', solderColor: '哑黑色', panelDesignCount: '1',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-005', { layers: 1, widthMm: 90, heightMm: 110, quantity: 30 }, {
      boardThickness: '1.2', solderColor: '蓝色', panelDesignCount: '1',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-006', { layers: 1, widthMm: 130, heightMm: 140, quantity: 75 }, {
      boardThickness: '1.0', solderColor: '绿色', panelDesignCount: '2',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-007', { layers: 1, widthMm: 70, heightMm: 95, quantity: 50 }, {
      boardThickness: '1.6', solderColor: '红色', panelDesignCount: '1',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-008', { layers: 1, widthMm: 160, heightMm: 170, quantity: 10 }, {
      boardThickness: '1.2', solderColor: '黄色', panelDesignCount: '2',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-009', { layers: 1, widthMm: 110, heightMm: 125, quantity: 150 }, {
      boardThickness: '1.0', solderColor: '哑黑色', panelDesignCount: '1',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-010', { layers: 1, widthMm: 85, heightMm: 105, quantity: 20 }, {
      boardThickness: '1.6', solderColor: '白色', panelDesignCount: '2',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-011', { layers: 1, widthMm: 175, heightMm: 185, quantity: 30 }, {
      boardThickness: '1.2', solderColor: '蓝色', panelDesignCount: '1',
    }),
    processSample('aluminum', 'JLC-CN-PCB-V7-PROCESS-HOLDOUT-ALUMINUM-012', { layers: 1, widthMm: 95, heightMm: 115, quantity: 100 }, {
      boardThickness: '1.0', solderColor: '红色', panelDesignCount: '1',
    }),
  ]
}

function buildFinalAcceptanceBase() {
  // 最终验收：每材料 ≥40，离 exact 网格，与拟合/工艺 holdout 互斥
  const sizes = [
    [56, 68], [63, 91], [71, 104], [79, 117], [86, 129],
    [94, 136], [102, 148], [109, 157], [117, 166], [124, 174],
    [132, 181], [139, 189], [147, 176], [154, 193], [61, 99],
    [74, 128], [88, 141], [97, 153], [113, 167], [128, 158],
    [143, 184], [158, 171], [67, 122], [82, 144], [99, 161],
    [118, 173], [136, 188], [151, 169], [77, 133], [91, 149],
    [106, 162], [121, 178], [138, 155], [152, 187], [64, 108],
    [83, 139], [98, 151], [114, 165], [129, 179], [146, 192],
  ]
  const quantities = [15, 30, 50, 75, 100, 150, 20, 10, 5, 200]
  const rows = []
  for (let i = 0; i < 40; i += 1) {
    const [widthMm, heightMm] = sizes[i]
    const quantity = quantities[i % quantities.length]
    rows.push({
      id: `JLC-CN-PCB-V7-ACC-FR4-${String(i + 1).padStart(3, '0')}`,
      samplingVersion: 'v7-acceptance',
      sampleRole: 'final_acceptance',
      materialKey: 'fr4',
      materialLabel: 'FR-4',
      layers: i % 2 === 0 ? 2 : 4,
      widthMm,
      heightMm,
      quantity,
      boardThickness: '1.6',
      solderColor: '绿色',
      surfaceFinish: '有铅喷锡',
      copperThickness: '1oz',
      solderMaskCoverage: '过孔盖油',
      panelDesignCount: '1',
      processChangedFields: [],
    })
  }
  for (let i = 0; i < 40; i += 1) {
    const [widthMm, heightMm] = sizes[(i + 5) % sizes.length]
    const quantity = quantities[(i + 3) % quantities.length]
    rows.push({
      id: `JLC-CN-PCB-V7-ACC-FPC-${String(i + 1).padStart(3, '0')}`,
      samplingVersion: 'v7-acceptance',
      sampleRole: 'final_acceptance',
      materialKey: 'fpc',
      materialLabel: 'FPC软板',
      layers: i % 2 === 0 ? 1 : 2,
      widthMm,
      heightMm,
      quantity,
      boardThickness: '0.11',
      solderColor: '页面默认',
      surfaceFinish: '沉金',
      copperThickness: '1oz',
      solderMaskCoverage: '页面默认',
      panelDesignCount: '1',
      processChangedFields: [],
    })
  }
  for (let i = 0; i < 40; i += 1) {
    const [widthMm, heightMm] = sizes[(i + 11) % sizes.length]
    const quantity = quantities[(i + 7) % quantities.length]
    rows.push({
      id: `JLC-CN-PCB-V7-ACC-ALU-${String(i + 1).padStart(3, '0')}`,
      samplingVersion: 'v7-acceptance',
      sampleRole: 'final_acceptance',
      materialKey: 'aluminum',
      materialLabel: '铝基板',
      layers: 1,
      widthMm,
      heightMm,
      quantity,
      boardThickness: '1.6',
      solderColor: '绿色',
      surfaceFinish: '无铅喷锡',
      copperThickness: '1oz',
      solderMaskCoverage: '页面默认',
      panelDesignCount: '1',
      processChangedFields: [],
    })
  }
  return rows
}

const smokeTargets = [
  { id: 'JLC-CN-PCB-V4-SMOKE-FR4-2L', materialKey: 'fr4', materialLabel: 'FR-4', layers: 2, widthMm: 200, heightMm: 200, quantity: 200, boardThickness: '1.6', solderColor: '绿色', surfaceFinish: '有铅喷锡' },
  { id: 'JLC-CN-PCB-V4-SMOKE-FR4-4L', materialKey: 'fr4', materialLabel: 'FR-4', layers: 4, widthMm: 200, heightMm: 200, quantity: 200, boardThickness: '1.6', solderColor: '绿色', surfaceFinish: '有铅喷锡' },
  { id: 'JLC-CN-PCB-V4-SMOKE-FPC-1L', materialKey: 'fpc', materialLabel: 'FPC软板', layers: 1, widthMm: 200, heightMm: 200, quantity: 200 },
  { id: 'JLC-CN-PCB-V4-SMOKE-FPC-2L', materialKey: 'fpc', materialLabel: 'FPC软板', layers: 2, widthMm: 200, heightMm: 200, quantity: 200 },
  { id: 'JLC-CN-PCB-V4-SMOKE-ALU-1L', materialKey: 'aluminum', materialLabel: '铝基板', layers: 1, widthMm: 200, heightMm: 200, quantity: 200 },
].map((sample) => ({ ...sample, samplingVersion: SAMPLING_VERSION }))
const goldenBase = buildGoldenBase()
const goldenTargets = repeatSamples(goldenBase, 3, 'golden')
const exactHoldoutTargets = repeatSamples(buildHoldoutBase(), 1, 'exact_holdout')
const estimatorHoldoutTargets = repeatSamples(buildEstimatorHoldoutBase(), 1, 'estimator_holdout')
const processGoldenBase = buildProcessGoldenBase()
const processInteractionBase = buildProcessInteractionBase()
const processGoldenTargets = repeatSamples([...processGoldenBase, ...processInteractionBase], 3, 'process_golden')
  .map((sample) => ({ ...sample, samplingVersion: PROCESS_SAMPLING_VERSION }))
const processHoldoutBase = buildProcessHoldoutBase()
const processHoldoutTargets = repeatSamples(processHoldoutBase, 3, 'process_holdout')
  .map((sample) => ({ ...sample, samplingVersion: PROCESS_SAMPLING_VERSION }))
const finalAcceptanceBase = buildFinalAcceptanceBase()
const finalAcceptanceTargets = repeatSamples(finalAcceptanceBase, 1, 'final_acceptance')
  .map((sample) => ({ ...sample, samplingVersion: 'v7-acceptance' }))

const fitGeometryKeys = collectKeys([...goldenBase, ...processGoldenBase, ...processInteractionBase], geometryKey)
const fitProcessKeys = collectKeys([...processGoldenBase, ...processInteractionBase], processKey)
const holdoutProcessKeys = collectKeys(processHoldoutBase, processKey)
const acceptanceGeometryKeys = collectKeys(finalAcceptanceBase, geometryKey)
const acceptanceProcessKeys = collectKeys(finalAcceptanceBase, processKey)

const splitChecks = [
  assertDisjoint('fit_process', fitProcessKeys, 'process_holdout', holdoutProcessKeys),
  assertDisjoint('fit_geometry', fitGeometryKeys, 'final_acceptance', acceptanceGeometryKeys),
  assertDisjoint('process_holdout', holdoutProcessKeys, 'final_acceptance', acceptanceProcessKeys),
]

await fs.writeFile('scripts/jlc-cn-pcb-v4-smoke-targets.json', JSON.stringify(smokeTargets, null, 2), 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-golden-v4-targets.json', JSON.stringify(goldenTargets, null, 2), 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-exact-holdout-v4-targets.json', JSON.stringify(exactHoldoutTargets, null, 2), 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-estimator-holdout-v4-targets.json', JSON.stringify(estimatorHoldoutTargets, null, 2), 'utf8')
for (const materialKey of ['fr4', 'fpc', 'aluminum']) {
  const materialTargets = goldenTargets.filter((sample) => sample.materialKey === materialKey)
  await fs.writeFile(
    `scripts/jlc-cn-pcb-golden-v4-${materialKey}-targets.json`,
    JSON.stringify(materialTargets, null, 2),
    'utf8',
  )
}
await fs.writeFile('scripts/jlc-cn-pcb-process-v7-options.json', JSON.stringify(processOptions, null, 2), 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-process-v7-targets.json', JSON.stringify(processGoldenTargets, null, 2), 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-process-holdout-v7-targets.json', JSON.stringify(processHoldoutTargets, null, 2), 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-v7-acceptance-targets.json', JSON.stringify(finalAcceptanceTargets, null, 2), 'utf8')
// 兼容旧路径：同步写出 v6 文件名别名（内容已升级为 v7）
await fs.writeFile('scripts/jlc-cn-pcb-process-v6-options.json', JSON.stringify(processOptions, null, 2), 'utf8')
for (const materialKey of ['fr4', 'fpc', 'aluminum']) {
  await fs.writeFile(
    `scripts/jlc-cn-pcb-process-v7-${materialKey}-targets.json`,
    JSON.stringify(processGoldenTargets.filter((sample) => sample.materialKey === materialKey), null, 2),
    'utf8',
  )
  await fs.writeFile(
    `scripts/jlc-cn-pcb-v7-acceptance-${materialKey}-targets.json`,
    JSON.stringify(finalAcceptanceTargets.filter((sample) => sample.materialKey === materialKey), null, 2),
    'utf8',
  )
}

await fs.writeFile('scripts/jlc-cn-pcb-v7-split-report.json', JSON.stringify({
  generatedAt: new Date().toISOString(),
  processSamplingVersion: PROCESS_SAMPLING_VERSION,
  checks: splitChecks,
  counts: {
    goldenUnique: goldenBase.length,
    processGoldenUnique: processGoldenBase.length + processInteractionBase.length,
    processHoldoutUnique: processHoldoutBase.length,
    finalAcceptanceUnique: finalAcceptanceBase.length,
    finalAcceptanceByMaterial: {
      fr4: finalAcceptanceBase.filter((row) => row.materialKey === 'fr4').length,
      fpc: finalAcceptanceBase.filter((row) => row.materialKey === 'fpc').length,
      aluminum: finalAcceptanceBase.filter((row) => row.materialKey === 'aluminum').length,
    },
  },
}, null, 2), 'utf8')

console.log(JSON.stringify({
  smokeTargets: smokeTargets.length,
  goldenUnique: goldenBase.length,
  goldenTargets: goldenTargets.length,
  exactHoldoutTargets: exactHoldoutTargets.length,
  estimatorHoldoutTargets: estimatorHoldoutTargets.length,
  processGoldenUnique: processGoldenBase.length + processInteractionBase.length,
  processInteractionUnique: processInteractionBase.length,
  processGoldenTargets: processGoldenTargets.length,
  processHoldoutUnique: processHoldoutBase.length,
  processHoldoutTargets: processHoldoutTargets.length,
  finalAcceptanceUnique: finalAcceptanceBase.length,
  splitChecks,
}, null, 2))
