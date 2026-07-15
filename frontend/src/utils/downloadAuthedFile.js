import http from '../api/http'

/** 将绝对或相对 file_url 转为可请求路径；/media 走站点根路径，其余走 /api。 */
export function toApiPath(fileUrl) {
  if (!fileUrl) return ''
  try {
    const u = new URL(fileUrl, window.location.origin)
    let path = u.pathname + u.search
    // 公开媒体不走 /api 前缀
    if (path.startsWith('/media/')) return path
    if (path.startsWith('/api/')) path = path.slice(4)
    return path
  } catch {
    const s = String(fileUrl)
    if (s.startsWith('/media/')) return s
    return s.replace(/^\/api/, '')
  }
}

/**
 * 通过 JWT 鉴权拉取文件并触发浏览器下载。
 * /media 公开资源直接按站点路径拉取。
 */
export async function downloadAuthedFile(fileUrl, fileName = 'file') {
  const path = toApiPath(fileUrl)
  if (!path) throw new Error('missing file url')
  let blob
  if (path.startsWith('/media/')) {
    const res = await fetch(path)
    if (!res.ok) throw new Error(`download failed: ${res.status}`)
    blob = await res.blob()
  } else {
    const data = await http.get(path, { responseType: 'blob' })
    blob = data instanceof Blob ? data : new Blob([data])
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName || 'file'
  a.click()
  URL.revokeObjectURL(url)
}
