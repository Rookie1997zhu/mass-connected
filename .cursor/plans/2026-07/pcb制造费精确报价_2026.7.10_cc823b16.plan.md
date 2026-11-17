---
name: PCB制造费精确报价
overview: 把 PCB 样板制造费作为现有“PCB 开发”报价的可选子项；第一版只对复采后精确命中的 FR-4 与 FPC 自动报价，其余材料和规格统一人工复核。通过独立时段验证集计算 Hit@20%，达到 80% 后才启用对应价格表。
todos:
  - id: resample-golden-dataset
    content: 扩展采样脚本并完成 FR-4/FPC 三重复黄金矩阵采样
    status: completed
  - id: validate-hit-rate
    content: 实现数据质量门禁并用独立时段30条验证集验收 Hit@20%
    status: completed
  - id: normalize-pricing-docs
    content: 统一三份报价文档并生成仅含有效精确价格的机器表
    status: completed
  - id: integrate-pcb-calculator
    content: 将精确制造费子计算器接入现有 PCB 开发后端、汇率与 PDF
    status: completed
  - id: add-pcb-manufacturing-ui
    content: 增加 PCB 制造费可选表单、结果提示和四语文案
    status: completed
  - id: run-regression-checks
    content: 完成计算、seed、PDF、前端构建和现有 PCB 开发回归验证
    status: completed
isProject: false
---

# PCB 制造费精确报价与复采计划

## 目标与范围

- 在现有 `quote_type="pcb"` 中增加可选“PCB 样板制造费”，保留原 PCB 开发费、服务费和配送费逻辑。
- 自动报价仅覆盖：FR-4 2/4 层精确表格、FPC 2 层精确表格；铝基板及其他材料、非表内规格、特殊工艺统一 `requiresManualReview=true`。
- 客户报价仍为 `JLC有效采样价 × 1.10`，再按已有汇率换算成 KRW 并入 PCB 开发总价。
- 第一版禁用现有乘法系数外推；不承诺 Gerber 审核后的最终成交价。

## 实现步骤

1. **建立可复现的黄金价格表**
   - 扩展 [scripts/jlc-cn-browser-sample.mjs](scripts/jlc-cn-browser-sample.mjs) 的采样模式与目标：
     - FR-4：2/4 层 × `50×50、80×80、80×120、100×100、100×150、120×120、150×150mm` × `5、10、20、50、100pcs`，共 70 格。
     - FPC：2 层 × `50×50、100×100、100×150mm` × `5、10、20pcs`，共 9 格。
     - 每格独立浏览器上下文重复 3 次，以有效样本中位数作为候选价格。
   - 新增 targets、原始结果和验证报告 JSON；采样数据保留时间、DOM 总价、API 总价、特价标记、固定工艺参数和失败原因。

2. **增加数据质量门禁与 80% 验证**
   - DOM“预估支付总价”作为候选权威值，API 总价仅作交叉校验；两者差异超过 1% 时重试，仍不一致则剔除。
   - 检测层数/数量误触、重复样本离散、特价 `specialProduceMoney`、价格倒挂和跨来源同规格冲突；异常样本不得进入自动报价表。
   - 黄金表生成后，在独立时段重新抽取 30 个受支持格点（FR-4 20、FPC 10），不参与定价，输出：
     - `Hit@20% = 相对误差≤20%的样本比例`
     - MAPE、最大误差、按材料分组结果
   - 仅当整体及 FR-4/FPC 各自 `Hit@20% ≥ 80%`、无单点误差超过 100% 时启用；否则对应材料继续人工复核。

3. **统一报价标准和机器数据源**
   - 更新 [docs/jlc-pcb-pricing-sampling.md](docs/jlc-pcb-pricing-sampling.md)、[docs/jlc-pcb-price-list.md](docs/jlc-pcb-price-list.md)、[docs/jlc-pcb-quote-standard.md](docs/jlc-pcb-quote-standard.md)：删除客户可见的系数外推路径，明确铝基板退出自动报价，并记录价格版本、采样时间和有效期。
   - 在 [backend/apps/simplequote/table_data.py](backend/apps/simplequote/table_data.py) 增加 `manufacturing_price_list` 精确价格表及 `pcb_manufacturing_margin_rate=0.10`；复用 `QuoteTable`/`QuoteParam`，无需数据库迁移。

4. **接入 PCB 开发后端计算**
   - 在 [backend/apps/simplequote/calculator.py](backend/apps/simplequote/calculator.py) 为 `calc_pcb()` 增加独立的样板制造费子计算器：
     - 输入开关、材料、层数、长宽、数量和基础工艺。
     - FR-4/FPC 只做规范化后的精确键匹配，不做最近邻或系数外推。
     - 命中后计算 CNY 客户价，复用 `cny_to_krw` 换算后加入现有 KRW `breakdown`/总价。
     - 未命中时不把参考价加入总额，返回人工复核原因、价格表版本和有效期。
   - 在 [backend/apps/simplequote/views.py](backend/apps/simplequote/views.py) 合并制造费参数和汇率；保持历史报价 `inputs/result` JSON 快照不重算。
   - 在 [backend/core/pdf.py](backend/core/pdf.py) 的 PCB 开发 PDF 中增加制造费明细、数据来源和人工复核提示。

5. **接入前端表单和结果展示**
   - 在 [frontend/src/views/quote/SimpleQuoteView.vue](frontend/src/views/quote/SimpleQuoteView.vue) 的 PCB 开发区增加可选“含 PCB 样板制造费”及材料、层数、尺寸、数量字段；材料仅提供 FR-4/FPC 自动范围，其他材料选择后明确显示待人工确认。
   - 在结果区展示制造费、计价方式、价格有效期和人工复核原因。
   - 在 [frontend/src/i18n/index.js](frontend/src/i18n/index.js) 补齐四语文案；通用 API 和现有历史列表结构继续复用。

6. **测试与上线门禁**
   - 新增后端测试覆盖：开关关闭时原 PCB 开发金额完全不变；FR-4/FPC 精确命中；材料/尺寸/数量不命中；CNY→KRW；10% margin；异常价格表；人工复核不计入总额；seed 幂等；PDF 冒烟。
   - 运行前端 lint/build、后端测试和简单报价回归；核对历史 `quote_type="pcb"` 仍可正常查看。
   - 先导入通过验证的黄金表，再启用前端开关；价格表过期或验证不达标时自动降级为人工复核。

## 风险与缓解

- **JLC 活动价漂移**：记录特价标记、采样时间和有效期；定期抽样验证，过期即停用自动报价。
- **API/DOM 状态污染**：每个样本新 context，差异超过 1% 自动重试/剔除，禁止人工静默改价。
- **币种混合**：制造价保留 CNY 原值，同时按统一 `cny_to_krw` 换算后才并入现有 KRW 总价。
- **Gerber 附加费缺失**：界面和 PDF 明示不含，并对孔数、V-CUT、阻抗、沉金面积等强制人工复核。
- **旧 PCB 开发逻辑回归**：制造费默认关闭，并以“关闭开关金额完全一致”作为阻塞性测试。

## 验收标准

1. FR-4/FPC 只有精确命中已启用、未过期价格表时产生自动制造费。
2. 铝基板、其他材料、非表内规格和特殊工艺均不产生自动金额，并返回稳定的人工复核原因。
3. 独立时段 30 条验证集上，整体及分材料 Hit@20% 均不低于 80%。
4. 报价结果同时保存 JLC CNY 原价、10% margin、KRW 换算价、价格版本和有效期。
5. 关闭制造费开关时，现有 PCB 开发报价、PDF和历史记录行为不变。
6. 前端四语文案、后端测试、前端 lint/build、PDF冒烟全部通过。