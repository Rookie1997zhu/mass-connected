---
name: PCB报价第五版
overview: 在 v4 的三材料 hybrid 报价基础上，新增板厚、阻焊颜色、表面处理、铜厚四个常用工艺维度；采用“基准价 + 经验证工艺调整”的分层模型控制采样规模。明确不接入金（锡）手指斜边和钢网选项，JLC 未支持或未通过组合验证的规格继续人工复核。
todos:
  - id: freeze-v5-process-options
    content: 复采并冻结三材料四类常用工艺枚举、标准档和分层采样矩阵
    status: completed
  - id: sample-v5-process-prices
    content: 完善铜厚及工艺选中态采样，完成标准档、单工艺和组合 holdout 三次 DOM 复采
    status: completed
  - id: validate-v5-process-model
    content: 拟合工艺调整与有限组合修正，建立整体及分材料独立发布门禁
    status: completed
  - id: publish-v5-process-data
    content: 同步 v5 工艺枚举、模型、验证边界和开关，并保证失败不覆盖 v4
    status: completed
  - id: integrate-v5-process-quote
    content: 接入后端、前端四语和 PDF，保持历史报价及标准档兼容
    status: completed
  - id: verify-v5-release
    content: 完成回归、部署、浏览器 JLC 对比并输出 v5 准确度报告
    status: completed
isProject: false
---

# PCB 制造费精确报价第五版

## 范围与原则
- 保留 v4 的 `exact_lookup → verified_estimate → manual_review` 基准报价链路、10% margin 和 CNY→KRW 换算。
- 新增且仅新增四类常用工艺：板厚、阻焊颜色、表面处理、铜厚；各材料的实际枚举以 JLC 页面复采结果为准，不强行共用同一组选项。
- 明确排除金（锡）手指斜边和“是否开钢网”，不生成字段、不采样、不出现在前端或 PDF。
- 不做四维工艺全交叉采样；采用标准工艺基准价、单工艺增量采样及多工艺组合 holdout。未覆盖、页面不支持或验证失败的组合制造费为 0，并进入人工复核。

## 实现步骤
1. **冻结工艺枚举与分层采样矩阵**
   - 扩展 [scripts/jlc-cn-pcb-golden-targets.mjs](scripts/jlc-cn-pcb-golden-targets.mjs)，先对 FR-4、FPC、铝基板分别 smoke，冻结四类工艺的主流选项、标准档和材料适用性。
   - 保持 v4 的 222 个标准工艺基准规格；另选材料、层数、尺寸和数量代表锚点做 OFAT 单工艺采样，再生成未参与拟合的多工艺组合 holdout，避免约 4 万规格的全交叉矩阵。
   - 为所有目标写入 `boardThickness`、`solderColor`、`surfaceFinish`、`copperThickness`，并将四字段纳入样本唯一键和断点续采键。

2. **完善 JLC DOM 工艺选项采样**
   - 更新 [scripts/jlc-cn-browser-sample.mjs](scripts/jlc-cn-browser-sample.mjs)，补齐铜厚选择器，并验证每次报价前页面最终选中态与目标一致；继续使用 `JLC_CONTEXT_SCOPE=spec` 隔离隐藏状态。
   - 标准档、单工艺档和组合档均执行三次 DOM 复采；选项不存在、选中态不一致、活动异常价或重复 CV 超标时拒绝样本，不用 API/历史价格替代发布数据。

3. **拟合工艺调整并建立独立门禁**
   - 扩展 [scripts/jlc-cn-pcb-validate-samples.mjs](scripts/jlc-cn-pcb-validate-samples.mjs)，在 v4 基准价模型之后按材料拟合工艺增量；先比较乘法系数与加性差额的 holdout 表现，按验证结果选择，不预设所有工艺完全可分离。
   - 对明显存在交互的常用组合增加有限的组合修正项；没有对应验证依据的组合不得自动报价。
   - 工艺 holdout 单独统计整体及分材料 Hit@20%、MAPE、最大相对误差，并要求整体及每种启用材料 `Hit@20%≥80%`；某材料失败时仅关闭该材料的工艺自动报价，不影响其 v4 标准档报价。

4. **发布 v5 数据并保持可回滚**
   - 扩展 [scripts/jlc-cn-pcb-sync-table-data.mjs](scripts/jlc-cn-pcb-sync-table-data.mjs) 和 [backend/apps/simplequote/table_data.py](backend/apps/simplequote/table_data.py)，同步材料级工艺枚举、标准档、调整参数、已验证组合边界、验证指标及独立启用开关，版本使用 `jlc-cn-pcb-v5-YYYYMMDD`。
   - sync 前强制检查 v4 基准门禁与 v5 工艺门禁；失败时不得覆盖当前生效的 v4 数据。继续复用现有 QuoteTable JSON 数据结构，不做数据库迁移。

5. **接入后端、前端和 PDF**
   - 在 [backend/apps/simplequote/calculator.py](backend/apps/simplequote/calculator.py) 读取四个工艺字段：先得到 v4 基准精确价或估算价，再应用已验证的工艺调整；返回所选工艺、调整明细、工艺模型版本和验证状态。缺失新字段的历史请求按各材料标准档处理，价格与 v4 一致。
   - 在 [frontend/src/views/quote/SimpleQuoteView.vue](frontend/src/views/quote/SimpleQuoteView.vue) 增加四个随材料联动的工艺控件与结果追溯信息；在 [frontend/src/i18n/index.js](frontend/src/i18n/index.js) 补齐四语文案。排除项不得出现。
   - 在 [backend/core/pdf.py](backend/core/pdf.py) 记录所选工艺、基准计价方式、工艺调整和版本；历史报价缺字段时按标准档兼容显示。

6. **回归、复采和准确度验收**
   - 扩展 [backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py](backend/apps/simplequote/tests/test_pcb_manufacturing_quote.py)，覆盖标准档与 v4 同价、四种单工艺、多工艺组合、材料不适用项、非法值、未验证组合、分材料开关、范围外降级、历史结果及金额换算。
   - 执行完整采样、验证、sync/seed、Django check、后端测试、前端 build、Compose 更新与健康检查。
   - 浏览器按材料抽查标准档、每类单工艺和多工艺组合，并与同轮 JLC DOM 最终价逐项比较；生成 [docs/pcb-quote-v5-accuracy-test-report.md](docs/pcb-quote-v5-accuracy-test-report.md)，分别报告基准 exact、基准 estimator、工艺组合指标及人工复核边界。

## 验收标准
- 四类工艺仅展示各材料经 JLC DOM 确认的常用选项；金（锡）手指斜边和钢网在全链路中均不存在。
- 标准工艺档的三材料报价与 v4 完全一致，现有 exact、estimator、margin、汇率和历史报价无回归。
- 所有发布工艺样本三次 DOM 复采有效且 CV≤2%；工艺 holdout 整体及每种启用材料 Hit@20%≥80%。
- 已验证组合自动报价且可追溯基准版本、工艺模型版本和调整明细；未验证、材料不适用或页面不支持的组合人工复核且制造费为 0。
- 后端检查与测试、前端构建、Docker 健康检查和浏览器 JLC 对比均通过，并产出 v5 Markdown 准确度报告。