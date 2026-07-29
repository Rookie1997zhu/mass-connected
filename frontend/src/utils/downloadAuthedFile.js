import http from '../api/http'

/** 将绝对或相对 file_url 转为可请求路径；统一走 /api（含鉴权媒体下载）。 */
export function toApiPath(fileUrl) {
  if (!fileUrl) return ''
  try {
    const u = new URL(fileUrl, window.location.origin)
    let path = u.pathname + u.search
    if (path.startsWith('/api/')) path = path.slice(4)
    return path
  } catch {
    const s = String(fileUrl)
    return s.replace(/^\/api/, '')
  }
}

/**
 * 通过 JWT 鉴权拉取文件并触发浏览器下载。
 */
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

/** 鉴权拉取为 blob URL（用于 img / iframe / 预览）。调用方负责 revoke。 */
export async function fetchAuthedBlobUrl(fileUrl) {
  const path = toApiPath(fileUrl)
  if (!path) throw new Error('missing file url')
  const data = await http.get(path, { responseType: 'blob' })
  const blob = data instanceof Blob ? data : new Blob([data])
  return URL.createObjectURL(blob)
}
