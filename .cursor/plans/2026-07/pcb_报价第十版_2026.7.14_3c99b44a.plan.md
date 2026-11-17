---
name: PCB 报价第十版
overview: 以 v9 最终验收仅作诊断，重点重建 FPC 分层/面积/数量模型并补齐自动报价覆盖率门禁；FR-4 与铝基沿用已验证方向做防回归，全新 v10 验收全部通过后才原子发布。
todos:
  - id: v10-diagnostics
    content: 固化 v9 分段误差、自动报价覆盖率与评分管线诊断
    status: completed
  - id: v10-data-protocol
    content: 建立 v10 互斥 split、运行时可运行预检、新指纹与一次性门禁
    status: completed
  - id: v10-fpc-model
    content: 实现 FPC 分层地板价/面积/数量模型及前后端镜像护栏
    status: completed
  - id: v10-sampling
    content: 完成 v10 FPC fit/tuning、三材料回归和全新三采验收数据
    status: completed
  - id: v10-release
    content: 执行含覆盖率的独立验收并在全门禁通过后原子发布
    status: completed
  - id: v10-regression
    content: 完成后端、前端、PDF、Compose 与失败回退回归验证
    status: completed
isProject: false
---

# PCB 制造费精确报价第十版

## 目标与范围
- 保持活动版本 `jlc-cn-pcb-v6-20260712`；v10 未通过前不改变线上自动报价。
- v9 验收集 `fnvish_6d9edbea` 只作 diagnostic，禁止进入 v10 fit、tuning 或发布判定。
- 重点修复 FPC：v9 自动报价样本 Hit@20 仅 87.5%、MAPE 11.05%、最大误差 23.88%，且 42 个稳定规格中仅 24 个被自动报价。
- FR-4、铝基保留 v9 已验证模型方向，但补齐运行时覆盖率验证；不改数据库结构和对外 API 契约。

## 实现步骤
1. **固化 v9 诊断并修正评分前置条件**
   - 扩展 [scripts/jlc-cn-pcb-v9-acceptance-score.py](scripts/jlc-cn-pcb-v9-acceptance-score.py) 的诊断输出，按材料统计自动报价覆盖率、人工复核原因、层数/面积/数量分段误差。
   - 将 FPC 高误差点（如 `FPC-017/028/029`）和 53 个低覆盖人工复核点归档为 v10 diagnostic，不作为训练数据。
   - 在消费验收指纹前增加候选表字段规范化、三材料最小可运行样本和模型哈希预检；评分管线无有效报价时不得消费指纹。

2. **建立 v10 数据协议与运行时一致的支持门禁**
   - 新增 v10 spec-key、split 生成、split 断言、模型冻结和 acceptance score 脚本，显式拒绝 `V7-ACC`、`V8-ACC`、`V9-ACC` 及 diagnostic 数据。
   - v9 fit 可作为历史拟合锚点；v9 tuning 仅用于回归诊断，不转入 v10 fit。新增 FPC 边界 fit 与独立 tuning，覆盖 1/2 层、小/中/大面积及 5–200 数量阶梯。
   - split 断言除 exact/process/近邻隔离外，必须用 [backend/apps/simplequote/calculator.py](backend/apps/simplequote/calculator.py) 的镜像算法预演所有 final targets：尺寸轴范围、距离阈值、邻居数和材料开关均须可运行，避免“支持包络通过但运行时人工复核”。
   - 生成每材料至少 48 个全新 final targets、每规格三采、CV ≤2%，冻结新指纹并保持一次性有效判定。

3. **重建 FPC 模型并保持前后端算法镜像**
   - 在 [scripts/jlc-cn-pcb-v9-model.mjs](scripts/jlc-cn-pcb-v9-model.mjs)、[scripts/jlc-cn-pcb-v9-build-model.mjs](scripts/jlc-cn-pcb-v9-build-model.mjs) 的 v10 对应实现中，将 FPC 按层数拆分，采用起订地板价、面积增长和数量阶梯的分段模型；加入单调性、倍率上限和局部残差护栏。
   - tuning 只比较预先声明的候选参数；模型选择后立即冻结，final acceptance 开始后禁止重建或调参。
   - 在 [backend/apps/simplequote/calculator.py](backend/apps/simplequote/calculator.py) 实现完全镜像的 FPC v10 算法；FR-4/铝基保留 v9 公式并按 v10 新 holdout 校准覆盖护栏。
   - 低覆盖、外推、异常倍率、未通过材料仍统一进入人工复核。

4. **稳定采样并完成 v10 fit/tuning/final 数据**
   - 复用 [scripts/jlc-cn-browser-sample.mjs](scripts/jlc-cn-browser-sample.mjs) 的持久化上下文、DOM/API 双校验、特价 quarantine、断点续采和坏规格组快速跳过。
   - 先采 v10 FPC fit/tuning 及三材料回归 holdout；模型、风险区和运行时覆盖预检全部冻结后，再采至少 432 行 final acceptance。
   - 每个阶段输出稳定规格数、quarantine、失败分类和重采结果，临时浏览器配置与批次文件在收尾时清理。

5. **独立验收与原子发布**
   - 保留原门禁：每材料有效稳定规格 ≥40；总体 Hit@10 ≥90%、Hit@20 ≥95%、MAPE ≤8%、最大误差 ≤20%；每材料 Hit@20 ≥95%、最大误差 ≤20%。
   - 新增覆盖门禁：总体及每材料自动报价覆盖率 ≥90%，且所有 final targets 在冻结前通过运行时可运行预检。
   - [scripts/jlc-cn-pcb-sync-table-data.mjs](scripts/jlc-cn-pcb-sync-table-data.mjs) 仅接受通过、已完成有效一次性判定且尚未发布的 v10 报告；使用临时文件原子替换并在成功后标记 published。
   - 任一材料或覆盖门禁失败则保持 v6，失败指纹不得再次用于调参或发布。

6. **回归与发布前验证**
   - 扩展 [backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py](backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py)：FPC 分层模型、单调性、覆盖边界、异常倍率、材料级开关、失败回退、版本字段及原子发布门禁。
   - 验证现有 [frontend/src/views/quote/SimpleQuoteView.vue](frontend/src/views/quote/SimpleQuoteView.vue) 与 [backend/core/pdf.py](backend/core/pdf.py) 能正确显示 v10 版本、验收状态和回退提示；仅在字段新增时补 i18n。
   - 执行 split/assert、模型镜像对拍、评分脚本语法、后端测试、前端 build、Django check、Compose 状态和 HTTP 冒烟。

## 风险与缓解
- FPC tuning 样本过少导致再次过拟合：扩大层数/面积/数量组合，要求分材料覆盖率和最大误差同时通过。
- 支持包络与运行时实现不一致：冻结前直接调用镜像估算器预演 final targets，而非仅用几何距离判断。
- final acceptance 反向影响模型：模型哈希先冻结，验收指纹一次性消费；失败后只能进入下一版本。
- JLC SPA、促销价和工艺状态污染：DOM/API/规格三方一致、特价 quarantine、稳定三采及分批重试。
- 自动报价覆盖率过低掩盖误差：新增总体和分材料 ≥90% 的硬门，人工复核样本不再从覆盖考核中消失。

## 验收标准
1. v9 final acceptance 全部标记 diagnostic，泄漏到 v10 fit/tuning/final 任一集合即硬失败。
2. FPC 新模型在独立 tuning 上 Hit@20 ≥95%、最大误差 ≤20%，且覆盖率 ≥90%；FR-4、铝基无回归。
3. v10 final acceptance 每材料至少 40 个稳定规格，三采完整且 CV ≤2%。
4. 总体及分材料误差门禁全部通过；总体和每材料自动报价覆盖率均 ≥90%。
5. 模型哈希、final 指纹和评分管线预检均通过；有效发布判定后同一指纹不可重跑。
6. 通过前同步脚本拒绝发布并保持 v6；全部通过后一次原子切换并保留 v6 回滚版本。
7. 后端测试、前端 build、Django/Compose 健康检查及 HTTP 冒烟无阻塞错误。