---
name: PCB 报价第九版
overview: 以 v8 失败数据只做诊断，重新采集独立的 v9 拟合、调参与验收数据；重点修复 FR-4 离群数据链路和铝基板系统性偏差，全部材料通过原门禁后才原子发布。
todos:
  - id: v9-diagnostics
    content: 输出逐样本误差明细，定位 FR-4 离群点并审计铝基启用配置
    status: completed
  - id: v9-data-protocol
    content: 建立 v9 diagnostic、互斥 split、支持包络、全新指纹与一次性消费门禁
    status: completed
  - id: v9-model
    content: 实现 FR-4 分段与铝基独立地板价/面积/数量模型及运行时护栏
    status: completed
  - id: v9-sampling
    content: 加固持久化网页采样并完成 v9 fit、tuning 与三采验收数据
    status: completed
  - id: v9-release
    content: 执行独立验收，只在三材料全部达标后原子发布
    status: completed
  - id: v9-regression
    content: 完成后端、前端、PDF、Compose 与失败回退回归验证
    status: completed
isProject: false
---

# PCB 制造费精确报价第九版

## 目标与范围
- 保持当前活动版本 `jlc-cn-pcb-v6-20260712`，v9 未通过前不改变线上自动报价。
- v8 冻结验收集 `fnvish_4cd79a17` 仅作为 diagnostic，禁止进入 v9 fit/tuning 或重新用于发布判定。
- 重做 FR-4 与铝基板估算；FPC 以防回归为主。
- 不改数据库结构和对外 API 契约；继续沿用现有前端/PDF 的版本与验收状态展示。

## 实现步骤
1. **补齐逐样本诊断与数据卫生**
   - 扩展 [`scripts/jlc-cn-pcb-v8-acceptance-score.py`](scripts/jlc-cn-pcb-v8-acceptance-score.py)，输出每个规格的 actual、predicted、relativeError、估算 basis、距离/覆盖度与工艺快照，精确定位 FR-4 2161% 离群点。
   - 在 [`scripts/jlc-cn-browser-sample.mjs`](scripts/jlc-cn-browser-sample.mjs) 修正重复工艺按钮读取、特价识别、DOM/API/规格一致性；异常样本进入 quarantine，不直接删除或用于拟合。
   - 校验 [`scripts/jlc-cn-pcb-validate-samples.mjs`](scripts/jlc-cn-pcb-validate-samples.mjs) 产物与 [`backend/apps/simplequote/table_data.py`](backend/apps/simplequote/table_data.py) 的 `estimator_enabled_materials` 完全一致，禁止手工越权启用铝基 estimator。

2. **建立 v9 数据协议与一次性门禁**
   - 新增 v9 的 spec-key、split 生成、split 断言与 acceptance score 脚本，沿用 v8 结构但显式拒绝 `V7-ACC`、`V8-ACC` 和 diagnostic 样本。
   - 将 v8 targets/samples 标记为 `v8_final_acceptance_do_not_train`，仅生成诊断报告。
   - 新建互斥的 boundary-fit、tuning-holdout、process-holdout、final-acceptance；final acceptance 每材料至少 48 个基样、每规格三采、CV ≤2%，确保有效样本仍不少于 40。
   - 独立性同时要求：无 exact/process-key 重叠、无近重复；每个验收点又必须位于同材料同层的模型支持包络内并具有至少 2 个合格 fit 邻居，避免 v8 的无覆盖外推。
   - 冻结全新的 v9 指纹，并记录“已消费”状态；同一指纹只能执行一次发布判定。

3. **重建分材料估算模型**
   - 在 [`scripts/jlc-cn-pcb-validate-samples.mjs`](scripts/jlc-cn-pcb-validate-samples.mjs) 与 [`backend/apps/simplequote/calculator.py`](backend/apps/simplequote/calculator.py) 保持镜像算法。
   - FR-4：定位并隔离错误锚点，按层数/面积/数量阶梯拟合，禁止数据异常造成数量级偏差。
   - 铝基：使用独立材料参数，分离起订地板价与面积/数量增长段；采用分材料距离阈值、局部邻居数和风险区，不再复用 FR-4 权重。
   - FPC：保留已达标路径并做回归；非标厚度仅在独立 holdout 达标区域启用。
   - 低覆盖、外推、异常倍率或材料未通过时统一返回人工复核，不允许自动报价。

4. **稳定采样链路并补采 v9 数据**
   - 复用当前已验证的 persistent browser profile、精确数量 selector、分批断点续采；增加页面健康检查、指数退避、浏览器会话关闭快速恢复。
   - 先采 boundary-fit 与 tuning，完成模型选择和风险区冻结；此后禁止再根据 final acceptance 调参。
   - 再生成并三采全新的 v9 final acceptance（预计至少 432 行），保存 DOM/API 双证据和页面指纹。

5. **独立验收与原子发布**
   - 维持严格门禁：每材料有效样本 ≥40；总体 Hit@10 ≥90%、Hit@20 ≥95%、MAPE ≤8%、最大误差 ≤20%；每材料 Hit@20 ≥95%、最大误差 ≤20%。
   - v9 必须三种材料全部通过才更新活动版本；任一失败则保持 v6，并将未通过材料继续限制为 exact/manual review。
   - [`scripts/jlc-cn-pcb-sync-table-data.mjs`](scripts/jlc-cn-pcb-sync-table-data.mjs) 只读取已通过且未消费的 v9 报告，写入前后校验 meta 完整性，失败不得产生半发布状态。

6. **回归与发布前验证**
   - 覆盖 exact lookup、材料级 estimator 开关、边界风险区、acceptance failed 回退、版本字段、PDF/前端提示的后端测试。
   - 执行 split/assert、采样完整性、评分脚本语法、后端测试、前端 lint/build、Compose 健康检查；确认同步脚本在失败报告下仍明确拒绝发布。

## 风险与缓解
- JLC SPA/促销价污染：持久化上下文、DOM/API 双校验、特价 quarantine、三采与断点恢复。
- 防泄漏导致无局部覆盖：把“近重复隔离”和“支持包络覆盖”设为两个同时通过的硬门，而不是简单扩大隔离带。
- 铝基小样本过拟合：扩大 boundary/tuning 覆盖，按材料建模，未过材料门禁不启用。
- 看到 v9 final acceptance 后再次调参：指纹一次性消费；失败后只能进入下一版本和新验收集。

## 验收标准
1. v8 验收样本均标记 diagnostic，任何 v9 fit/tuning/final acceptance 泄漏都会硬失败。
2. v9 final acceptance 每材料至少 40 个有效稳定规格，三采完整且 CV ≤2%。
3. 三种材料分别及总体全部达到既定误差门禁，无异常倍率样本被静默放行。
4. 运行时启用材料与验证产物一致；未通过材料只能 exact lookup 或人工复核。
5. v9 通过前同步脚本拒绝发布且活动版本保持 v6；通过后一次原子切换并保留回滚版本。
6. 后端测试、前端 lint/build 与服务健康检查无阻塞错误。