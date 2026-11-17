---
name: PCB报价第四版
overview: 第四版仅以 JLC PCB 制造报价为基准，在 FR-4、FPC、铝基板上扩大常用精确价格矩阵，并增加“精确查表优先、JLC 页面支持范围内参数估算兜底”的 hybrid 模式。估算模型以广覆盖 JLC DOM holdout 验证，整体及分材料 Hit@20% 达到 80% 才发布，失败材料继续沿用 v3 精确查表与人工复核。
todos:
  - id: freeze-v4-matrix
    content: 完成三材料 v4 smoke，冻结 JLC 页面支持边界和 200×200mm/200片常用精确矩阵
    status: completed
  - id: build-v4-estimator
    content: 生成分材料/层数 hybrid estimator，并建立真实档间与边界 holdout
    status: completed
  - id: validate-v4-gates
    content: 扩展 exact/estimator 分材料验证门禁，达到 Hit@20% 80% 发布标准
    status: completed
  - id: publish-v4-data
    content: 同步 v4 精确表、模型、支持边界与分材料开关并 seed
    status: completed
  - id: integrate-v4-quote
    content: 接入精确优先估算兜底，贯通 API、前端四语与 PDF 可追溯字段
    status: completed
  - id: verify-v4-release
    content: 完成回归、部署、浏览器 JLC 对比并输出 v4 Markdown 准确度报告
    status: completed
isProject: false
---

# PCB 制造费精确报价第四版

## 目标与范围
- 做：保留 v3 三种材料与精确查表；将常用精确矩阵扩到 JLC 实际支持的 200×200mm、200片以内；对精确表未命中但仍处于 JLC 页面支持范围的规格提供参数估算；同步采样、验证、后端、前端、PDF、文档与浏览器验收。
- 报价优先级：`exact_lookup` → `verified_estimate` → `manual_review`；继续使用 JLC 原价 + 10% margin + CNY→KRW。
- 不做：不使用 [project/new/03-PCB开发成本.md](project/new/03-PCB开发成本.md) 作为制造费依据；不修改 PCB 开发费权重；不新增材料或复杂工艺维度；不做数据库迁移。

## 实现步骤
1. **冻结 v4 页面支持范围与扩展矩阵**
   - 扩展 [scripts/jlc-cn-pcb-golden-targets.mjs](scripts/jlc-cn-pcb-golden-targets.mjs)，先用 smoke 确认 FR-4、FPC、铝基板在 JLC 页面实际支持的层数、尺寸与数量边界。
   - 在现有矩阵中补齐档间点，并增加 200×200mm、200片以内的常用精确点；页面不支持的组合直接移除。
   - 分离 `exact-golden/exact-holdout` 与 `estimator-holdout`：后者覆盖档间尺寸、非标准长宽比、数量跳变点及页面边界，避免 v3 holdout 仅回放精确点。

2. **生成并验证 hybrid 估算模型**
   - 新增版本化 estimator 生成脚本，使用有效 JLC DOM 样本按材料和层数拟合面积、长宽比、数量阶梯等特征；禁止使用 bootstrap/legacy、异常活动价或选中态不一致样本。
   - 扩展 [scripts/jlc-cn-pcb-validate-samples.mjs](scripts/jlc-cn-pcb-validate-samples.mjs)：精确行继续要求三次重复全有效且 CV≤2%；估算 holdout 独立统计整体及 FR-4/FPC/铝基板的 Hit@20%、MAPE、最大相对误差。
   - 发布门禁：估算整体及每种材料 `Hit@20%≥80%`、最大相对误差≤100%；某材料失败时只关闭该材料 estimator，保留其 v3/v4 精确查表，禁止失败影响其他材料。

3. **发布 v4 价格表、模型与支持边界**
   - 扩展 [scripts/jlc-cn-pcb-sync-table-data.mjs](scripts/jlc-cn-pcb-sync-table-data.mjs)，同步 v4 精确行、模型参数、JLC 页面支持边界、分材料 estimator 开关和验证指标，版本输出 `jlc-cn-pcb-v4-YYYYMMDD`。
   - 更新 [backend/apps/simplequote/table_data.py](backend/apps/simplequote/table_data.py) 与现有 `QuoteTable` seed；保持数据结构向后兼容，不新增模型字段或迁移。
   - sync 前强制检查 exact 门禁及 estimator 分材料状态；失败时不覆盖当前 v3 生效数据。

4. **后端接入精确优先的估算兜底**
   - 在 [backend/apps/simplequote/calculator.py](backend/apps/simplequote/calculator.py) 保持 `_find_pcb_manufacturing_row()` 最高优先级；未命中时仅对已启用材料、JLC 页面支持层数/尺寸/数量范围调用 estimator。
   - 结果新增兼容字段：`pricing_mode`、`is_estimated`、`confidence`、`estimator_version`、`validation_metrics`；现有金额、版本、人工复核字段保持不变。
   - 页面不支持、材料 estimator 未通过、输入异常或模型缺失时继续不计制造费并返回人工复核；10% margin 与 KRW 换算逻辑不变。

5. **前端、PDF、测试与文档**
   - 更新 [frontend/src/views/quote/SimpleQuoteView.vue](frontend/src/views/quote/SimpleQuoteView.vue) 和 [frontend/src/i18n/index.js](frontend/src/i18n/index.js)，明确展示“精确价/估算价”、估算置信度及误差提示，四语言补齐且不改变现有提交字段。
   - 更新 [backend/core/pdf.py](backend/core/pdf.py)，在报价 PDF 中记录计价方式、模型版本和估算提示；历史报价缺少新字段时按精确价兼容显示。
   - 扩展 [backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py](backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py)：覆盖三材料精确优先、估算命中、页面范围边界、分材料 estimator 关闭、验证失败、历史结果、关闭开关与金额换算。
   - 更新 JLC 三份报价文档及 [docs/pcb-quote-v3-accuracy-test-report.md](docs/pcb-quote-v3-accuracy-test-report.md) 的 v4 验收章节。

6. **复采、部署与浏览器准确度报告**
   - 执行 smoke → exact golden/holdout → estimator holdout → validate → sync → seed；随后运行 Django check/测试、前端 build，并重启 backend/frontend/caddy。
   - 浏览器至少抽查 6 个精确规格、每种材料 5 个估算规格及 3 个范围外规格；逐项比较本站 `jlc_estimate_cny` 与同次 JLC DOM 最终价。
   - 输出 v4 Markdown 测试报告，分别统计 exact 与 estimator 的 Hit@20%、MAPE、最大误差，并记录人工复核边界和非阻塞告警。

## 风险与缓解
- JLC 数量阶梯和活动价非线性：扩大数量跳变点 holdout，剔除活动价异常，模型按材料/层数分组。
- “页面支持即可估算”会包含稀疏区域：使用覆盖全支持范围的代表性 holdout；只在整体及分材料 80% 门禁通过后启用，并向用户明确标记估算价。
- 估算失败污染 v3：分材料开关、版本化产物和 sync 前门禁保证可单独关闭 estimator 或整体回退 v3。
- 历史报价兼容：只新增可选结果字段，前端/PDF 对缺失字段使用 v3 默认值。

## 验收标准
1. v4 精确矩阵覆盖三种现有材料的常用 200×200mm、200片以内且所有发布行来自有效 JLC DOM 三次复采，CV≤2%。
2. estimator holdout 整体及 FR-4/FPC/铝基板分别 Hit@20%≥80%，最大相对误差≤100%；失败材料不得启用估算自动计费。
3. 精确命中始终返回 `exact_lookup`；未命中但在 JLC 支持范围且材料 estimator 通过时返回 `verified_estimate`；范围外或验证失败时人工复核且制造费为 0。
4. API、保存结果和 PDF 能追溯价格版本、模型版本、计价方式与验证指标，历史 v3 报价可正常打开。
5. 10% margin、CNY→KRW、关闭制造费开关和现有 FR-4/FPC/铝基板精确报价无回归。
6. 后端测试、前端 build、Docker 健康检查通过，并生成逐项 JLC DOM 对比的 v4 Markdown 测试报告。