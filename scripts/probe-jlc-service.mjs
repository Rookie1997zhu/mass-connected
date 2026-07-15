const url = 'https://cart.jlcpcb.com/api/overseas-core-platform/shoppingCart/quereyOrderService'
const res = await fetch(url, {
  method: 'POST',
  headers: {
    'content-type': 'application/json',
    origin: 'https://cart.jlcpcb.com',
    referer: 'https://cart.jlcpcb.com/quote',
  },
  body: '{}',
})
const data = await res.json()
console.log(JSON.stringify(data, null, 2).slice(0, 8000))
