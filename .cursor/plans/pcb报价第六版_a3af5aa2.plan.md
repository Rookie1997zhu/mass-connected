---
name: PCB报价第六版
overview: 在第五版三材料 hybrid 报价与工艺模型上，扩展铜厚、焊盘喷镀/表面处理、阻焊颜色、阻焊覆盖和拼板款数；SMT 仅作为需求标记，不影响 PCB 制造费。第六版同时引入分规格风险门禁，优先消除第五版最大 31.29% 的估算误差，并保持 v5 可回滚。
todos:
  - id: freeze-v6-jlc-options
    content: 按材料和层数冻结铜厚、颜色、阻焊覆盖、焊盘喷镀及拼板款数边界
    status: completed
  - id: sample-v6-process-matrix
    content: 完成单工艺、关键两两交互和独立组合 holdout 的三次 DOM 采样
    status: completed
  - id: fit-v6-risk-model
    content: 拟合新增工艺与交互修正，并建立分规格风险门禁和校准置信度
    status: completed
  - id: publish-v6-data
    content: 同步 v6 枚举、模型、风险分区和开关，失败时保留 v5
    status: completed
  - id: integrate-v6-quote
    content: 接入后端、四语前端和 PDF，加入仅记录的 SMT 需求标记
    status: completed
  - id: verify-v6-release
    content: 完成回归、部署、120规格 JLC 对比和 v6 准确度报告
    status: completed
isProject: false
---

# PCB 制造费精确报价第六版

## 目标与范围
- 保留 v5 的 `exact_lookup → verified_estimate → manual_review`、10% margin、汇率换算、三材料支持和历史请求兼容。
- 扩展价格相关字段：铜厚、阻焊颜色、阻焊覆盖、焊盘喷镀/表面处理、拼板款数；继续保留板厚。
- “表面处理”与 JLC“焊盘喷镀”合并为现有 `surface_finish`，避免重复加价。
- 新增 `smt_required` 仅记录需求并展示在结果/PDF，不参与 PCB 制造费，也不尝试计算贴片费。
- 继续排除金（锡）手指斜边和是否开钢网；不新增字段、不采样、不计价。
- 不做数据库迁移，继续使用 QuoteTable JSON 数据结构。

## 实现步骤
1. **冻结 JLC 动态工艺边界**
   - 扩展 [scripts/jlc-cn-pcb-golden-targets.mjs](scripts/jlc-cn-pcb-golden-targets.mjs) 和 [scripts/jlc-cn-browser-sample.mjs](scripts/jlc-cn-browser-sample.mjs)，按材料、层数、尺寸和数量读取并验证最终选中态。
   - 从 JLC 页面冻结材料级选项：铜厚；OSP/有铅喷锡/无铅喷锡/沉金；常规与页面稳定的扩展阻焊颜色；过孔盖油/开窗/塞油/树脂塞孔电镀盖帽；拼板款数的有效范围。
   - 页面禁用、依赖 Gerber 才能确认或不稳定的选项不发布；铜浆塞孔等仅在真实可选且验证通过时纳入。

2. **构建分层采样矩阵**
   - 保留 222 个 v5 标准基准规格，新增 OFAT 单工艺锚点、价格敏感的两两交互样本和未参与拟合的组合 holdout。
   - 重点覆盖 `铜厚×层数`、`铜厚×焊盘喷镀`、`阻焊覆盖×焊盘喷镀`、`拼板款数×数量/面积`、`颜色×材料`。
   - 所有发布样本执行三次 DOM 复采、`JLC_CONTEXT_SCOPE=spec` 隔离；CV>2%、选中态错配、活动异常价或非 DOM 价格全部拒绝。

3. **升级估算与工艺模型**
   - 扩展 [scripts/jlc-cn-pcb-validate-samples.mjs](scripts/jlc-cn-pcb-validate-samples.mjs)，在 v5 基准估算后拟合新增工艺增量与有限交互修正。
   - 针对第五版 FR-4 4层小尺寸、FPC 非标准板厚等高误差区域增加局部校准；置信度由独立 holdout 实际误差校准，不再只依赖几何距离。
   - 门禁细化到“材料＋层数＋尺寸/数量区间＋工艺组合”；高风险分区单独人工复核，不因材料整体通过而放行异常区间。

4. **发布 v6 数据并可回滚**
   - 扩展 [scripts/jlc-cn-pcb-sync-table-data.mjs](scripts/jlc-cn-pcb-sync-table-data.mjs) 与 [backend/apps/simplequote/table_data.py](backend/apps/simplequote/table_data.py)，同步选项枚举、默认值、系数、交互修正、风险分区、验证指标和独立开关。
   - 使用 `jlc-cn-pcb-v6-YYYYMMDD`；v6 任一门禁失败时保留当前 v5 数据，不覆盖已生效版本。

5. **接入后端、前端与 PDF**
   - 在 [backend/apps/simplequote/calculator.py](backend/apps/simplequote/calculator.py) 增加 `solder_mask_coverage`、`panel_design_count`、`smt_required`，并扩展现有 `copper_thickness`、`solder_color`、`surface_finish` 枚举与组合校验。
   - 计价顺序为基准 exact/estimate → 已验证单工艺调整 → 已验证交互修正 → 风险门禁；未验证组合制造费为 0 并人工复核。
   - 在 [frontend/src/views/quote/SimpleQuoteView.vue](frontend/src/views/quote/SimpleQuoteView.vue) 增加材料/层数联动控件，在 [frontend/src/i18n/index.js](frontend/src/i18n/index.js) 补齐四语；SMT 明确标注“仅记录需求，不含贴片费”。
   - 在 [backend/core/pdf.py](backend/core/pdf.py) 输出新增工艺、调整明细、风险状态、模型版本和 SMT 需求标记。

6. **回归与大型实价验收**
   - 扩展 [backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py](backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py)，覆盖单工艺、交互组合、材料/层数依赖、非法值、风险分区、SMT 不影响价格、历史请求和 v5 回滚。
   - 至少使用 120 个不参与拟合的独立规格对比同轮 JLC 最终 DOM，分别报告 exact、纯 estimator、estimator＋工艺、客户价含 margin 的指标。
   - 执行 Django check、后端测试、前端 build、Compose 更新、健康检查和浏览器验收，生成 [docs/pcb-quote-v6-accuracy-test-report.md](docs/pcb-quote-v6-accuracy-test-report.md)。

## 风险与缓解
- JLC 选项随材料、层数或尺寸动态变化：每规格隔离浏览器上下文，并校验最终选中态。
- 工艺组合数量膨胀：使用 OFAT＋价格敏感两两交互＋独立 holdout，不做全交叉。
- 拼板款数可能依赖 Gerber 结构：只发布页面能够稳定确认的范围，其余人工复核。
- SMT 标记被误解为已报价：前端、API 结果和 PDF 明确 `smt_price_included=false`。
- 模型整体指标掩盖局部大误差：使用分区门禁和经 holdout 校准的置信度，高风险区直接降级。

## 验收标准
- 所有新增自动报价选项均来自 JLC 最终 DOM，三次复采有效且 CV≤2%，工艺选中态 100% 匹配。
- 独立大型 holdout 整体及每个启用材料误差≤20%占比≥90%、平均相对误差≤10%；每个自动报价风险分区最大误差≤20%，否则仅关闭该分区。
- 纯估算与工艺组合分别统计；目标为纯估算误差≤10%占比≥90%，工艺组合误差≤10%占比≥80%。
- 标准工艺价格与 v5 完全一致；现有 exact、margin、汇率和历史报价无回归。
- `smt_required` 开关不改变 PCB 制造费，并明确不包含贴片费；金手指斜边和钢网继续不存在。
- 后端测试、Django check、前端构建、Docker 健康检查及浏览器 JLC 对比通过，并产出 v6 Markdown 准确度报告。