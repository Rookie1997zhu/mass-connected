const html = await fetch('https://cart.jlcpcb.com/quote?orderType=1&stencilLayer=2&stencilWidth=100&stencilLength=100').then((r) => r.text())
const jsPath = html.match(/\/shop-cart-static\/js\/6725cb48a3ea6138bda0\.js/)?.[0]
const js = await fetch(`https://cart.jlcpcb.com${jsPath}`).then((r) => r.text())
const idx = js.indexOf('calculationGoodsCostsNew(')
console.log('calls', (js.match(/calculationGoodsCostsNew\(/g) || []).length)
let pos = 0
let n = 0
while ((pos = js.indexOf('calculationGoodsCostsNew(', pos)) !== -1 && n < 5) {
  console.log('\n=== call', n, '===')
  console.log(js.slice(Math.max(0, pos - 800), pos + 1200))
  pos += 10
  n += 1
}
