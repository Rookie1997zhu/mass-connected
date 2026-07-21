import fs from 'node:fs/promises'

const entries = await fs.readdir('scripts')
const stale = entries.filter((name) => /^\.jlc-v12-.*\.json$/.test(name))
await Promise.all(stale.map((name) => fs.rm(`scripts/${name}`, { force: true })))
const rootEntries = await fs.readdir('.')
const profiles = rootEntries.filter((name) => /^\.jlc-playwright-profile-v12/.test(name))
await Promise.all(profiles.map((name) => fs.rm(name, { recursive: true, force: true })))
console.log(JSON.stringify({
  status: 'v12_temp_cleaned',
  removedBatchFiles: stale.length,
  removedProfiles: profiles.length,
}))
