import http from '../api'

/** 将绝对或相对 file_url 转为 axios 可用的 /api 相对路径。 */
export function toApiPath(fileUrl) {
  if (!fileUrl) return ''
  try {
    const u = new URL(fileUrl, window.location.origin)
    let path = u.pathname + u.search
    if (path.startsWith('/api/')) path = path.slice(4)
    return path
  } catch {
    return String(fileUrl).replace(/^\/api/, '')
  }
}

export async function downloadAuthedFile(fileUrl, fileName = 'file') {
  const path = toApiPath(fileUrl)
  if (!path) throw new Error('missing file url')
  const data = await http.get(path, { responseType: 'blob' })
  const blob = data instanceof Blob ? data : new Blob([data])
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName || 'file'
  a.click()
  URL.revokeObjectURL(url)
}

export async function openAuthedFile(fileUrl) {
  const path = toApiPath(fileUrl)
  if (!path) throw new Error('missing file url')
  const data = await http.get(path, { responseType: 'blob' })
  const blob = data instanceof Blob ? data : new Blob([data])
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank', 'noopener')
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
