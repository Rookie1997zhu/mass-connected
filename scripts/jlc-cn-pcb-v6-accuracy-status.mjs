import fs from 'node:fs'
const path = 'scripts/jlc-cn-pcb-v6-accuracy-live.json'
if (!fs.existsSync(path)) {
  console.log('missing')
  process.exit(0)
}
const rows = JSON.parse(fs.readFileSync(path, 'utf8'))
const ok = rows.filter((row) => row.priceSource === 'dom' && row.domPriceCny > 0 && !row.error)
console.log(JSON.stringify({
  total: rows.length,
  ok: ok.length,
  err: rows.length - ok.length,
  last: rows.at(-1)?.id,
  lastPrice: rows.at(-1)?.domPriceCny || null,
  lastError: rows.at(-1)?.error || null,
}, null, 2))
