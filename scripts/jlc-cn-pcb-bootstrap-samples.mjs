/**
 * 当 live 复采暂时不可用时，用已成功 compare/smoke 样本 + legacy 表价
 * 生成带 v2 字段结构的 golden/holdout 占位样本，供验证脚本联调。
 * 注意：仅用于管道联调；正式启用仍需 node jlc-cn-browser-sample.mjs pcb-golden/holdout 真实复采。
 */
import fs from 'node:fs/promises'

const compareLive = JSON.parse(await fs.readFile('scripts/jlc-cn-browser-compare-live.json', 'utf8'))
const smoke = JSON.parse(await fs.readFile('scripts/jlc-cn-browser-smoke.json', 'utf8'))
const holdoutTargets = JSON.parse(await fs.readFile('scripts/jlc-cn-pcb-holdout-targets.json', 'utf8'))
const goldenTargets = JSON.parse(await fs.readFile('scripts/jlc-cn-pcb-golden-targets.json', 'utf8'))
const legacyList = JSON.parse(await fs.readFile('scripts/jlc-cn-pcb-manufacturing-price-list.json', 'utf8'))

function keyOf(item) {
  return [
    item.materialKey || item.material_key || 'fr4',
    Number(item.layers),
    Number(item.widthMm || item.width_mm),
    Number(item.heightMm || item.height_mm),
    Number(item.quantity),
  ].join('|')
}

const liveMap = new Map()
for (const sample of [...compareLive, ...smoke]) {
  if (sample.error || !sample.displayedPriceCny) continue
  liveMap.set(keyOf(sample), sample)
}

function enrichTarget(target, priceCny, sourceId) {
  const lengthCm = Number((target.widthMm / 10).toFixed(2))
  const widthCm = Number((target.heightMm / 10).toFixed(2))
  return {
    ...target,
    materialLabel: target.materialKey === 'fpc' ? 'FPC软板' : 'FR-4',
    sampleTime: new Date().toISOString(),
    sourceUrl: 'https://www.jlc.com/newOrder/#/pcb/pcbPlaceOrder',
    currency: 'CNY',
    lengthCm,
    widthCm,
    displayedPriceCny: priceCny,
    domPriceCny: priceCny,
    apiPriceCny: priceCny,
    apiDomDiff: 0,
    priceSource: sourceId.startsWith('live:') ? 'dom' : 'legacy_seed',
    selectedQuantity: String(target.quantity),
    selectedLengthCm: String(lengthCm),
    selectedWidthCm: String(widthCm),
    selectedMaterialLabel: target.materialKey === 'fpc' ? 'FPC软板' : 'FR-4',
    selectedLayers: Number(target.layers),
    priceText: `预估支付总价(不含运费):\\n¥${priceCny}`,
    priceBreakdown: { internetPayTotalmoney: priceCny },
    notes: sourceId,
  }
}

function resolvePrice(target) {
  const live = liveMap.get(keyOf(target))
  if (live?.displayedPriceCny) {
    const diff = live.apiDomDiff ?? (live.domPriceCny && live.apiPriceCny
      ? Math.abs(live.apiPriceCny - live.domPriceCny) / live.domPriceCny
      : null)
    if (diff == null || diff <= 0.01) {
      return { price: live.displayedPriceCny, sourceId: `live:${live.id}` }
    }
  }
  const legacy = legacyList.rows.find((row) => keyOf(row) === keyOf(target))
  const legacyPrice = legacy?.jlcPriceCny ?? legacy?.jlc_price_cny
  if (legacyPrice) return { price: legacyPrice, sourceId: 'legacy:table_data' }
  return null
}

const goldenSamples = []
for (const target of goldenTargets) {
  const resolved = resolvePrice(target)
  if (!resolved) continue
  goldenSamples.push(enrichTarget(target, resolved.price, resolved.sourceId))
}

const holdoutSamples = []
for (const target of holdoutTargets) {
  const resolved = resolvePrice(target)
  if (!resolved) continue
  holdoutSamples.push(enrichTarget(target, resolved.price, resolved.sourceId))
}

await fs.writeFile('scripts/jlc-cn-pcb-golden-samples.json', JSON.stringify(goldenSamples, null, 2), 'utf8')
await fs.writeFile('scripts/jlc-cn-pcb-holdout-samples.json', JSON.stringify(holdoutSamples, null, 2), 'utf8')
console.log(JSON.stringify({ golden: goldenSamples.length, holdout: holdoutSamples.length }, null, 2))
