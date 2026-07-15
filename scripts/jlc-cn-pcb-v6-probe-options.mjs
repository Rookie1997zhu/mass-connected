/**
 * Probe JLC CN process option availability for v6 freeze.
 * Usage: node scripts/jlc-cn-pcb-v6-probe-options.mjs
 */
import fs from 'node:fs/promises'
import { chromium } from 'playwright'

const ORDER_URL = 'https://www.jlc.com/newOrder/#/pcb/pcbPlaceOrder?spm=PCB.Homepage.functionbar.1002'
const MATERIALS = [
  { key: 'fr4', label: 'FR-4', layers: [2, 4] },
  { key: 'fpc', label: 'FPC软板', layers: [1, 2] },
  { key: 'aluminum', label: '铝基板', layers: [1] },
]

const SECTION_LABELS = [
  '拼板款数',
  '成品板厚',
  '阻焊颜色',
  '阻焊覆盖',
  '焊盘喷镀',
  '外层铜厚',
  '铜厚',
  '是否SMT贴片',
]

async function dismissOverlays(page) {
  for (let i = 0; i < 3; i += 1) {
    await page.keyboard.press('Escape').catch(() => {})
    await page.waitForTimeout(200)
  }
}

async function selectMaterial(page, label) {
  const btn = page.getByRole('button', { name: label, exact: true }).first()
  await btn.click({ force: true, timeout: 8000 })
  await page.waitForTimeout(1200)
}

async function selectLayer(page, layers) {
  const btn = page.getByRole('button', { name: String(layers), exact: true }).first()
  await btn.click({ force: true, timeout: 5000 })
  await page.waitForTimeout(800)
}

async function fillSizeAndQty(page) {
  const length = page.getByPlaceholder('长').first()
  const width = page.getByPlaceholder('宽').first()
  await length.fill('10')
  await width.fill('10')
  await page.getByPlaceholder('数量').first().click({ force: true })
  await page.waitForTimeout(400)
  const qty5 = page.getByRole('button', { name: '5', exact: true }).first()
  if (await qty5.isVisible().catch(() => false)) {
    await qty5.click({ force: true })
  }
  await page.keyboard.press('Escape').catch(() => {})
  await page.waitForTimeout(1500)
}

async function readSectionOptions(page) {
  return page.evaluate((sectionLabels) => {
    const normalize = (text) => (text || '').replace(/\s+/g, ' ').trim()
    const isVisible = (el) => {
      const rect = el.getBoundingClientRect()
      return rect.width > 0 && rect.height > 0
    }
    const allText = normalize(document.body.innerText)
    const result = {
      pageHasOz: /oz/i.test(allText),
      pageHasCopperLabel: /铜厚|外层铜厚|内层铜厚/.test(allText),
      sections: {},
      allVisibleButtons: [],
    }

    const labels = [...document.querySelectorAll('*')].filter((el) => {
      if (!isVisible(el)) return false
      const text = normalize(el.textContent)
      return sectionLabels.includes(text) && text.length < 20
    })

    for (const labelEl of labels) {
      const label = normalize(labelEl.textContent)
      let container = labelEl.parentElement
      for (let depth = 0; depth < 6 && container; depth += 1) {
        const buttons = [...container.querySelectorAll('button')]
          .filter(isVisible)
          .map((btn) => ({
            text: normalize(btn.textContent).slice(0, 80),
            disabled: btn.disabled || /disabled|is-disabled/.test(btn.className || ''),
            selected: /checked|active|selected|is-active/.test(btn.className || ''),
          }))
          .filter((item) => item.text && item.text !== label)
        const spin = container.querySelector('input[type="number"], input[role="spinbutton"], .el-input-number input')
        if (buttons.length || spin) {
          result.sections[label] = {
            buttons,
            spin: spin
              ? {
                value: spin.value,
                min: spin.min || spin.getAttribute('aria-valuemin'),
                max: spin.max || spin.getAttribute('aria-valuemax'),
              }
              : null,
          }
          break
        }
        container = container.parentElement
      }
    }

    result.allVisibleButtons = [...document.querySelectorAll('button')]
      .filter(isVisible)
      .map((btn) => normalize(btn.textContent).slice(0, 60))
      .filter((text) => /oz|盖油|开窗|塞油|树脂|铜浆|OSP|喷锡|沉金|拼板|绿色|红色|蓝色|白色|哑黑|黄色|紫色|黑色/i.test(text))
      .slice(0, 120)

    return result
  }, SECTION_LABELS)
}

async function probeOne(page, material, layers) {
  await page.goto(ORDER_URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(2500)
  await dismissOverlays(page)
  await selectMaterial(page, material.label)
  await selectLayer(page, layers)
  await fillSizeAndQty(page)
  await dismissOverlays(page)
  const options = await readSectionOptions(page)
  return {
    materialKey: material.key,
    materialLabel: material.label,
    layers,
    ...options,
  }
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } })
const rows = []
try {
  for (const material of MATERIALS) {
    for (const layers of material.layers) {
      console.log(`probing ${material.key} ${layers}L...`)
      const row = await probeOne(page, material, layers)
      rows.push(row)
      console.log(JSON.stringify({
        material: row.materialKey,
        layers: row.layers,
        pageHasOz: row.pageHasOz,
        pageHasCopperLabel: row.pageHasCopperLabel,
        sectionKeys: Object.keys(row.sections || {}),
        solderMask: row.sections?.['阻焊覆盖']?.buttons?.map((b) => `${b.text}${b.disabled ? '(disabled)' : ''}`),
        surface: row.sections?.['焊盘喷镀']?.buttons?.map((b) => `${b.text}${b.disabled ? '(disabled)' : ''}`),
        colors: row.sections?.['阻焊颜色']?.buttons?.map((b) => b.text),
        panel: row.sections?.['拼板款数'],
      }, null, 2))
    }
  }
} finally {
  await browser.close()
}

await fs.writeFile('scripts/jlc-cn-pcb-v6-options-probe.json', JSON.stringify({
  probedAt: new Date().toISOString(),
  rows,
}, null, 2), 'utf8')
console.log('wrote scripts/jlc-cn-pcb-v6-options-probe.json')
