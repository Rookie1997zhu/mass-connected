# JLC PCB 制造费报价标准（OEM.co 内部版）

## 1. v5 适用范围

- 自动报价材料：FR-4、FPC 软板、铝基板。
- FR-4：2/4 层；FPC：1/2 层；铝基板：1 层。
- 报价优先级为 `exact_lookup` → `verified_estimate` → `manual_review`。
- Estimator 仅在 50~200mm、5~200片、材料/层数已通过独立门禁时启用；不跨材料或跨层数套价。
- 铜基板、罗杰斯、铁氟龙、HDI 及其他材料继续人工复核。
- 在基准报价后支持已验证的板厚、阻焊颜色、表面处理（含 OSP/焊盘喷镀）、阻焊覆盖、拼板款数和 1oz 铜厚；金（锡）手指斜边与钢网明确排除。
- `smt_required` 仅记录贴片需求，不参与 PCB 制造费（`smt_price_included=false`）。
- 分规格风险门禁：高误差区间（如 FR-4 4层小尺寸低数量）自动降级人工复核。

机器可读价格和发布状态以以下文件为准：

- `backend/apps/simplequote/table_data.py`
- `scripts/jlc-cn-pcb-manufacturing-price-list.json`
- `scripts/jlc-cn-pcb-validation-report.json`

## 2. 固定采样口径

| 项目 | 口径 |
|---|---|
| 页面 | JLC 中文公开 PCB 下单页，未登录 |
| 权威价格 | DOM「预估支付总价(不含运费)」 |
| 交叉校验 | `calculateCustomerOrderMoney` API；不可用时不替代 DOM |
| 尺寸 | 业务及价格表使用 mm，页面输入 cm |
| FR-4 工艺 | 1.6mm、绿色、有铅喷锡 |
| FPC 工艺 | 页面默认 FPC 工艺 |
| 铝基板工艺 | 页面默认铝基板工艺 |
| 通用选项 | 工业/消费/其他类电子产品、不需要确认生产稿、默认测试项 |
| 排除项 | 运费、税费、优惠券、账号折扣、Gerber 审核附加费 |

## 3. 客户报价

```text
jlcBaseCny = exactLookup(...) or verifiedEstimate(...)
jlcEstimateCny = applyValidatedProcessAdjustments(jlcBaseCny)
customerQuoteCny = round(jlcEstimateCny * 1.10, 2)
customerQuoteKrw = round(customerQuoteCny * configuredCnyKrwRate)
```

只有同时满足以下条件才计入制造费：

1. `validation_status == "passed"`；
2. 材料位于 `enabled_materials`；
3. 精确价格行存在且启用，或该材料 estimator 已通过且规格在验证边界内；
4. 非标准工艺的材料、选项、层数及组合已通过工艺 holdout；
5. 用户开启 PCB 制造费。

否则制造费为 0，`requires_manual_review=true`，并返回稳定的人工复核原因。

## 4. 发布门禁

- Golden：每个唯一规格重复 3 次。
- 每条有效样本必须使用 DOM 价格，且材料、层数、尺寸、数量选中态一致。
- 同规格重复价格变异系数 `CV <= 2%`。
- Holdout 整体及 FR-4、FPC、铝基板分别满足：
  - `Hit@20% >= 80%`
  - `maxRelativeError <= 100%`
- Exact 门禁失败时不发布；Estimator 与工艺模型按材料独立启用，工艺失败材料继续使用标准档 v4 报价。

## 5. 人工复核边界

以下任一情况必须人工复核且不计制造费：

- 价格表未精确命中，且 estimator 未通过或规格超出支持边界；
- 验证状态不是 `passed`；
- 材料未启用或价格行被禁用；
- 材料/层数选项异常，或 DOM 价格读取失败；
- 非 1oz 铜厚、导热系数、介电常数、阻抗、特殊叠层或未验证的表面处理；
- 金（锡）手指斜边、钢网以及任何未验证工艺组合；
- Gerber 孔数、V-CUT、铣边、测试点、沉金面积等需文件审核；
- 加急、运费、税费、发票、优惠券或账号活动价。

## 6. 版本与维护

- v5 版本格式：`jlc-cn-pcb-v5-YYYYMMDD`；基准估算模型沿用 `jlc-cn-pcb-v4-estimator-YYYYMMDD`；工艺模型为 `jlc-cn-pcb-v5-process-YYYYMMDD`。
- 建议每 30 天复采，或在 JLC 页面/价格规则明显变化时立即复采。
- 采样顺序：工艺 smoke → 分材料 OFAT golden → 多工艺 holdout → validate → sync → seed。
- 只有验证报告 `status=passed` 时才允许执行 sync 和 seed。
