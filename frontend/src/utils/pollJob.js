import { fetchChatTranslateJob, fetchParseJob } from '../api'

export const CHAT_TRANSLATE_JOB_TIMEOUT = 60000

/**
 * 通用异步 job 短轮询：直至 done / failed / 超时。
 * @param {() => Promise<object>} fetchFn 返回响应对象（含 .data）的函数
 * @param {object} [opts]
 * @param {number} [opts.interval=1500] 轮询间隔（ms）
 * @param {number} [opts.timeout=90000] 超时（ms）
 * @param {string} [opts.notFoundCode='PARSE_JOB_NOT_FOUND'] 缺失 job 时错误码
 * @param {string} [opts.failedCode='PARSE_JOB_FAILED'] 任务失败默认错误码
 * @param {string} [opts.timeoutCode='PARSE_JOB_TIMEOUT'] 超时错误码
 * @returns {Promise<object>} job data（含 result）
 */
export async function pollJob(
  fetchFn,
  {
    interval = 1500,
    timeout = 90000,
    notFoundCode = 'PARSE_JOB_NOT_FOUND',
    failedCode = 'PARSE_JOB_FAILED',
    timeoutCode = 'PARSE_JOB_TIMEOUT',
  } = {},
) {
  if (typeof fetchFn !== 'function') {
    const err = new Error('missing job id')
    err.code = notFoundCode
    throw err
  }
  const started = Date.now()
  while (Date.now() - started < timeout) {
    const res = await fetchFn()
    const data = res?.data || {}
    const status = data.status
    if (status === 'done') return data
    if (status === 'failed') {
      const err = new Error(data.error_message || '任务失败')
      err.code = data.error_code || failedCode
      err.data = data
      throw err
    }
    await new Promise((resolve) => setTimeout(resolve, interval))
  }
  const err = new Error('任务超时，请稍后重试')
  err.code = timeoutCode
  throw err
}

/**
 * 短轮询异步 parse/preview job，直至 done / failed / 超时。
 * @returns {Promise<object>} job data（含 result）
 */
export async function pollParseJob(jobId, { interval = 1500, timeout = 90000 } = {}) {
  if (!jobId) {
    const err = new Error('missing job id')
    err.code = 'PARSE_JOB_NOT_FOUND'
    throw err
  }
  return pollJob(() => fetchParseJob(jobId), {
    interval,
    timeout,
    notFoundCode: 'PARSE_JOB_NOT_FOUND',
    failedCode: 'PARSE_JOB_FAILED',
    timeoutCode: 'PARSE_JOB_TIMEOUT',
  })
}

/**
 * 短轮询聊天消息翻译 job，直至 done / failed / 超时。
 * @returns {Promise<object>} job data（含 result.translated_text）
 */
export async function pollChatTranslateJob(
  role,
  jobId,
  { interval = 1500, timeout = CHAT_TRANSLATE_JOB_TIMEOUT } = {},
) {
  if (!jobId) {
    const err = new Error('missing job id')
    err.code = 'TRANSLATE_JOB_NOT_FOUND'
    throw err
  }
  return pollJob(() => fetchChatTranslateJob(role, jobId), {
    interval,
    timeout,
    notFoundCode: 'TRANSLATE_JOB_NOT_FOUND',
    failedCode: 'TRANSLATE_JOB_FAILED',
    timeoutCode: 'TRANSLATE_JOB_TIMEOUT',
  })
}
