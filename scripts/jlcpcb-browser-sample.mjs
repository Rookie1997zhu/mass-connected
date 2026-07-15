/**
 * Browser-based JLCPCB quote sampling via public quote page.
 * Low frequency, no login/cart/order.
 */
import fs from 'node:fs/promises'
import { chromium } from 'playwright'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function readPrice(page) {
  await page.waitForTimeout(1200)
  const priceText = await page.locator('text=Calculated Price').locator('xpath=..').innerText().catch(() => '')
  const match = priceText.match(/\$\s*([0-9]+(?:\.[0-9]{2})?)/g)
  const all = match ? match.map((m) => Number(m.replace(/[^\d.]/g, ''))) : []
  const calculated = all.length ? all[all.length - 1] : null
  const specialOffer = await page.locator('li', { hasText: 'Special Offer' }).first().innerText().catch(() => '')
  const specialMatch = specialOffer.match(/\$\s*([0-9]+(?:\.[0-9]{2})?)/)
  const specialOfferUsd = specialMatch ? Number(specialMatch[1]) : null
  const effectivePriceUsd = calculated && calculated > 0 ? calculated : specialOfferUsd
  return {
    calculatedPriceUsd: calculated,
    specialOfferUsd,
    effectivePriceUsd,
    priceText: priceText.trim(),
  }
}

async function ensureFr4(page) {
  const fr4 = page.getByRole('button', { name: 'FR-4', exact: true })
  if (await fr4.count()) {
    await fr4.first().click()
    await page.waitForTimeout(300)
  }
}

async function setQuote(page, sample) {
  const url = `https://cart.jlcpcb.com/quote?orderType=1&stencilLayer=${sample.layers}&stencilWidth=${sample.widthMm}&stencilLength=${sample.heightMm}`
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await ensureFr4(page)

  const x = page.getByRole('textbox', { name: 'X' })
  const y = page.getByRole('textbox', { name: 'Y' })
  await x.fill(String(sample.widthMm))
  await y.fill(String(sample.heightMm))
  await y.press('Tab')

  await page.getByRole('button', { name: String(sample.layers), exact: true }).first().click()

  if (sample.quantity && sample.quantity !== 5) {
    const qtyBlock = page.locator('text=PCB Qty').locator('xpath=..')
    const qtyInput = qtyBlock.locator('input[placeholder="Select"]').first()
    if (await qtyInput.count()) {
      await qtyInput.click()
      await qtyBlock.getByText(String(sample.quantity), { exact: true }).click()
    }
  }

  if (sample.solderColor) {
    await page.getByRole('button', { name: sample.solderColor, exact: true }).first().click()
  }
  if (sample.surfaceFinish) {
    await page.getByRole('button', { name: sample.surfaceFinish, exact: true }).first().click()
  }
  if (sample.boardThickness) {
    const thickBtn = page.getByRole('button', { name: `${sample.boardThickness}mm`, exact: true })
    if (await thickBtn.count()) {
      const enabled = await thickBtn.first().isEnabled().catch(() => false)
      if (enabled) await thickBtn.first().click()
    }
  }

  await page.getByRole('button', { name: 'Single PCB', exact: true }).click().catch(() => {})
  if (!sample.solderColor) {
    await page.getByRole('button', { name: 'Green', exact: true }).first().click().catch(() => {})
  }
  if (!sample.surfaceFinish) {
    await page.getByRole('button', { name: 'HASL(with lead)', exact: true }).first().click().catch(() => {})
  }

  // Prefer 1.6mm when available for baseline comparability
  if (!sample.boardThickness) {
    const thick16 = page.getByRole('button', { name: '1.6mm', exact: true })
    if (await thick16.count()) {
      const enabled = await thick16.first().isEnabled().catch(() => false)
      if (enabled) await thick16.first().click().catch(() => {})
    }
  }

  return readPrice(page)
}

function buildSamples(mode) {
  const smoke = [
    { id: 'SMOKE-001', layers: 2, widthMm: 50, heightMm: 50, quantity: 5 },
    { id: 'SMOKE-002', layers: 2, widthMm: 100, heightMm: 100, quantity: 5 },
    { id: 'SMOKE-003', layers: 4, widthMm: 50, heightMm: 50, quantity: 5 },
  ]

  const sizes = [[50, 50], [100, 100], [100, 150], [150, 150]]
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
    ...item,
  }))

  if (mode === 'all') return [...smoke, ...baseMatrix, ...delta]
  if (mode === 'base') return baseMatrix
  if (mode === 'delta') return delta
  return smoke
}

async function main() {
  const mode = process.argv[2] || 'smoke'
  const outFile = process.argv[3] || `scripts/jlcpcb-browser-${mode}.json`
  const samples = buildSamples(mode)
  const sampleTime = new Date().toISOString()
  const launchOptions = { headless: true }
  for (const channel of ['msedge', 'chrome']) {
    try {
      const browser = await chromium.launch({ ...launchOptions, channel })
      return runWithBrowser(browser, samples, outFile, sampleTime)
    } catch {
      // try next channel
    }
  }
  const browser = await chromium.launch(launchOptions)
  return runWithBrowser(browser, samples, outFile, sampleTime)
}

async function runWithBrowser(browser, samples, outFile, sampleTime) {
  const page = await browser.newPage()
  const results = []

  for (const sample of samples) {
    try {
      const price = await setQuote(page, sample)
      results.push({
        ...sample,
        sampleTime,
        sourceUrl: 'https://cart.jlcpcb.com/quote',
        currency: 'USD',
        fixedOptions: 'FR-4, Single PCB, Green, White silkscreen, HASL(with lead), 1oz, default test options',
        calculatedPriceUsd: price.effectivePriceUsd,
        rawCalculatedPriceUsd: price.calculatedPriceUsd,
        specialOfferUsd: price.specialOfferUsd,
        notes: 'Public quote page sample; excludes shipping/tax/Gerber review surcharges',
        priceText: price.priceText,
      })
      console.log(JSON.stringify({
        id: sample.id,
        layers: sample.layers,
        size: `${sample.widthMm}x${sample.heightMm}`,
        qty: sample.quantity,
        price: price.effectivePriceUsd,
      }))
    } catch (err) {
      results.push({ ...sample, error: String(err) })
      console.log(JSON.stringify({ id: sample.id, error: String(err) }))
    }
    await sleep(900)
  }

  await browser.close()
  await fs.writeFile(outFile, JSON.stringify(results, null, 2), 'utf8')
  console.log(`Wrote ${results.length} samples to ${outFile}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
