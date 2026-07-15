import { chromium } from 'playwright'

const url = 'https://www.jlc.com/newOrder/#/pcb/pcbPlaceOrder?spm=PCB.Homepage.functionbar.1002'
const launchOptions = [
  { name: 'headed-chrome', opts: { headless: false, channel: 'chrome' } },
  { name: 'headed-chromium', opts: { headless: false } },
  { name: 'headless-chrome', opts: { headless: true, channel: 'chrome' } },
]

for (const item of launchOptions) {
  let browser
  try {
    browser = await chromium.launch({
      ...item.opts,
      args: ['--disable-blink-features=AutomationControlled'],
    })
    const page = await browser.newPage({ locale: 'zh-CN', viewport: { width: 1400, height: 900 } })
    await page.goto(url, { waitUntil: 'commit', timeout: 120000 })
    let fr4 = 0
    for (let i = 0; i < 20; i += 1) {
      await page.waitForTimeout(2000)
      fr4 = await page.locator('button:has-text("FR-4")').count()
      if (fr4 > 0) break
    }
    const bodyLen = (await page.locator('body').innerText().catch(() => '')).length
    console.log(JSON.stringify({ mode: item.name, fr4, bodyLen, title: await page.title() }))
    await browser.close()
    if (fr4 > 0) process.exit(0)
  } catch (error) {
    console.log(JSON.stringify({ mode: item.name, error: String(error) }))
    await browser?.close().catch(() => {})
  }
}
process.exit(1)
