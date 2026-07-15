# 详细报价交易链路：减少管理员介入 — 待办清单

> 创建日期：2026-07-15  
> 状态：**待评估，暂不实施**  
> 背景：详细报价履约升级后，供应商提交报价原需管理员在后台「对客户可见」开关开放，买家才能看到方案。已先行改为供应商提交后自动对买家可见；本文档记录其余可减少管理员介入的改项，供日后产品决策与排期。

---

## 已完成（2026-07-15）

| 项 | 说明 |
|----|------|
| 报价自动对买家可见 | 供应商提交/修订报价后，自动设置 `is_customer_visible=True`、分配 `Plan A/B/C…`、RFQ 状态推进至 `comparing`，并通知买家 |
| 实现位置 | `backend/apps/rfq/views.py` — `publish_supplier_quote_to_buyer()`、`SupplierQuoteRequestQuoteView` |

---

## 待评估改项

目标：**买卖双方尽量自助完成「询价 → 报价 → 选方案 → 付款 → 开工」**，管理员仅处理异常、风控与运营内容。

| 优先级 | 环节 | 现状 | 建议改法 | 涉及模块（预估） | 风险/备注 |
|--------|------|------|----------|------------------|-----------|
| **最高** | 付款确认 → 转项目 | 买家上传凭证后，须管理员在后台确认付款，才签署合同并创建项目 | 三选一或组合：<br>① 接入在线支付，回调自动确认<br>② 供应商确认到账后自动推进<br>③ 上传凭证后超时自动通过（小额） | `backend/apps/payment/views.py`、`contract/services.py`、`project/services.py` | 资金风险最高，需明确对账与争议流程 |
| **高** | 平台加价率 | 管理员在 RFQ 上手工设置 `markup_percent`（默认 0） | 全局默认加价 + 按工艺品类覆盖；确认方案时自动快照，不再逐单手工填 | `rfq/models.py`、配置表或 `ServiceCategory`、管理端 RFQ 页 | 需与财务口径对齐 |
| **高** | 内部 RFQ 找供应商 | `scope=internal` 不进需求大厅，依赖管理员创建 `QuoteRequest` 派单 | 默认 `scope=public`；或内部 RFQ 也支持按品类自动匹配/邀请供应商 | `rfq/views.py`（创建 RFQ、需求大厅）、`open_demand_hall_queryset` | 内部单是否应对全平台供应商可见需产品定 |
| **中** | 供应商账号 | 仅管理员创建供应商账号 | 企业自助入驻 + 自动/半自动审核（资料齐全即 `approved`） | `accounts/views.py`、`accounts/serializers.py`、入驻前端页 | 需防垃圾注册与资质造假 |
| **中** | 供应商入驻审核 | `FactoryProfile.status=approved` 后才可用供应商能力 | 注册即 `observing` 可报价；或规则引擎自动通过 | `accounts/models.py`、`core/permissions.py` | 与上条联动 |
| **中** | 需求大厅下架时机 | 首份报价后 RFQ → `comparing`，可能不再出现在大厅 | 若要多供应商竞价，大厅应保留至买家确认方案或截止日 | `OPEN_RFQ_STATUSES`、`publish_supplier_quote_to_buyer` 状态机 | 影响抢单 UX |
| **低** | 要求修订报价 | 仅管理员可将 `QuoteRequest` 标为 `needs_revision` | 买家可「请求改价」；或维持供应商在确认前自行修订（已实现） | `rfq/views.py`、买家/供应商前端 | 低优先级，供应商已可 PATCH 报价 |
| **低** | 方案标签 A/B/C | 原依赖管理员填写 | 已随自动开放按 `Plan A/B/C…` 分配 | 已实现 | — |
| **低** | 抢单通知管理员 | 供应商抢单后 `notify_staff` | 可改为仅站内运营看板，或大额/内部单才通知 | `SupplierDemandHallGrabView` | 不影响交易闭环 |
| **低** | 新 RFQ 通知管理员 | 会员提交 RFQ 后 `notify_staff` | 可改为自动进入需求大厅，无需「受理」 | `MemberRFQListCreateView` | 与 `scope` 默认公开联动 |

---

## 建议实施顺序（日后参考）

若目标是「最小改动、最大减员」，建议按以下批次推进：

### 批次 1 — 交易闭环（阻塞最大）

1. 付款确认自动化（选定一种到账确认机制）
2. 全局/品类默认加价率
3. RFQ 默认公开进需求大厅

### 批次 2 — 供给侧扩面

4. 供应商自助入驻 + 审核策略
5. 需求大厅多供应商竞价保留策略

### 批次 3 — 体验优化

6. 买家「请求改价」、弱化管理员修订流程
7. 精简 `notify_staff` 运营通知

---

## 管理员建议保留的职责

即使完成上述改项，仍建议保留管理员用于：

- 异常仲裁（拒单回退、合同作废）
- 黑名单 / 暂停供应商
- 大额订单风控抽查
- 内容运营（新闻、工艺分类、商城）
- 积分充值审核（若仍走线下转账）
- 询盘、商城订单等非 RFQ 主线业务

---

## 相关文档与代码

| 资源 | 路径 |
|------|------|
| 三端角色功能说明 | `MASS CONNECTED 三端角色功能说明.md` |
| 详细报价履约升级方案 | `.cursor/plans/详细报价履约升级_801b3ca9.plan.md` |
| 供应商报价提交 | `backend/apps/rfq/views.py` — `SupplierQuoteRequestQuoteView` |
| 买家方案展示 | `backend/apps/rfq/serializers.py` — `MemberRFQDetailSerializer.get_plans` |
| 付款确认 | `backend/apps/payment/views.py` — `AdminPaymentConfirmView` |
| 管理端报价开放（现可为备用） | `admin/src/views/RfqsView.vue` |

---

## 验收口径（实施时参考）

实施任一改项时，建议单独补充验收标准。整体目标验收可概括为：

1. 供应商提交报价后，买家无需管理员操作即可看到并对比方案。
2. 买家确认方案 → 付款 → 项目开工，中间无强制人工审核节点（除选定风控策略外）。
3. 价格展示、合同、付款、订单快照金额一致。
4. 权限与数据边界不退化（买家不见供应商底价与联系方式）。
