/** 站内通知标题多为中文入库；展示时按原文映射到 i18n。 */

const EXACT_TITLE_KEYS: Record<string, string> = {
  新的聊天消息: 'notifications.titles.newChatMessage',
  项目进度更新: 'notifications.titles.projectProgressUpdated',
  项目异常反馈: 'notifications.titles.projectIssueReported',
  有新的待办事项: 'notifications.titles.newTodo',
  已转为详细报价: 'notifications.titles.convertedToDetailedQuote',
  积分变动: 'notifications.titles.pointsChanged',
  积分充值已到账: 'notifications.titles.pointsRecharged',
  项目已启动: 'notifications.titles.projectStarted',
  新项目已分配: 'notifications.titles.projectAssigned',
  付款已确认: 'notifications.titles.paymentConfirmed',
  客户付款已确认: 'notifications.titles.customerPaymentConfirmed',
  报价方案已就绪: 'notifications.titles.quoteReady',
  供应商已拒单: 'notifications.titles.supplierRejectedOrder',
  报价未被采用: 'notifications.titles.quoteNotSelected',
  新的生产订单待确认: 'notifications.titles.productionOrderPending',
  报价已被采用: 'notifications.titles.quoteSelected',
  合同已生成: 'notifications.titles.contractCreated',
  报价需修订: 'notifications.titles.quoteNeedsRevision',
  报价请求已取消: 'notifications.titles.quoteRequestCancelled',
  订单提醒: 'notifications.titles.orderReminder',
}

type TranslateFn = (key: string, values?: Record<string, unknown>) => string
type TeFn = (key: string) => boolean

export function localizeNotificationTitle(
  title: string | null | undefined,
  t: TranslateFn,
  te?: TeFn,
): string {
  const raw = (title || '').trim()
  if (!raw) return t('notifications.fallback')

  const exactKey = EXACT_TITLE_KEYS[raw]
  if (exactKey && (!te || te(exactKey))) {
    return t(exactKey)
  }

  if (raw.startsWith('订单提醒：') || raw.startsWith('订单提醒:')) {
    const orderNo = raw.replace(/^订单提醒[：:]/, '').trim()
    const key = 'notifications.titles.orderReminderWithNo'
    if (!te || te(key)) {
      return t(key, { orderNo: orderNo || '-' })
    }
  }

  return raw
}
