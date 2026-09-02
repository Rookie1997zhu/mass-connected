/** 后端入库/硬编码中文 message → i18n key（与 notificationI18n 同模式） */
const CHINESE_MESSAGE_KEYS = {
  '邮箱已注册': 'errors.codes.MEMBER_EMAIL_EXISTS',
  '账号或密码错误': 'errors.codes.AUTH_CREDENTIALS_INVALID',
  '账号已禁用': 'errors.codes.MEMBER_INACTIVE',
  '验证链接无效': 'errors.codes.EMAIL_VERIFY_TOKEN_INVALID',
  '验证链接已过期': 'errors.codes.EMAIL_VERIFY_TOKEN_EXPIRED',
  '邮箱已验证': 'errors.codes.EMAIL_ALREADY_VERIFIED',
  '发送过于频繁，请稍后再试': 'errors.codes.RATE_LIMIT_EXCEEDED',
  '请先验证邮箱后再进行此操作': 'errors.codes.EMAIL_NOT_VERIFIED',
  '请使用企业会员注册（member_type=enterprise）': 'errors.codes.FACTORY_REGISTER_DEPRECATED',
  '缺少 refresh token': 'errors.codes.AUTH_REFRESH_MISSING',
  'refresh token 无效或已失效': 'errors.codes.AUTH_REFRESH_INVALID',
  '请求失败': 'errors.codes.COMMON_VALIDATION_ERROR',
  '服务器内部错误': 'errors.codes.COMMON_INTERNAL_ERROR',
  '无管理权限': 'errors.codes.AUTH_PERMISSION_DENIED',
  '需要会员登录': 'errors.codes.AUTH_PERMISSION_DENIED',
  '该功能仅限买家会员使用，当前为企业账号': 'errors.codes.AUTH_PERMISSION_DENIED',
  '需要已审核的企业会员': 'errors.codes.AUTH_PERMISSION_DENIED',
  '需要登录': 'errors.codes.AUTH_PERMISSION_DENIED',
  '当前状态不可修改询价': 'errors.codes.RFQ_STATUS_LOCKED',
  '请上传文件': 'errors.codes.MEDIA_FILE_TYPE_INVALID',
  '报价已过期': 'errors.codes.QUOTE_EXPIRED',
  '该报价已生成生产订单': 'errors.codes.PRODUCTION_ORDER_EXISTS',
  '文件不存在': 'errors.codes.FILE_MISSING',
  '暂无可下载的报价方案': 'errors.codes.QUOTE_PLANS_EMPTY',
  '暂不支持该报价类型': 'errors.codes.SIMPLE_QUOTE_TYPE_INVALID',
  '该报价已转为详细报价': 'errors.codes.SIMPLE_QUOTE_ALREADY_CONVERTED',
  '缺少可用的服务分类': 'errors.codes.SERVICE_CATEGORY_MISSING',
  '库存不足': 'errors.codes.PRODUCT_STOCK_INSUFFICIENT',
  '数量无效': 'errors.codes.CART_QUANTITY_INVALID',
  '购物车为空': 'errors.codes.CART_EMPTY',
  '无效的状态': 'errors.codes.ORDER_STATUS_INVALID',
  '文件大小超限': 'errors.codes.MEDIA_FILE_SIZE_EXCEEDED',
  '消息内容为空': 'errors.codes.VALIDATION_ERROR',
  '消息内容无效': 'errors.codes.VALIDATION_ERROR',
  '无权访问该会话': 'errors.codes.CHAT_NOT_PARTICIPANT',
  '生产单不存在': 'errors.codes.ORDER_NOT_FOUND',
  '当前无进行中的纠纷': 'errors.codes.CHAT_DISPUTE_REQUIRED',
  '发送失败': 'errors.codes.VALIDATION_ERROR',
  '付款凭证不存在': 'errors.codes.PAYMENT_PROOF_MISSING',
  '该付款已确认': 'errors.codes.PAYMENT_ALREADY_CONFIRMED',
  '充值凭证不存在': 'errors.codes.RECHARGE_PROOF_MISSING',
  '该充值已确认': 'errors.codes.RECHARGE_ALREADY_CONFIRMED',
  '调整积分不能为 0': 'errors.codes.POINT_AMOUNT_INVALID',
  '进度内容不能为空': 'errors.codes.PROJECT_UPDATE_CONTENT_REQUIRED',
  '无效的阶段状态': 'errors.codes.PROJECT_STAGE_STATUS_INVALID',
  '无效的项目状态': 'errors.codes.PROJECT_STATUS_INVALID',
  '无效的进度值': 'errors.codes.PROJECT_PROGRESS_INVALID',
  '当前状态不可接单': 'errors.codes.PRODUCTION_ORDER_STATUS_INVALID',
  '当前状态不可拒单': 'errors.codes.PRODUCTION_ORDER_STATUS_INVALID',
  '当前状态不可签署': 'errors.codes.CONTRACT_STATUS_INVALID',
  '暂无可用保密协议模板': 'errors.codes.NDA_TEMPLATE_MISSING',
  '请填写客户公司名称': 'errors.codes.NDA_COMPANY_REQUIRED',
  '营业执照不存在': 'errors.codes.SUPPLIER_LICENSE_MISSING',
  '企业名称必填': 'errors.fields.company_name',
  '文件解析超时，请改为手动填写参数': 'errors.codes.STP_PARSE_TIMEOUT',
  '文件解析失败，请改为手动填写参数': 'errors.codes.STP_PARSE_FAILED',
  'STP解析失败': 'errors.codes.PARSE_JOB_FAILED',
  'STP 解析失败': 'errors.codes.PARSE_JOB_FAILED',
  'OCR服务不可用，请改为手动填写参数': 'errors.codes.OCR_UNAVAILABLE',
  'OCR 服务不可用，请改为手动填写参数': 'errors.codes.OCR_UNAVAILABLE',
  '图纸解析超时，请改为手动填写参数': 'errors.codes.DRAWING_PARSE_TIMEOUT',
  '图纸解析失败，请改为手动填写参数': 'errors.codes.DRAWING_PARSE_FAILED',
  '图纸解析失败': 'errors.codes.PARSE_JOB_FAILED',
  '文档转换失败，请下载原件查看': 'errors.codes.PREVIEW_CONVERT_FAILED',
  '消息不存在': 'errors.codes.CHAT_MESSAGE_NOT_FOUND',
  '翻译失败': 'errors.codes.TRANSLATE_JOB_FAILED',
  '任务失败': 'errors.codes.PARSE_JOB_FAILED',
  '任务超时，请稍后重试': 'errors.codes.PARSE_JOB_TIMEOUT',
}

/** @param {unknown} errors */
export function extractFirstFieldError(errors) {
  if (!errors || typeof errors !== 'object') return null
  for (const [field, value] of Object.entries(errors)) {
    if (field === 'detail' || field === 'non_field_errors') {
      const msg = normalizeErrorValue(value)
      if (msg) return { field: null, message: msg }
      continue
    }
    const msg = normalizeErrorValue(value)
    if (msg) return { field, message: msg }
  }
  return null
}

/** @param {unknown} value */
function normalizeErrorValue(value) {
  if (value == null) return null
  if (typeof value === 'string') return value.trim() || null
  if (Array.isArray(value)) {
    for (const item of value) {
      const msg = normalizeErrorValue(item)
      if (msg) return msg
    }
    return null
  }
  if (typeof value === 'object') {
    if (typeof value.string === 'string') return value.string.trim() || null
    if (typeof value.message === 'string') return value.message.trim() || null
    return normalizeErrorValue(Object.values(value))
  }
  return String(value)
}

/**
 * @param {string | null | undefined} message
 * @returns {string | null} i18n key
 */
function mapChineseMessage(message) {
  if (!message || typeof message !== 'string') return null
  const trimmed = message.trim()
  return CHINESE_MESSAGE_KEYS[trimmed] || null
}

/**
 * @param {string} key
 * @param {(key: string) => string} t
 * @param {(key: string) => boolean} [te]
 */
function translateIfExists(key, t, te) {
  if (te) {
    if (!te(key)) return null
    return t(key)
  }
  const translated = t(key)
  if (!translated || translated === key) return null
  return translated
}

/** @param {unknown} error @param {(key: string) => string} t */
export function resolveEmailVerificationError(error, t) {
  if (error && typeof error === 'object' && error.code === 'EMAIL_NOT_VERIFIED') {
    return t('errors.emailNotVerified')
  }
  return null
}

/**
 * 将 API / job 错误解析为当前界面语言文案。未知 code 不展示中文 message。
 * @param {unknown} error
 * @param {(key: string) => string} t
 * @param {string} [fallbackKey]
 * @param {(key: string) => boolean} [te]
 */
export function resolveApiMessage(error, t, fallbackKey = 'common.failed', te) {
  if (!error || typeof error !== 'object') {
    return t(fallbackKey)
  }

  const code = typeof error.code === 'string' ? error.code : null
  if (code === 'EMAIL_NOT_VERIFIED') {
    return t('errors.emailNotVerified')
  }
  if (code) {
    const byCode = translateIfExists(`errors.codes.${code}`, t, te)
    if (byCode) return byCode
  }

  const fieldErr = extractFirstFieldError(error.errors)
  if (fieldErr?.field) {
    const byField = translateIfExists(`errors.fields.${fieldErr.field}`, t, te)
    if (byField) return byField
  }
  if (fieldErr?.message) {
    const mappedField = mapChineseMessage(fieldErr.message)
    if (mappedField) {
      const text = translateIfExists(mappedField, t, te)
      if (text) return text
    }
  }

  const message = typeof error.message === 'string' ? error.message : null
  const mapped = mapChineseMessage(message)
  if (mapped) {
    const text = translateIfExists(mapped, t, te)
    if (text) return text
  }

  return t(fallbackKey)
}
