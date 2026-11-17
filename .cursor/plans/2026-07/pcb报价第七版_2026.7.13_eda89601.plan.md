---
name: PCB报价第七版
overview: 可以开发第七版，建议定位为“独立实采可信度、估算准确度与 FR-4/FPC 工艺开放版”。先修复 JLC 采样可靠性和样本泄漏，再用独立 holdout 驱动模型、风险分区与材料级开关；SMT 仍仅记录需求，不计算贴片费。
todos:
  - id: define-v7-data-splits
    content: 建立拟合、工艺 holdout 与最终验收互斥的数据协议和防泄漏检查
    status: completed
  - id: stabilize-jlc-sampling
    content: 重构 JLC 采样器并完成三次复采、选中态和页面指纹验证
    status: completed
  - id: sample-v7-process-matrix
    content: 补采 FR-4/FPC 分规模工艺矩阵和独立组合 holdout
    status: completed
  - id: fit-v7-models
    content: 拟合分段估算/工艺模型并自动标定风险分区与置信度
    status: completed
  - id: publish-v7-integration
    content: 发布 v7 数据，接入后端、前端四语、PDF与分区开关
    status: completed
  - id: verify-v7-release
    content: 完成独立大型实价验收、回归、部署检查和 v7 准确度报告
    status: completed
isProject: false
---

# PCB 制造费精确报价第七版

## 目标与范围
- 在 v6 `exact_lookup → verified_estimate → manual_review`、10% margin、三材料与回滚机制上迭代，不改变历史请求契约。
- 提高真实独立样本下的 Hit@10%、降低最大误差，并提高自动报价覆盖率。
- 对通过独立门禁的 FR-4/FPC 非标准工艺逐项或逐分区开放，不做材料整体无条件放行。
- 修复 v6 大型报告复用拟合/历史样本的问题；v7 发布验收必须使用全新且与拟合集无交集的 JLC 实价。
- `smt_required` 继续仅记录，`smt_price_included=false`；不开发 SMT 贴片费，不新增数据库迁移。

## 实现步骤
1. **建立 v7 独立数据协议与防泄漏门禁**
   - 在 [scripts/jlc-cn-pcb-golden-targets.mjs](scripts/jlc-cn-pcb-golden-targets.mjs) 生成拟合、工艺 holdout、最终验收三套互斥规格；最终验收每材料至少 40 条，主要为离 exact 网格规格。
   - 新增规格键交集校验；拟合/工艺样本与最终验收有任一交集即停止发布。
   - 废止 [scripts/jlc-cn-pcb-v6-large-material-assemble.mjs](scripts/jlc-cn-pcb-v6-large-material-assemble.mjs) 的历史样本拼装验收方式，保留旧报告但明确其仅供回归参考。

2. **提高 JLC 采样可靠性**
   - 重构 [scripts/jlc-cn-browser-sample.mjs](scripts/jlc-cn-browser-sample.mjs)：记录页面指纹、请求/DOM 双价格、最终选中态和失败分类；每规格隔离上下文并支持断点续采。
   - 仅接收三次有效复采、CV≤2%、选中态 100% 匹配的样本；DOM/API 不一致或 SPA 未完整加载时拒绝该样本，不使用旧样本填充。
   - 若自动化环境仍被 JLC 限制，提供浏览器会话接管/人工登录后的续采入口，但不降低数据门槛。

3. **扩充 FR-4/FPC 工艺矩阵**
   - 对 FR-4 的板厚、颜色、OSP/无铅喷锡/沉金、阻焊覆盖、拼板款数，以及 FPC 的 0.12/0.20mm 与拼板款数，按小/中/大面积和低/中/高数量采样。
   - 每材料至少 12 个独立工艺组合 holdout；铜厚仍只发布 JLC 页面能稳定验证的选项，无法稳定选择的 2oz 不开放。
   - 工艺按“材料＋层数＋面积/数量区间＋组合”分别门禁，允许只开放通过的局部组合。

4. **升级估算、工艺与风险模型**
   - 在 [scripts/jlc-cn-pcb-validate-samples.mjs](scripts/jlc-cn-pcb-validate-samples.mjs) 将全局 OFAT 常数调整升级为随面积/数量变化的分段或对数模型，并用独立 holdout 选择模型。
   - 将风险区从硬编码改为按当前 holdout 误差自动标定；异常分区继续返回 `manual_review`，不输出制造费。
   - 分别输出 exact、纯 estimator、工艺调整、风险分区和置信度校准指标，生成 `jlc-cn-pcb-v7-*` 产物。

5. **发布 v7 数据与接入**
   - 扩展 [scripts/jlc-cn-pcb-sync-table-data.mjs](scripts/jlc-cn-pcb-sync-table-data.mjs) 与 [backend/apps/simplequote/table_data.py](backend/apps/simplequote/table_data.py)，同步 v7 模型、独立性证明、页面指纹、材料/分区开关和验证指标；任何主门禁失败时保持 v6。
   - [backend/apps/simplequote/calculator.py](backend/apps/simplequote/calculator.py) 适配分段工艺系数和分区级放行；标准工艺、margin、汇率、SMT 标记保持不变。
   - 在 [frontend/src/views/quote/SimpleQuoteView.vue](frontend/src/views/quote/SimpleQuoteView.vue) 同步实际开放的 FR-4/FPC 选项和材料/层数联动；新增枚举在 [frontend/src/i18n/index.js](frontend/src/i18n/index.js) 补齐四语。PDF 仅在字段变化时更新 [backend/core/pdf.py](backend/core/pdf.py)。

6. **回归与独立大型验收**
   - 扩展 [backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py](backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py)：分段系数、FR-4/FPC 局部开放、风险边界、未通过分区降级、v6 回滚、SMT 不改价和历史请求兼容。
   - 使用全新独立 JLC DOM 样本做大型验收；报告明确样本时间、页面指纹、与拟合集交集为 0，并生成 `docs/pcb-quote-v7-accuracy-test-report.md`。
   - 完成 Django check、后端测试、前端 build、Compose 健康检查和浏览器核心路径验收。

## 风险与缓解
- JLC SPA/反自动化导致无法采满：保留失败证据并断点续采，不以历史样本冒充独立验收；必要时使用用户可见浏览器会话接管。
- 工艺组合爆炸：使用分层 OFAT、规模锚点和高价值交互，不做全交叉；按组合/分区独立启用。
- 模型在训练样本上过拟合：拟合、调参 holdout、最终验收三套数据严格隔离，最终验收只跑一次发布判定。
- FR-4/FPC 某些工艺仍不达标：只开放已通过分区，其余保持人工复核，不阻塞其他材料发布。

## 验收标准
- 最终验收样本与所有拟合/调参样本规格键交集为 0；每材料不少于 40 条新鲜有效 DOM 样本，exact_lookup 占比≤10%。
- 发布样本三次复采有效、CV≤2%、工艺选中态 100% 匹配，采样失败率≤5%。
- 纯估算：整体及每个启用材料 Hit@10%≥90%、Hit@20%≥95%、MAPE≤8%、最大误差≤20%。
- 工艺组合：每个开放材料/分区 Hit@20%≥90%、MAPE≤10%、最大误差≤20%；FR-4 与 FPC 各至少开放一个当前 v6 未开放的非标准工艺分区。
- 标准工艺价格与 v6 一致；历史请求、exact、margin、汇率、PDF 和 `smt_required` 无回归。
- 任一未达门禁的材料/组合自动降级为人工复核；v7 发布失败时继续使用 `jlc-cn-pcb-v6-20260712`。