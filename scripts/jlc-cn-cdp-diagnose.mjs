import { chromium } from 'playwright'

const browser = await chromium.connectOverCDP('http://127.0.0.1:9222')
try {
  console.log(JSON.stringify({ contexts: browser.contexts().length }))
  for (const context of browser.contexts()) {
    for (const page of context.pages()) {
      const fr4 = await page.locator('button:has-text("FR-4")').count().catch(() => -1)
      const title = await page.title().catch(() => '')
      const body = (await page.locator('body').innerText().catch(() => '')).slice(0, 120)
      console.log(JSON.stringify({ url: page.url(), title, fr4, body }))
    }
  }
} finally {
  await browser.close()
}
