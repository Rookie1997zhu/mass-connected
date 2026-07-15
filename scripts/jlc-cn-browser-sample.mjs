/**
 * 嘉立创中文站 PCB 报价采样（公开下单页，低频，不登录/不下单）
 * https://www.jlc.com/newOrder/#/pcb/pcbPlaceOrder
 */
import fs from 'node:fs/promises'
import { chromium } from 'playwright'

const SOURCE_URL = 'https://www.jlc.com/newOrder/#/pcb/pcbPlaceOrder?spm=PCB.Homepage.functionbar.1002'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const MATERIALS = {
  fr4: { key: 'fr4', label: 'FR-4', defaultLayers: 2, prefix: 'FR4', fixedOptions: '1.6mm, 绿色, 有铅喷锡, 1oz' },
  fpc: { key: 'fpc', label: 'FPC软板', defaultLayers: 2, prefix: 'FPC', fixedOptions: '0.11mm, 页面默认阻焊, 沉金, 1oz' },
  aluminum: { key: 'aluminum', label: '铝基板', defaultLayers: 1, prefix: 'ALU', fixedOptions: '1.6mm, 绿色, 无铅喷锡, 1oz' },
  copper: { key: 'copper', label: '铜基板', defaultLayers: 1, prefix: 'COPPER' },
  rogers: { key: 'rogers', label: '罗杰斯高频板', defaultLayers: 2, prefix: 'ROGERS' },
  teflon: { key: 'teflon', label: '铁氟龙高频板', defaultLayers: 2, prefix: 'TEFLON' },
  hdi: { key: 'hdi', label: 'HDI盲埋孔板', defaultLayers: 4, prefix: 'HDI' },
}

const EXTRA_MATERIAL_KEYS = ['fpc', 'aluminum', 'copper', 'rogers', 'teflon', 'hdi']

function mmToCm(mm) {
  return Number((mm / 10).toFixed(2))
}

function buildSamples(mode) {
  const smoke = [
    { id: 'JLC-CN-SMOKE-001', materialKey: 'fr4', layers: 2, widthMm: 50, heightMm: 50, quantity: 5 },
    { id: 'JLC-CN-SMOKE-002', materialKey: 'fr4', layers: 2, widthMm: 100, heightMm: 100, quantity: 5 },
    { id: 'JLC-CN-SMOKE-003', materialKey: 'fr4', layers: 4, widthMm: 50, heightMm: 50, quantity: 5 },
  ]

  const sizes = [[50, 50], [100, 100], [100, 150], [150, 150]]
  const quantities = [5, 10, 20, 50, 100]
  const baseMatrix = []
  let idx = 1
  for (const layers of [2, 4]) {
    for (const [widthMm, heightMm] of sizes) {
      for (const quantity of quantities) {
        baseMatrix.push({
          id: `JLC-CN-BASE-${String(idx++).padStart(3, '0')}`,
          materialKey: 'fr4',
          layers,
          widthMm,
          heightMm,
          quantity,
        })
      }
    }
  }

  const delta = [
    { id: 'JLC-CN-DELTA-COLOR-GREEN', solderColor: '绿色' },
    { id: 'JLC-CN-DELTA-COLOR-RED', solderColor: '红色' },
    { id: 'JLC-CN-DELTA-COLOR-BLUE', solderColor: '蓝色' },
    { id: 'JLC-CN-DELTA-COLOR-BLACK', solderColor: '哑黑色' },
    { id: 'JLC-CN-DELTA-COLOR-WHITE', solderColor: '白色' },
    { id: 'JLC-CN-DELTA-FINISH-HASL', surfaceFinish: '有铅喷锡' },
    { id: 'JLC-CN-DELTA-FINISH-LF-HASL', surfaceFinish: '无铅喷锡' },
    { id: 'JLC-CN-DELTA-FINISH-ENIG', surfaceFinish: '沉金' },
    { id: 'JLC-CN-DELTA-THICK-0.8', boardThickness: '0.8' },
    { id: 'JLC-CN-DELTA-THICK-1.0', boardThickness: '1.0' },
    { id: 'JLC-CN-DELTA-THICK-1.6', boardThickness: '1.6' },
    { id: 'JLC-CN-DELTA-THICK-2.0', boardThickness: '2.0' },
    { id: 'JLC-CN-DELTA-LAYER-6', layers: 6, widthMm: 50, heightMm: 50, quantity: 5 },
    { id: 'JLC-CN-DELTA-LAYER-8', layers: 8, widthMm: 50, heightMm: 50, quantity: 5 },
  ].map((item) => ({
    materialKey: 'fr4',
    layers: 2,
    widthMm: 100,
    heightMm: 100,
    quantity: 5,
    ...item,
  }))

  if (mode === 'all') return [...smoke, ...baseMatrix, ...delta]
  if (mode === 'base') return baseMatrix
  if (mode === 'delta') return delta
  if (mode === 'materials-smoke') return buildMaterialSamples('smoke')
  if (mode === 'materials-matrix') return buildMaterialSamples('matrix')
  return smoke
}

function buildMaterialSamples(scope) {
  const smokeSizes = [[50, 50], [100, 100], [100, 150]]
  const matrixSizes = [[50, 50], [100, 100], [100, 150]]
  const matrixQuantities = [5, 10, 20]
  const samples = []

  for (const key of EXTRA_MATERIAL_KEYS) {
    const material = MATERIALS[key]
    if (scope === 'smoke') {
      smokeSizes.forEach(([widthMm, heightMm], index) => {
        samples.push({
          id: `JLC-CN-MAT-${material.prefix}-SMOKE-${String(index + 1).padStart(3, '0')}`,
          materialKey: key,
          layers: material.defaultLayers,
          widthMm,
          heightMm,
          quantity: 5,
        })
      })
      continue
    }

    let idx = 1
    for (const [widthMm, heightMm] of matrixSizes) {
      for (const quantity of matrixQuantities) {
        samples.push({
          id: `JLC-CN-MAT-${material.prefix}-MATRIX-${String(idx++).padStart(3, '0')}`,
          materialKey: key,
          layers: material.defaultLayers,
          widthMm,
          heightMm,
          quantity,
        })
      }
    }
  }

  return samples
}

async function dismissOverlays(page) {
  for (let i = 0; i < 15; i += 1) {
    await page.keyboard.press('Escape').catch(() => {})

    const saveInit = page.getByRole('button', { name: '保存', exact: true })
    if (await saveInit.isVisible().catch(() => false)) {
      await saveInit.click({ timeout: 2000 }).catch(() => {})
      await page.waitForTimeout(400)
    }

    const tourButtons = ['开始体验', '下一步', '开始下单', '确定', '我知道了', '关闭', 'Close']
    for (const name of tourButtons) {
      const btn = page.getByRole('button', { name, exact: false })
      if (await btn.first().isVisible().catch(() => false)) {
        await btn.first().click({ timeout: 1500 }).catch(() => {})
        await page.waitForTimeout(300)
      }
    }

    await page.locator('.el-dialog__headerbtn, .el-message-box__headerbtn').first().click({ timeout: 800 }).catch(() => {})
    await page.evaluate(() => {
      document.querySelectorAll('.el-dialog__wrapper, .v-modal, .driver-popover').forEach((el) => {
        el.remove()
      })
    })

    const blocking = await page.locator('.el-dialog__wrapper:visible, .driver-popover:visible').count().catch(() => 0)
    if (!blocking) break
    await page.waitForTimeout(350)
  }
}

function parseDomPriceFromSection(priceSection) {
  const totalMatch = priceSection.match(/预估支付总价\(不含运费\)[:\s]*[¥￥]?\s*([0-9]+(?:\.[0-9]{1,2})?)/)
  if (totalMatch) return Number(totalMatch[1])

  const yuanMatches = [...priceSection.matchAll(/[¥￥]\s*([0-9]+(?:\.[0-9]{1,2})?)/g)].map((m) => Number(m[1]))
  const nonZero = yuanMatches.filter((n) => n > 0)
  if (nonZero.length) return nonZero[nonZero.length - 1]
  return yuanMatches[0] ?? null
}

const trackedPriceApi = new WeakMap()

function trackPriceApi(page) {
  trackedPriceApi.set(page, null)
  page.on('response', async (response) => {
    if (!response.url().includes('calculateCustomerOrderMoney') || response.status() !== 200) return
    try {
      const json = await response.json()
      const money = json?.carriageFilePreverifyMoneyVO
      trackedPriceApi.set(page, {
        apiPriceCny: money?.internetPayTotalmoney ?? null,
        priceBreakdown: money ?? null,
      })
    } catch {
      // DOM remains authoritative when API response parsing is unavailable.
    }
  })
}

function resetTrackedPriceApi(page) {
  trackedPriceApi.set(page, null)
}

function readTrackedPriceApi(page) {
  return trackedPriceApi.get(page) || { apiPriceCny: null, priceBreakdown: null }
}

async function readFormState(page) {
  return page.evaluate(() => {
    const readInput = (selector) => {
      const input = document.querySelector(selector)
      return input instanceof HTMLInputElement ? input.value.trim() : null
    }

    const activeMaterialButton = [...document.querySelectorAll('button')].find((btn) => {
      const text = btn.textContent?.trim() || ''
      if (!['FR-4', 'FPC软板', '铝基板', '铜基板'].includes(text)) return false
      const cls = btn.className || ''
      return /active|selected|is-active|checked/.test(cls)
    })

    const layerRoot = document.querySelector('#layerNumber, .layerNumber, .layerNumberBox')
    const activeLayerButton = [...document.querySelectorAll('button')].find((btn) => {
      if (!/^\d+$/.test(btn.textContent?.trim() || '')) return false
      if (layerRoot?.contains(btn)) return false
      const cls = btn.className || ''
      return /active|selected|is-active|checked/.test(cls)
    })

    return {
      selectedQuantity: readInput('input[placeholder="数量"]'),
      selectedLengthCm: readInput('input[placeholder="长"]'),
      selectedWidthCm: readInput('input[placeholder="宽"]'),
      selectedMaterialLabel: activeMaterialButton?.textContent?.trim() || null,
      selectedLayers: activeLayerButton ? Number(activeLayerButton.textContent.trim()) : null,
    }
  })
}

async function readPrice(page, apiPrice) {
  await page.waitForTimeout(300)
  const bodyText = await page.locator('body').innerText()
  const priceSection = bodyText.split('价格明细')[1]?.slice(0, 2500) || bodyText.slice(-3000)

  const domPriceCny = parseDomPriceFromSection(priceSection)
  const apiPriceCny = apiPrice?.apiPriceCny ?? apiPrice?.priceBreakdown?.internetPayTotalmoney ?? null

  let displayedPriceCny = domPriceCny
  let priceSource = 'dom'
  if (displayedPriceCny == null || displayedPriceCny === 0) {
    displayedPriceCny = apiPriceCny
    priceSource = apiPriceCny ? 'api_fallback' : null
  }

  const apiDomDiff = domPriceCny && apiPriceCny
    ? Number((Math.abs(apiPriceCny - domPriceCny) / domPriceCny).toFixed(4))
    : null
  const hasSpecialOffer = Number(apiPrice?.priceBreakdown?.specialProduceMoney || 0) > 0
    || /特价|优惠价|限时价/.test(priceSection)

  // v7：双价格不一致时拒绝 DOM 发布样本（不回退到旧样本）
  const maxApiDomDiff = Number(process.env.JLC_MAX_API_DOM_DIFF || 0.01)
  if (domPriceCny && apiPriceCny && apiDomDiff != null && apiDomDiff > maxApiDomDiff) {
    throw new Error(`dom_api_price_mismatch: diff=${apiDomDiff} > ${maxApiDomDiff}`)
  }

  return {
    displayedPriceCny,
    domPriceCny,
    apiPriceCny,
    apiDomDiff,
    priceSource,
    priceBreakdown: apiPrice?.priceBreakdown ?? null,
    priceText: priceSection.trim(),
    hasSpecialOffer,
    quarantined: hasSpecialOffer,
    quarantineReasons: hasSpecialOffer ? ['special_offer_price'] : [],
  }
}

async function readPageFingerprint(page) {
  return page.evaluate(() => {
    const title = document.title || ''
    const fr4 = [...document.querySelectorAll('button')].some((btn) => (btn.textContent || '').includes('FR-4'))
    const priceReady = (document.body?.innerText || '').includes('价格明细')
    return {
      title,
      fr4Visible: fr4,
      priceSectionVisible: priceReady,
      href: location.href,
      capturedAt: new Date().toISOString(),
    }
  })
}

function classifySampleError(error) {
  const text = String(error || '')
  if (/FR-4 button not visible|order page unavailable/i.test(text)) return 'spa_not_ready'
  if (/dom_api_price_mismatch/i.test(text)) return 'dom_api_mismatch'
  if (/price not stable|stale price/i.test(text)) return 'price_unstable'
  if (/quantity mismatch/i.test(text)) return 'quantity_mismatch'
  if (/process option/i.test(text)) return 'process_selection_failed'
  if (/Timeout/i.test(text)) return 'timeout'
  return 'unknown'
}

async function selectQuantity(page, quantity) {
  await dismissOverlays(page)
  await page.keyboard.press('Escape').catch(() => {})
  const qtyInput = page.locator('input[placeholder="数量"]').first()
  await qtyInput.scrollIntoViewIfNeeded().catch(() => {})
  await qtyInput.click({ force: true, timeout: 5000 })
  await page.waitForTimeout(400)

  // Open the custom quantity modal (#pcbNumberModal) and click by stable id.
  const option = page.locator(`#pcbNumber_${quantity} button[name="板子数量"]`).first()
  await option.waitFor({ state: 'attached', timeout: 8000 }).catch(() => {})
  if (!(await option.count())) {
    throw new Error(`quantity option not found: ${quantity}`)
  }
  await option.click({ force: true, timeout: 5000 })
  await page.waitForTimeout(500)
  await page.keyboard.press('Escape').catch(() => {})
  await page.locator('#pcbNumberModal').waitFor({ state: 'hidden', timeout: 2000 }).catch(() => {})

  let selected = await qtyInput.inputValue().catch(() => '')
  if (selected !== String(quantity)) {
    // Some SPA states keep the readonly input briefly empty; re-read after a beat.
    await page.waitForTimeout(700)
    selected = await qtyInput.inputValue().catch(() => '')
  }
  if (selected !== String(quantity)) {
    throw new Error(`quantity mismatch: expected ${quantity}, got ${selected || 'empty'}`)
  }
}

async function fillBoardSize(page, lengthCm, widthCm) {
  const filled = await page.evaluate(({ lengthValue, widthValue }) => {
    const setValue = (input, value) => {
      if (!(input instanceof HTMLInputElement)) return false
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      setter?.call(input, String(value))
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.dispatchEvent(new Event('change', { bubbles: true }))
      input.dispatchEvent(new Event('blur', { bubbles: true }))
      return true
    }

    const lengthInput = document.querySelector('input[placeholder="长"]')
    const widthInput = document.querySelector('input[placeholder="宽"]')
    return setValue(lengthInput, lengthValue) && setValue(widthInput, widthValue)
  }, { lengthValue: lengthCm, widthValue: widthCm })

  if (!filled) {
    throw new Error('board size inputs not found')
  }

  await page.waitForTimeout(600)
}

function slimBreakdown(bd) {
  if (!bd) return null
  return {
    internetPayTotalmoney: bd.internetPayTotalmoney,
    specialProduceMoney: bd.specialProduceMoney,
    guaranteeMoney: bd.guaranteeMoney,
    projectmoney: bd.projectmoney,
    stencilmoney: bd.stencilmoney,
    fillmoney: bd.fillmoney,
    comfirmFileMoney: bd.comfirmFileMoney,
    additionalCostItemList: bd.additionalCostItemList,
  }
}

async function openOrderPage(page) {
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    try {
      const alreadyReady = await page.locator('button:has-text("FR-4")').count().catch(() => 0)
      if (!alreadyReady) {
        await page.goto(SOURCE_URL, { waitUntil: 'commit', timeout: 180000 })
        await page.waitForLoadState('domcontentloaded', { timeout: 30000 }).catch(() => {})
      }
      // SPA 渲染可能远慢于 document 事件；轮询等待 FR-4，避免一次 60s 硬超时
      let ready = false
      for (let poll = 0; poll < 60; poll += 1) {
        await page.waitForTimeout(2000)
        await dismissOverlays(page)
        const fr4 = await page.locator('button:has-text("FR-4")').count()
        if (fr4 > 0) {
          ready = true
          break
        }
      }
      if (!ready) throw new Error('FR-4 button not visible after polling')
      await page.waitForTimeout(1200)
      await dismissOverlays(page)
      // 关闭常见引导/确认弹层
      await page.getByRole('button', { name: '确定' }).first().click({ force: true, timeout: 1500 }).catch(() => {})
      await page.getByRole('button', { name: '我已知悉' }).first().click({ force: true, timeout: 1500 }).catch(() => {})
      await dismissOverlays(page)
      return
    } catch (err) {
      if (attempt === 4) {
        const title = await page.title().catch(() => '')
        throw new Error(`order page unavailable at ${page.url()} (${title}): ${err}`)
      }
      await page.waitForTimeout(5000 * attempt)
    }
  }
}

async function selectMaterial(page, material) {
  await dismissOverlays(page)
  const exactButton = page.getByRole('button', { name: material.label, exact: true }).first()
  if (await exactButton.isVisible().catch(() => false)) {
    await exactButton.click({ force: true })
    await page.waitForTimeout(1200)
    await dismissOverlays(page)
    return
  }

  const fuzzyButton = page.getByRole('button', { name: new RegExp(material.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }).first()
  if (await fuzzyButton.isVisible().catch(() => false)) {
    await fuzzyButton.click({ force: true })
    await page.waitForTimeout(1200)
    await dismissOverlays(page)
    return
  }

  throw new Error(`material option not found: ${material.label}`)
}

async function selectLayer(page, layers) {
  if (!layers) return
  await dismissOverlays(page)

  const clicked = await page.evaluate((layerValue) => {
    const labelCandidates = [...document.querySelectorAll('*')]
      .filter((el) => el.textContent?.trim() === '板子层数')
    const label = labelCandidates[0]
    const section = label?.closest('.form-item, .jlc-form-item, tr, .el-row, .base-info-item') || label?.parentElement?.parentElement
    const candidates = [...document.querySelectorAll('button')].filter((btn) => {
      if (btn.textContent?.trim() !== String(layerValue)) return false
      const rect = btn.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) return false
      if (section?.contains(btn)) return true
      if (!label) return false
      const labelRect = label.getBoundingClientRect()
      return Math.abs(rect.top - labelRect.top) < 90 && rect.left > labelRect.left
    })

    if (candidates[0] instanceof HTMLElement) {
      candidates[0].click()
      return true
    }
    return false
  }, layers)

  if (!clicked) {
    await page.getByRole('button', { name: String(layers), exact: true }).first().click({ force: true }).catch(() => {})
  }

  await page.waitForTimeout(700)
  await dismissOverlays(page)
}

async function ensureProcessOption(page, name, { required = true } = {}) {
  const aliases = {
    OSP: ['OSP', 'OSP 免费'],
  }
  const candidates = aliases[name] || [name]
  let matched = null
  for (const candidate of candidates) {
    const escapedName = candidate.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/mm$/, '(?:mm)?')
    const option = page.getByRole('button', { name: new RegExp(`^\\s*${escapedName}\\s*$`) }).first()
    const visible = await option.isVisible({ timeout: 2500 }).catch(() => false)
    if (visible) {
      matched = { option, candidate }
      break
    }
  }
  if (!matched) {
    if (required) throw new Error(`process option not found: ${name}`)
    return { name, present: false, selected: true, implicitDefault: true }
  }
  const { option, candidate } = matched
  const selected = await option.evaluate((element) => /checked|active|selected|is-active/.test(element.className || ''))
  if (!selected) {
    await option.click({ force: true, timeout: 5000 })
    await page.waitForTimeout(500)
  }
  const selectedAfter = await option.evaluate((element) => /checked|active|selected|is-active/.test(element.className || ''))
  if (!selectedAfter) {
    if (required) throw new Error(`process option did not remain selected: ${candidate}`)
    return { name, present: true, selected: false, implicitDefault: false }
  }
  return { name, present: true, selected: true, implicitDefault: false }
}

async function ensurePanelDesignCount(page, count, { required = true } = {}) {
  const target = String(count)
  const applied = await page.evaluate((value) => {
    const label = [...document.querySelectorAll('*')].find((el) => el.textContent?.trim() === '拼板款数')
    const section = label?.closest('.form-item, .jlc-form-item, tr, .el-row, .base-info-item')
      || label?.parentElement?.parentElement
      || document.body
    const input = section.querySelector('.el-input-number input, input[type="number"], input[role="spinbutton"]')
    if (!(input instanceof HTMLInputElement)) return { ok: false, reason: 'input_missing' }
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new Event('change', { bubbles: true }))
    input.dispatchEvent(new Event('blur', { bubbles: true }))
    return { ok: input.value === value, value: input.value }
  }, target)
  await page.waitForTimeout(600)
  if (!applied.ok) {
    if (required) throw new Error(`panel design count not set: expected ${target}, got ${applied.value || applied.reason}`)
    return { name: target, present: false, selected: true, implicitDefault: true }
  }
  return { name: target, present: true, selected: true, implicitDefault: false }
}

async function readRequestedProcessState(page, sample) {
  const changedFields = Array.isArray(sample.processChangedFields)
    ? new Set(sample.processChangedFields)
    : null
  const requestedValue = (field, value) => (
    !changedFields || changedFields.has(field) ? value : null
  )
  const requested = {
    boardThickness: requestedValue('boardThickness', sample.boardThickness ? `${sample.boardThickness}mm` : null),
    solderColor: requestedValue('solderColor', sample.solderColor && sample.solderColor !== '页面默认' ? sample.solderColor : null),
    surfaceFinish: requestedValue('surfaceFinish', sample.surfaceFinish || null),
    copperThickness: requestedValue('copperThickness', sample.copperThickness || null),
    solderMaskCoverage: requestedValue(
      'solderMaskCoverage',
      sample.solderMaskCoverage && sample.solderMaskCoverage !== '页面默认' ? sample.solderMaskCoverage : null,
    ),
    panelDesignCount: requestedValue('panelDesignCount', sample.panelDesignCount || null),
  }
  return page.evaluate((fields) => {
    const state = {}
    for (const [field, requestedName] of Object.entries(fields)) {
      if (!requestedName) {
        state[field] = { requested: null, present: false, selected: true, implicitDefault: true }
        continue
      }
      if (field === 'panelDesignCount') {
        const label = [...document.querySelectorAll('*')].find((el) => el.textContent?.trim() === '拼板款数')
        const section = label?.closest('.form-item, .jlc-form-item, tr, .el-row, .base-info-item')
          || label?.parentElement?.parentElement
          || document.body
        const input = section.querySelector('.el-input-number input, input[type="number"], input[role="spinbutton"]')
        const value = input instanceof HTMLInputElement ? input.value : null
        state[field] = {
          requested: requestedName,
          present: Boolean(input),
          selected: value === String(requestedName),
          implicitDefault: false,
          actual: value,
        }
        continue
      }
      const aliases = field === 'surfaceFinish' && requestedName === 'OSP'
        ? ['OSP', 'OSP 免费']
        : [requestedName]
      const normalizedAliases = aliases.map((item) => item.replace(/mm$/, ''))
      const buttons = [...document.querySelectorAll('button')].filter((item) => {
        const text = (item.textContent || '').trim().replace(/mm$/, '')
        const rect = item.getBoundingClientRect()
        return normalizedAliases.includes(text) && rect.width > 0 && rect.height > 0
      })
      if (!buttons.length) {
        state[field] = { requested: requestedName, present: false, selected: true, implicitDefault: true }
        continue
      }
      const upgradedViaNotice = field === 'solderMaskCoverage'
        && requestedName === '过孔盖油'
        && (document.body?.innerText || '').includes('过孔盖油已经免费升级为过孔塞油')
      state[field] = {
        requested: requestedName,
        present: true,
        selected: upgradedViaNotice
          || buttons.some((button) => /checked|active|selected|is-active/.test(button.className || '')),
        implicitDefault: false,
        effectiveValue: upgradedViaNotice ? '过孔塞油（免费升级）' : requestedName,
        matchingButtonCount: buttons.length,
        selectedButtonCount: buttons.filter(
          (button) => /checked|active|selected|is-active/.test(button.className || ''),
        ).length,
      }
    }
    return state
  }, requested)
}

async function waitForStableQuote(page, sample, lengthCm, widthCm, {
  previousDomPrice = null,
  requireFresh = false,
  requiredStableCount = 1,
} = {}) {
  await page.locator('h2:has-text("价格明细")').scrollIntoViewIfNeeded().catch(() => {})

  const material = MATERIALS[sample.materialKey || 'fr4'] || MATERIALS.fr4
  let best = null
  let lastDom = null
  let stableCount = 0
  let sawFreshPrice = !requireFresh || previousDomPrice == null

  for (let attempt = 0; attempt < 12; attempt += 1) {
    await page.waitForTimeout(attempt === 0 ? 1000 : 500)
    const apiPrice = readTrackedPriceApi(page)
    const price = await readPrice(page, apiPrice)
    const formState = await readFormState(page)
    const merged = { ...price, ...formState }

    const specReady = Number(formState.selectedQuantity) === Number(sample.quantity)
      && Number(formState.selectedLengthCm) === Number(lengthCm)
      && Number(formState.selectedWidthCm) === Number(widthCm)
      && formState.selectedMaterialLabel === material.label
      && Number(formState.selectedLayers) === Number(sample.layers)

    if (!specReady) {
      await selectMaterial(page, material)
      await selectLayer(page, sample.layers)
      await fillBoardSize(page, lengthCm, widthCm)
      await selectQuantity(page, sample.quantity)
      stableCount = 0
      lastDom = null
      continue
    }

    if (price.domPriceCny === lastDom && price.domPriceCny) {
      stableCount += 1
    } else {
      stableCount = 0
      lastDom = price.domPriceCny
    }
    if (price.domPriceCny && price.domPriceCny !== previousDomPrice) {
      sawFreshPrice = true
    }

    best = merged

    if (stableCount >= requiredStableCount && price.domPriceCny && sawFreshPrice) {
      return best
    }
  }

  if (best?.displayedPriceCny) {
    if (requireFresh && previousDomPrice != null && Number(best.domPriceCny) === Number(previousDomPrice)) {
      throw new Error(`stale price for ${sample.id}: still ${previousDomPrice}`)
    }
    return best
  }
  throw new Error(`price not stable for ${sample.id}`)
}

async function setQuote(page, sample, {
  reloadPage = false,
  reuseMaterialProcess = false,
  previousDomPrice = null,
} = {}) {
  if (reloadPage) {
    await openOrderPage(page)
  } else {
    await dismissOverlays(page)
  }

  resetTrackedPriceApi(page)
  const material = MATERIALS[sample.materialKey || 'fr4'] || MATERIALS.fr4
  const changedFields = Array.isArray(sample.processChangedFields)
    ? new Set(sample.processChangedFields)
    : null
  const shouldSelectProcess = (field) => !changedFields || changedFields.has(field)
  if (!reuseMaterialProcess) {
    await selectMaterial(page, material)
    await selectLayer(page, sample.layers)
  }

  const lengthCm = mmToCm(sample.widthMm)
  const widthCm = mmToCm(sample.heightMm)
  await fillBoardSize(page, lengthCm, widthCm)

  await dismissOverlays(page)
  await selectQuantity(page, sample.quantity)
  await page.keyboard.press('Escape').catch(() => {})

  if (!reuseMaterialProcess) {
    await page.getByRole('button', { name: '不需要' }).first().click({ force: true, timeout: 1500 }).catch(() => {})
    await page.getByRole('button', { name: '工业/消费/其他类电子产品' }).click({ force: true, timeout: 1500 }).catch(() => {})

    if (shouldSelectProcess('solderColor') && sample.solderColor && sample.solderColor !== '页面默认') {
      await ensureProcessOption(page, sample.solderColor)
    } else if (!changedFields && material.key === 'fr4') {
      await page.getByRole('button', { name: '绿色', exact: true }).first().click({ force: true, timeout: 1500 }).catch(() => {})
    }

    if (shouldSelectProcess('surfaceFinish') && sample.surfaceFinish) {
      await ensureProcessOption(page, sample.surfaceFinish)
    } else if (!changedFields && material.key === 'fr4') {
      await page.getByRole('button', { name: '有铅喷锡', exact: true }).first().click({ force: true, timeout: 1500 }).catch(() => {})
    }

    if (shouldSelectProcess('boardThickness') && sample.boardThickness) {
      await ensureProcessOption(page, `${sample.boardThickness}mm`, {
        required: !['1.6', '0.11'].includes(String(sample.boardThickness)),
      })
    } else if (!changedFields && material.key === 'fr4') {
      const thick16 = page.getByRole('button', { name: '1.6mm', exact: true })
      if (await thick16.count()) {
        const enabled = await thick16.first().isEnabled().catch(() => false)
        if (enabled) await thick16.first().click({ force: true, timeout: 1500 }).catch(() => {})
      }
    }
    if (shouldSelectProcess('copperThickness') && sample.copperThickness) {
      await ensureProcessOption(page, sample.copperThickness, {
        required: sample.copperThickness !== '1oz',
      })
    }
    if (shouldSelectProcess('solderMaskCoverage') && sample.solderMaskCoverage && sample.solderMaskCoverage !== '页面默认') {
      await ensureProcessOption(page, sample.solderMaskCoverage, {
        required: !['过孔盖油'].includes(sample.solderMaskCoverage),
      })
    }
    if (shouldSelectProcess('panelDesignCount') && sample.panelDesignCount) {
      await ensurePanelDesignCount(page, sample.panelDesignCount, {
        required: String(sample.panelDesignCount) !== '1',
      })
    }
  }

  await page.waitForTimeout(reuseMaterialProcess ? 2500 : 1200)
  const price = await waitForStableQuote(page, sample, lengthCm, widthCm, {
    previousDomPrice,
    requireFresh: reuseMaterialProcess,
    requiredStableCount: Number(process.env.JLC_STABLE_COUNT || 2),
  })
  return {
    ...price,
    selectedProcessOptions: await readRequestedProcessState(page, sample),
    pageFingerprint: await readPageFingerprint(page),
  }
}

async function readExistingResults(outFile) {
  try {
    const rows = JSON.parse(await fs.readFile(outFile, 'utf8'))
    return Array.isArray(rows) ? rows : []
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

async function writeResults(outFile, samples, resultsById) {
  // 合并写回：续采子集时保留文件中其它规格样本，避免覆盖丢失
  const existing = await readExistingResults(outFile)
  const merged = new Map(existing.map((row) => [row.id, row]))
  for (const sample of samples) {
    const row = resultsById.get(sample.id)
    if (row) merged.set(sample.id, row)
  }
  const rows = [...merged.values()].sort((a, b) => String(a.id).localeCompare(String(b.id)))
  const tempFile = `${outFile}.tmp`
  await fs.writeFile(tempFile, JSON.stringify(rows, null, 2), 'utf8')
  await fs.rm(outFile, { force: true })
  await fs.rename(tempFile, outFile)
}

function isSuccessfulDomSample(row) {
  return row?.priceSource === 'dom'
    && Number(row.domPriceCny) > 0
    && !row.error
    && row.quarantined !== true
}

function prepareResumeResults(existing, samples) {
  const targetById = new Map(samples.map((sample) => [sample.id, sample]))
  const resultsById = new Map(existing
    .filter((row) => targetById.has(row.id))
    .map((row) => [row.id, row]))
  const groups = new Map()

  for (const sample of samples) {
    const groupKey = sample.baseSampleId || sample.id
    if (!groups.has(groupKey)) groups.set(groupKey, [])
    groups.get(groupKey).push(sample)
  }

  for (const groupSamples of groups.values()) {
    if (groupSamples.length < 3) continue
    const rows = groupSamples
      .map((sample) => resultsById.get(sample.id))
      .filter((row) => row && isSuccessfulDomSample(row))
    if (rows.length !== groupSamples.length) continue
    const prices = rows.map((row) => Number(row.domPriceCny)).sort((a, b) => a - b)
    const medianPrice = prices[Math.floor(prices.length / 2)]
    for (const row of rows) {
      if (Math.abs(Number(row.domPriceCny) - medianPrice) / medianPrice > 0.02) {
        resultsById.delete(row.id)
        console.log(JSON.stringify({ id: row.id, status: 'resume_reject_unstable_repeat' }))
      }
    }
  }

  return resultsById
}

function hasSameSpec(row, sample) {
  return (row.materialKey || 'fr4') === (sample.materialKey || 'fr4')
    && (!sample.samplingVersion || row.samplingVersion === sample.samplingVersion)
    && Number(row.layers) === Number(sample.layers)
    && Number(row.widthMm) === Number(sample.widthMm)
    && Number(row.heightMm) === Number(sample.heightMm)
    && Number(row.quantity) === Number(sample.quantity)
    && String(row.boardThickness || '') === String(sample.boardThickness || '')
    && String(row.solderColor || '') === String(sample.solderColor || '')
    && String(row.surfaceFinish || '') === String(sample.surfaceFinish || '')
    && String(row.copperThickness || '') === String(sample.copperThickness || '')
    && String(row.solderMaskCoverage || '') === String(sample.solderMaskCoverage || '')
    && String(row.panelDesignCount || '') === String(sample.panelDesignCount || '')
    && JSON.stringify(row.processChangedFields) === JSON.stringify(sample.processChangedFields)
}

function quoteSpecKey(sample) {
  return [
    sample.materialKey || 'fr4',
    sample.layers,
    sample.widthMm,
    sample.heightMm,
    sample.quantity,
    sample.boardThickness || '',
    sample.solderColor || '',
    sample.surfaceFinish || '',
    sample.copperThickness || '',
    sample.solderMaskCoverage || '',
    sample.panelDesignCount || '',
  ].join('|')
}

function materialProcessKey(sample) {
  return [
    sample.materialKey || 'fr4',
    sample.layers,
    sample.boardThickness || '',
    sample.solderColor || '',
    sample.surfaceFinish || '',
    sample.copperThickness || '',
    sample.solderMaskCoverage || '',
    sample.panelDesignCount || '',
  ].join('|')
}

function buildSampleResult(sample, price, sampleTime) {
  const material = MATERIALS[sample.materialKey || 'fr4'] || MATERIALS.fr4
  const areaM2 = (sample.widthMm * sample.heightMm * sample.quantity) / 1_000_000
  const unitPrice = price.displayedPriceCny != null ? Number((price.displayedPriceCny / sample.quantity).toFixed(4)) : null
  const areaPrice = price.displayedPriceCny != null && areaM2 > 0 ? Number((price.displayedPriceCny / areaM2).toFixed(2)) : null
  return {
    ...sample,
    materialLabel: material.label,
    sampleTime,
    sourceUrl: SOURCE_URL,
    currency: 'CNY',
    lengthCm: mmToCm(sample.widthMm),
    widthCm: mmToCm(sample.heightMm),
    fixedOptions: `${material.label}, ${material.fixedOptions || '页面默认工艺'}, 工业/消费类, 不需要确认生产稿, 默认测试项`,
    displayedPriceCny: price.displayedPriceCny,
    domPriceCny: price.domPriceCny,
    apiPriceCny: price.apiPriceCny,
    apiDomDiff: price.apiDomDiff,
    priceSource: price.priceSource,
    hasSpecialOffer: price.hasSpecialOffer === true,
    quarantined: price.quarantined === true,
    quarantineReasons: price.quarantineReasons || [],
    selectedQuantity: price.selectedQuantity,
    selectedLengthCm: price.selectedLengthCm,
    selectedWidthCm: price.selectedWidthCm,
    selectedMaterialLabel: price.selectedMaterialLabel,
    selectedLayers: price.selectedLayers,
    selectedProcessOptions: price.selectedProcessOptions || null,
    pageFingerprint: price.pageFingerprint || null,
    unitPriceCny: unitPrice,
    areaPriceEstimateCnyPerM2: areaPrice,
    notes: '中文站公开下单页样本；尺寸输入单位为 cm（方案 mm 已换算）；不含运费/税费/Gerber 审核附加费',
    priceText: price.priceText,
    priceBreakdown: slimBreakdown(price.priceBreakdown),
  }
}

async function runWithBrowser(browser, samples, outFile, sampleTime, { leaveOpen = false } = {}) {
  const contextScope = process.env.JLC_CONTEXT_SCOPE
    || (process.env.JLC_FRESH_CONTEXT_PER_SAMPLE === 'false' ? 'shared' : 'sample')
  if (!['sample', 'spec', 'shared'].includes(contextScope)) {
    throw new Error(`unsupported JLC_CONTEXT_SCOPE: ${contextScope}`)
  }
  const freshContextPerSample = contextScope === 'sample'
  const freshContextPerSpec = contextScope === 'spec'
  const existing = await readExistingResults(outFile)
  const resultsById = prepareResumeResults(existing, samples)
  let sharedContext = null
  let sharedPage = null
  let activeContextSpecKey = null
  let lastAppliedSpecKey = null
  let lastMaterialProcessKey = null
  let lastDomPrice = null
  const failedBaseSampleIds = new Set()
  const reuseDefaultContext = leaveOpen && !freshContextPerSample && !freshContextPerSpec

  const createContext = async () => {
    if (reuseDefaultContext) {
      const existingContexts = browser.contexts()
      if (existingContexts.length) return existingContexts[0]
    }
    return browser.newContext({
      locale: 'zh-CN',
      viewport: { width: 1400, height: 900 },
    })
  }

  for (const sample of samples) {
    const baseSampleId = sample.baseSampleId || sample.id
    if (failedBaseSampleIds.has(baseSampleId)) {
      resultsById.set(sample.id, {
        ...sample,
        error: `group_skipped_after_failure: ${baseSampleId}`,
        errorClass: 'repeat_group_failed',
        failedAt: new Date().toISOString(),
      })
      await writeResults(outFile, samples, resultsById)
      continue
    }
    const previous = resultsById.get(sample.id)
    if (isSuccessfulDomSample(previous) && hasSameSpec(previous, sample)) {
      console.log(JSON.stringify({ id: sample.id, status: 'resume_skip', price: previous.domPriceCny }))
      continue
    }

    let lastError = null
    const maxSampleAttempts = Number(process.env.JLC_SAMPLE_ATTEMPTS || 3)
    for (let attempt = 1; attempt <= maxSampleAttempts; attempt += 1) {
      const currentSpecKey = quoteSpecKey(sample)
      if (!freshContextPerSample && (
        !sharedContext || (freshContextPerSpec && activeContextSpecKey !== currentSpecKey)
      )) {
        await sharedPage?.close().catch(() => {})
        if (sharedContext && !reuseDefaultContext) {
          await sharedContext.close().catch(() => {})
        }
        sharedContext = await createContext()
        sharedPage = null
        if (reuseDefaultContext) {
          const existingPage = sharedContext.pages().find((page) => /pcbPlaceOrder|jlc\.com/.test(page.url()))
          if (existingPage) sharedPage = existingPage
        }
        activeContextSpecKey = freshContextPerSpec ? currentSpecKey : null
        lastAppliedSpecKey = null
        lastMaterialProcessKey = null
        lastDomPrice = null
      }
      const context = freshContextPerSample ? await browser.newContext({
        locale: 'zh-CN',
        viewport: { width: 1400, height: 900 },
      }) : sharedContext
      const page = freshContextPerSample ? await context.newPage() : (sharedPage || await context.newPage())
      if (!freshContextPerSample) sharedPage = page
      if (!trackedPriceApi.has(page)) trackPriceApi(page)

      try {
        if (freshContextPerSample || page.url() === 'about:blank') {
          await openOrderPage(page)
        }
        const currentMaterialProcessKey = materialProcessKey(sample)
        const price = !freshContextPerSample && lastAppliedSpecKey === currentSpecKey
          ? {
              ...await waitForStableQuote(page, sample, mmToCm(sample.widthMm), mmToCm(sample.heightMm)),
              selectedProcessOptions: await readRequestedProcessState(page, sample),
            }
          : await setQuote(page, sample, {
            reuseMaterialProcess: !freshContextPerSample && lastMaterialProcessKey === currentMaterialProcessKey,
            previousDomPrice: lastDomPrice,
          })
        lastAppliedSpecKey = currentSpecKey
        lastMaterialProcessKey = currentMaterialProcessKey
        lastDomPrice = price.domPriceCny
        resultsById.set(sample.id, buildSampleResult(sample, price, sampleTime))
        await writeResults(outFile, samples, resultsById)
        console.log(JSON.stringify({
          id: sample.id,
          material: sample.materialKey || 'fr4',
          layers: sample.layers,
          sizeMm: `${sample.widthMm}x${sample.heightMm}`,
          qty: sample.quantity,
          price: price.displayedPriceCny,
        }))
        lastError = null
        if (freshContextPerSample) {
          await page.close()
          await context.close()
        }
        break
      } catch (err) {
        lastError = err
        console.log(JSON.stringify({ id: sample.id, attempt, error: String(err) }))
        if (/Target page, context or browser has been closed|browser has been closed/i.test(String(err))) {
          throw new Error(`browser_session_closed: ${err}`)
        }
        if (freshContextPerSample) {
          await page.close().catch(() => {})
          await context.close().catch(() => {})
        } else if (freshContextPerSpec) {
          await page.close().catch(() => {})
          await context.close().catch(() => {})
          sharedContext = null
          activeContextSpecKey = null
          sharedPage = null
        } else if (reuseDefaultContext) {
          // CDP 默认上下文不能关闭最后一个页面，否则可见 Chrome 会随之退出。
          await page.reload({ waitUntil: 'domcontentloaded', timeout: 60_000 }).catch(() => {})
          sharedPage = page
        } else {
          await page.close().catch(() => {})
          sharedPage = null
        }
        lastAppliedSpecKey = null
        lastMaterialProcessKey = null
        lastDomPrice = null
        await page.waitForTimeout(Math.min(8000, 1000 * (2 ** (attempt - 1)))).catch(() => {})
      }
    }

    if (lastError) {
      failedBaseSampleIds.add(baseSampleId)
      resultsById.set(sample.id, {
        ...sample,
        error: String(lastError),
        errorClass: classifySampleError(lastError),
        failedAt: new Date().toISOString(),
      })
      await writeResults(outFile, samples, resultsById)
      console.log(JSON.stringify({
        id: sample.id,
        status: 'failed',
        errorClass: classifySampleError(lastError),
        error: String(lastError).slice(0, 240),
      }))
    }
    const nextSample = samples[samples.indexOf(sample) + 1]
    await sleep(nextSample && quoteSpecKey(nextSample) === quoteSpecKey(sample) ? 500 : 1500)
  }

  // CDP 接管模式保留用户可见页面和默认上下文，便于连续批次续采。
  if (!leaveOpen) {
    await sharedPage?.close().catch(() => {})
    if (sharedContext && !reuseDefaultContext) {
      await sharedContext.close().catch(() => {})
    }
  }
  if (!leaveOpen) {
    await browser.close()
  }
  await writeResults(outFile, samples, resultsById)
  console.log(`Wrote ${resultsById.size} samples to ${outFile}`)
}

async function main() {
  const mode = process.argv[2] || 'smoke'
  const outFile = process.argv[3] || `scripts/jlc-cn-browser-${mode.endsWith('.json') ? 'custom' : mode}.json`
  const targetFileByMode = {
    'pcb-golden': 'scripts/jlc-cn-pcb-golden-targets.json',
    'pcb-holdout': 'scripts/jlc-cn-pcb-holdout-targets.json',
    'pcb-process-v7': 'scripts/jlc-cn-pcb-process-v7-targets.json',
    'pcb-process-holdout-v7': 'scripts/jlc-cn-pcb-process-holdout-v7-targets.json',
    'pcb-acceptance-v7': 'scripts/jlc-cn-pcb-v7-acceptance-targets.json',
    'pcb-boundary-v8': 'scripts/jlc-cn-pcb-v8-boundary-fit-targets.json',
    'pcb-tuning-v8': 'scripts/jlc-cn-pcb-v8-tuning-holdout-targets.json',
    'pcb-acceptance-v8': 'scripts/jlc-cn-pcb-v8-acceptance-targets.json',
    'pcb-fit-v9': 'scripts/jlc-cn-pcb-v9-boundary-fit-targets.json',
    'pcb-tuning-v9': 'scripts/jlc-cn-pcb-v9-tuning-holdout-targets.json',
    'pcb-process-v9': 'scripts/jlc-cn-pcb-v9-process-holdout-targets.json',
    'pcb-acceptance-v9': 'scripts/jlc-cn-pcb-v9-acceptance-targets.json',
    'pcb-fit-v10': 'scripts/jlc-cn-pcb-v10-fpc-fit-targets.json',
    'pcb-tuning-v10': 'scripts/jlc-cn-pcb-v10-tuning-holdout-targets.json',
    'pcb-process-v10': 'scripts/jlc-cn-pcb-v10-process-holdout-targets.json',
    'pcb-acceptance-v10': 'scripts/jlc-cn-pcb-v10-acceptance-targets.json',
  }
  const targetFile = mode.endsWith('.json') ? mode : targetFileByMode[mode]
  const samples = targetFile
    ? JSON.parse(await fs.readFile(targetFile, 'utf8'))
    : buildSamples(mode)
  const sampleTime = new Date().toISOString()
  const headless = process.env.JLC_HEADLESS !== 'false'

  const cdpUrl = process.env.JLC_CDP_URL
  if (cdpUrl) {
    const browser = await chromium.connectOverCDP(cdpUrl)
    console.log(JSON.stringify({ status: 'browser_connected_cdp', cdpUrl }))
    await runWithBrowser(browser, samples, outFile, sampleTime, { leaveOpen: true })
    // Playwright CDP connection keeps the Node event loop alive even after work
    // finishes. Exit without browser.close() so the user-visible Chrome remains.
    process.exit(0)
  }

  const preferredChannel = process.env.JLC_BROWSER_CHANNEL || ''
  const channels = preferredChannel
    ? [preferredChannel]
    : ['chrome', 'msedge']
  const userDataDir = process.env.JLC_USER_DATA_DIR

  if (userDataDir) {
    for (const channel of channels) {
      try {
        const context = await chromium.launchPersistentContext(userDataDir, {
          headless,
          channel,
          viewport: { width: 1400, height: 900 },
          locale: 'zh-CN',
          args: ['--disable-blink-features=AutomationControlled'],
        })
        const browserFacade = {
          contexts: () => [context],
          newContext: async () => context,
          close: async () => context.close().catch(() => {}),
        }
        console.log(JSON.stringify({
          status: 'browser_launched_persistent',
          channel,
          headless,
          userDataDir,
        }))
        return runWithBrowser(browserFacade, samples, outFile, sampleTime)
      } catch (err) {
        console.log(JSON.stringify({
          status: 'browser_persistent_launch_failed',
          channel,
          error: String(err),
        }))
      }
    }
  }

  for (const channel of channels) {
    try {
      const browser = await chromium.launch({
        headless,
        channel,
        args: ['--disable-blink-features=AutomationControlled'],
      })
      console.log(JSON.stringify({ status: 'browser_launched', channel, headless }))
      return runWithBrowser(browser, samples, outFile, sampleTime)
    } catch (err) {
      console.log(JSON.stringify({ status: 'browser_launch_failed', channel, error: String(err) }))
    }
  }

  const browser = await chromium.launch({
    headless,
    args: ['--disable-blink-features=AutomationControlled'],
  })
  console.log(JSON.stringify({ status: 'browser_launched', channel: 'chromium', headless }))
  return runWithBrowser(browser, samples, outFile, sampleTime)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
