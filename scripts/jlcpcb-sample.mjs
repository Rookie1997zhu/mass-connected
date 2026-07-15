/**
 * JLCPCB public quote sampling helper.
 * Uses the same public calculation endpoint as the online quote page.
 * Low-frequency sampling only; no login/cart/order actions.
 */

const API_URL = 'https://cart.jlcpcb.com/api/overseas-core-platform/shoppingCart/calculationGoodsCostsNew'
const SERVICE_URL = 'https://cart.jlcpcb.com/api/overseas-core-platform/shoppingCart/quereyOrderService'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      'content-type': 'application/json',
      accept: 'application/json, text/plain, */*',
      origin: 'https://cart.jlcpcb.com',
      referer: 'https://cart.jlcpcb.com/quote',
      ...(options.headers || {}),
    },
  })
  const text = await res.text()
  let data
  try {
    data = JSON.parse(text)
  } catch {
    data = text
  }
  return { status: res.status, data }
}

async function getOrderService() {
  const { status, data } = await fetchJson(SERVICE_URL, { method: 'POST', body: '{}' })
  if (status !== 200) throw new Error(`orderService failed: ${status}`)
  return data
}

function buildPayload({
  layers = 2,
  widthMm = 100,
  heightMm = 100,
  quantity = 5,
  solderColor = 'Green',
  surfaceFinish = 'HASL(with lead)',
  boardThickness = '1.6',
  copperWeight = 1,
}) {
  return {
    orderType: 1,
    plateType: 1,
    plateBrand: 1,
    stencilLayer: layers,
    stencilWidth: widthMm,
    stencilLength: heightMm,
    stencilCounts: quantity,
    differentDesign: 1,
    deliveryFormat: 1,
    boardThickness,
    solderColor,
    silkScreen: 'White',
    surfaceFinish,
    copperWeight,
    insideCopperWeight: 0.5,
    goldFinger: 0,
    viaCovering: 'Tenting vias',
    markOnPcb: 0,
    electricalTest: 1,
    confirmProductionFile: 0,
    productType: 1,
    edgePlating: 0,
    castellatedHoles: 0,
    paperBetweenPcb: 0,
    paperBetweenPcbType: 0,
    goldThickness: 1,
    blindSlot: 0,
    halfHole: 0,
    edgeRounding: 0,
    impedance: 0,
    bgaPackage: 0,
    removeProductNo: 0,
    ulMarking: 0,
    fourWireKelvinTest: 0,
    pressFitHole: 0,
    carbonInk: 0,
    viaInPad: 0,
    zAxis: 0,
    halogenFree: 0,
    tg: 130,
    appearanceQuality: 1,
    finalInspection: 0,
    reportList: [],
    specialProcessList: [],
    buildTime: 2,
    stencilPcb: 0,
    stencilOrder: 0,
    smtOrder: 0,
    smtStencil: 0,
    smtAssembly: 0,
    currency: 'USD',
    country: 'US',
  }
}

function extractPrice(data) {
  const root = data?.data ?? data
  const candidates = [
    root?.totalMoney,
    root?.totalPrice,
    root?.money,
    root?.price,
    root?.orderMoney,
    root?.goodsMoney,
    root?.pcbMoney,
    root?.calculatedPrice,
  ]
  for (const v of candidates) {
    if (typeof v === 'number') return v
    if (typeof v === 'string' && v.trim() !== '') return Number(v)
  }
  const costs = root?.costs || root?.costList || root?.chargeDetails || root?.details
  if (Array.isArray(costs)) {
    const total = costs.find((c) => /total|calculated|special offer/i.test(String(c?.name || c?.costName || '')))
    if (total?.money != null) return Number(total.money)
  }
  return null
}

async function quoteSample(sample) {
  const payload = buildPayload(sample)
  const { status, data } = await fetchJson(API_URL, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  if (status !== 200) {
    return { ...sample, error: `HTTP ${status}`, raw: data }
  }
  const price = extractPrice(data)
  return {
    ...sample,
    priceUsd: price,
    rawKeys: data?.data ? Object.keys(data.data) : Object.keys(data || {}),
    raw: data,
  }
}

async function main() {
  const mode = process.argv[2] || 'smoke'
  const service = await getOrderService()
  console.log(JSON.stringify({ mode, serviceKeys: Object.keys(service?.data || service || {}) }, null, 2))

  const smoke = [
    { id: 'SMOKE-001', layers: 2, widthMm: 50, heightMm: 50, quantity: 5 },
    { id: 'SMOKE-002', layers: 2, widthMm: 100, heightMm: 100, quantity: 5 },
    { id: 'SMOKE-003', layers: 4, widthMm: 50, heightMm: 50, quantity: 5 },
  ]

  const sizes = [
    [50, 50],
    [100, 100],
    [100, 150],
    [150, 150],
  ]
  const quantities = [5, 10, 20, 50, 100]
  const baseMatrix = []
  let idx = 1
  for (const layers of [2, 4]) {
    for (const [widthMm, heightMm] of sizes) {
      for (const quantity of quantities) {
        baseMatrix.push({
          id: `PCB-BASE-${String(idx++).padStart(3, '0')}`,
          layers,
          widthMm,
          heightMm,
          quantity,
        })
      }
    }
  }

  const delta = [
    { id: 'PCB-DELTA-COLOR-GREEN', solderColor: 'Green' },
    { id: 'PCB-DELTA-COLOR-RED', solderColor: 'Red' },
    { id: 'PCB-DELTA-COLOR-BLUE', solderColor: 'Blue' },
    { id: 'PCB-DELTA-COLOR-BLACK', solderColor: 'Black' },
    { id: 'PCB-DELTA-COLOR-WHITE', solderColor: 'White' },
    { id: 'PCB-DELTA-FINISH-HASL', surfaceFinish: 'HASL(with lead)' },
    { id: 'PCB-DELTA-FINISH-LF-HASL', surfaceFinish: 'LeadFree HASL' },
    { id: 'PCB-DELTA-FINISH-ENIG', surfaceFinish: 'ENIG' },
    { id: 'PCB-DELTA-THICK-0.8', boardThickness: '0.8' },
    { id: 'PCB-DELTA-THICK-1.0', boardThickness: '1.0' },
    { id: 'PCB-DELTA-THICK-1.6', boardThickness: '1.6' },
    { id: 'PCB-DELTA-THICK-2.0', boardThickness: '2.0' },
    { id: 'PCB-DELTA-LAYER-6', layers: 6, widthMm: 50, heightMm: 50, quantity: 5 },
    { id: 'PCB-DELTA-LAYER-8', layers: 8, widthMm: 50, heightMm: 50, quantity: 5 },
  ].map((item) => ({
    layers: 2,
    widthMm: 100,
    heightMm: 100,
    quantity: 5,
    solderColor: 'Green',
    surfaceFinish: 'HASL(with lead)',
    boardThickness: '1.6',
    ...item,
  }))

  const list = mode === 'all' ? [...smoke, ...baseMatrix, ...delta] : mode === 'base' ? baseMatrix : mode === 'delta' ? delta : smoke
  const results = []
  for (const sample of list) {
    const result = await quoteSample(sample)
    results.push(result)
    console.log(JSON.stringify({
      id: result.id,
      layers: result.layers,
      size: `${result.widthMm}x${result.heightMm}`,
      qty: result.quantity,
      priceUsd: result.priceUsd,
      error: result.error || null,
    }))
    await sleep(800)
  }

  const outFile = process.argv[3] || `scripts/jlcpcb-sample-${mode}.json`
  await import('node:fs/promises').then((fs) => fs.writeFile(outFile, JSON.stringify(results, null, 2), 'utf8'))
  console.log(`Wrote ${results.length} samples to ${outFile}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
