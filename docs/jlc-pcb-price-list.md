# PCB 制造费精确价格表

> 当前生效价格、行数、验证状态与版本以 `backend/apps/simplequote/table_data.py` 为准。完整机器表位于 `scripts/jlc-cn-pcb-manufacturing-price-list.json`，本文不复制全部行，避免文档与运行数据漂移。

当前发布目标：`jlc-cn-pcb-v6-YYYYMMDD`。v6 保留 222 行基准价格与 hybrid 估算，并扩展阻焊覆盖、拼板款数、OSP（焊盘喷镀）与分规格风险门禁；工艺自动报价按材料 holdout 独立启停。

## v6 材料矩阵

| 材料 | 层数 | 尺寸(mm) | 数量 | 自动报价条件 |
|---|---|---|---|---|
| FR-4 | 2、4 | 50×50、80×80、80×120、100×100、100×150、120×120、150×150、200×200 | 5、10、20、50、100、200 | 精确命中或通过估算门禁；非标准工艺当前人工复核 |
| FPC 软板 | 1、2 | 50×50、80×80、100×100、100×150、120×120、150×150、200×200 | 5、10、20、50、100、200 | 精确命中或通过估算门禁；非标准工艺当前人工复核 |
| 铝基板 | 1 | 50×50、80×80、100×100、100×150、120×120、150×150、200×200 | 5、10、20、50、100、200 | 精确命中/估算 + 已验证工艺调整 |

页面不支持、采样失败、CV 超标或 holdout 未通过的行不会启用。

## 价格公式

```text
客户 CNY = round(JLC DOM 采样价 × 1.10, 2)
客户 KRW = round(客户 CNY × 系统 CNY→KRW 汇率)
```

- JLC 采样价取公开下单页「预估支付总价(不含运费)」。
- 不含运费、税费、优惠券、账号折扣及 Gerber 审核附加费。
- 精确表未命中时，使用同材料、同层数的分阶段对数插值；不跨材料、跨层数外推。

## Hybrid 与工艺调整行为

```text
if validationPassed
   and materialEnabled
   and exactRowEnabled:
  add manufacturing fee
  pricing_mode = exact_lookup
  requiresManualReview = false
else if estimatorPassedForMaterial
   and specWithinValidatedBounds:
  add estimated manufacturing fee
  pricing_mode = verified_estimate
  requiresManualReview = false
else:
  manufacturing fee = 0
  requiresManualReview = true

if selectedProcess != materialDefaultProcess:
  require processModelPassedForMaterial
  require every selected option and layer combination validated
  apply validated process adjustments
  otherwise manual review with zero manufacturing fee
```

精确键为：

```text
material_key + layers + width_mm + height_mm + quantity
```

## v6 常用工艺

| 材料 | 板厚 | 阻焊颜色 | 表面处理/焊盘喷镀 | 阻焊覆盖 | 拼板款数 | 铜厚 |
|---|---|---|---|---|---|---|
| FR-4 | 1.0、1.2、1.6、2.0mm（按层数门禁） | 绿、红、黄、蓝、白、哑黑 | OSP、有铅喷锡、无铅喷锡、沉金 | 过孔盖油/开窗/塞油/树脂塞孔盖帽 | 1、2 | 1oz |
| FPC 软板 | 1层 0.11mm；2层 0.11、0.12、0.20mm | 页面默认 | 沉金 | 页面默认 | 1、2 | 1oz |
| 铝基板 | 1.0、1.2、1.6mm | 绿、红、黄、蓝、白、哑黑 | 无铅喷锡 | 过孔盖油 | 1、2 | 1oz |

通用选项为工业/消费/其他类电子产品、不需要确认生产稿、默认测试项。
JLC 当前公开页在本次验证范围内未提供可稳定选择的其他铜厚，因此铜厚字段保留为 1oz；不得据此外推 2oz。金（锡）手指斜边与钢网明确不纳入报价。`smt_required` 仅记录需求，不含贴片费。

## 人工复核

- 铜基板、罗杰斯、铁氟龙、HDI 及其他未启用材料；
- FR-4、FPC、铝基板中超出 50~200mm、5~200片或未通过 estimator 门禁的规格；
- 未通过验证、过期、禁用或无法读取 DOM 价格的规格；
- 非 1oz 铜厚、导热系数、介电常数、阻抗、特殊叠层或未列出的表面处理；
- FR-4 / FPC 非标准工艺组合（当前工艺 holdout 未整体通过）；
- 命中风险分区的规格（如 FR-4 4层小尺寸低数量）；
- 任何依赖 Gerber 文件审核的附加工艺。
