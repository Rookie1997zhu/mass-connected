import { chromium } from 'playwright'

const URL = 'https://www.jlc.com/newOrder/#/pcb/pcbPlaceOrder?spm=PCB.Homepage.functionbar.1002'

async function selectLayer(page, layers) {
  await page.evaluate((layerValue) => {
    const labelEl = [...document.querySelectorAll('*')].find((el) => el.textContent?.trim() === '板子层数')
    const section = labelEl?.closest('.form-item, .jlc-form-item, tr, .el-row, .base-info-item')
      || labelEl?.parentElement?.parentElement
    const candidates = [...document.querySelectorAll('button')].filter((btn) => {
      if (btn.textContent?.trim() !== String(layerValue)) return false
      const rect = btn.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) return false
      if (section?.contains(btn)) return true
      if (!labelEl) return false
      const lr = labelEl.getBoundingClientRect()
      return Math.abs(rect.top - lr.top) < 90 && rect.left > lr.left
    })
    candidates[0]?.click()
  }, layers)
}

async function probe(label, layers) {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } })
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(2000)
  await page.getByRole('button', { name: label, exact: true }).first().click({ force: true })
  await page.waitForTimeout(1500)
  await selectLayer(page, layers)
  await page.waitForTimeout(800)
  await page.evaluate(() => {
    const set = (input, value) => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      setter?.call(input, String(value))
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.dispatchEvent(new Event('change', { bubbles: true }))
    }
    set(document.querySelector('input[placeholder="长"]'), 10)
    set(document.querySelector('input[placeholder="宽"]'), 10)
  })
  await page.locator('input[placeholder="数量"]').first().click({ force: true })
  await page.waitForTimeout(600)
  await page.getByRole('button', { name: '5', exact: true }).last().click({ force: true }).catch(() => {})
  await page.keyboard.press('Escape').catch(() => {})
  await page.waitForTimeout(2500)

  const info = await page.evaluate(() => {
    const visible = (el) => {
      const rect = el.getBoundingClientRect()
      return rect.width > 0 && rect.height > 0
    }
    const buttons = [...document.querySelectorAll('button')].filter(visible).map((btn) => ({
      text: (btn.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80),
      disabled: btn.disabled || /disabled|is-disabled/.test(btn.className || ''),
      selected: /checked|active|selected|is-active/.test(btn.className || ''),
    }))
    const pick = (pred) => buttons.filter((btn) => pred(btn.text))
    const activeMat = [...document.querySelectorAll('button')].find((btn) => (
      ['FR-4', 'FPC软板', '铝基板'].includes(btn.textContent?.trim())
      && /active|selected|is-active|checked/.test(btn.className || '')
    ))
    const panel = document.querySelector('.el-input-number input, input[type="number"]')
    return {
      material: activeMat?.textContent?.trim() || null,
      bodyHasOz: /oz/i.test(document.body.innerText),
      bodyHasCopper: /铜厚|外层铜厚/.test(document.body.innerText),
      coverage: pick((text) => /过孔|盖油|开窗|塞油|树脂|铜浆/.test(text)),
      surface: pick((text) => /OSP|喷锡|沉金/.test(text)),
      colors: pick((text) => /绿色|红色|黄色|蓝色|白色|哑黑|黑色|紫|橙/.test(text)).slice(0, 24),
      thickness: pick((text) => /^\d+(\.\d+)?(mm)?$/.test(text)).slice(0, 24),
      panelSpin: panel ? { value: panel.value, min: panel.min, max: panel.max } : null,
    }
  })
  await browser.close()
  return { label, layers, ...info }
}

const rows = []
for (const item of [
  ['FR-4', 2],
  ['FR-4', 4],
  ['FPC软板', 1],
  ['FPC软板', 2],
  ['铝基板', 1],
]) {
  console.log(`probing ${item[0]} ${item[1]}L`)
  const row = await probe(item[0], item[1])
  rows.push(row)
  console.log(JSON.stringify(row, null, 2))
}

await import('node:fs/promises').then((fs) => fs.writeFile(
  'scripts/jlc-cn-pcb-v6-options-probe-v2.json',
  JSON.stringify({ probedAt: new Date().toISOString(), rows }, null, 2),
  'utf8',
))
