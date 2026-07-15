# JLC 中文站 PCB 公开报价采样

## 1. 声明

本采样仅用于 OEM.co 内部 PCB 制造费估算。数据来自 JLC 中文公开下单页，不代表 JLC 官方完整价格表、合同价或最终成交价；不登录、不上传 Gerber、不下单。

## 2. v6 范围

| 材料 | 层数 | 尺寸(mm) | 数量 |
|---|---|---|---|
| FR-4 | 2、4 | v3 尺寸 + 200×200 | 5、10、20、50、100、200 |
| FPC 软板 | 1、2 | v3 尺寸 + 200×200 | 5、10、20、50、100、200 |
| 铝基板 | 1 | v3 尺寸 + 200×200 | 5、10、20、50、100、200 |

v6 继承已通过验证的 666 条 v4 golden 基准，并新增阻焊覆盖、拼板款数、OSP 与关键两两交互的 OFAT/交互复采，以及独立组合 holdout。铜厚在当前公开页验证范围内仅发布 1oz；金（锡）手指斜边和钢网不采样；SMT 仅作需求标记。

## 3. 数据源与固定选项

- 权威值：DOM「预估支付总价(不含运费)」。
- API：`calculateCustomerOrderMoney`，仅用于交叉校验。
- 页面尺寸单位为 cm；targets 与业务价格表使用 mm，采样器自动除以 10。
- FR-4：1.6mm、绿色、有铅喷锡、过孔盖油、拼板 1。
- FPC：页面默认 FPC 工艺、拼板 1。
- 铝基板：1.6mm、绿色、无铅喷锡、过孔盖油、拼板 1。
- 通用：工业/消费/其他类电子产品、不需要确认生产稿、默认测试项。
- 采样隔离：`JLC_CONTEXT_SCOPE=spec`，三次复采，CV≤2%，工艺选中态校验。

## 4. 采样文件

| 文件 | 用途 |
|---|---|
| `scripts/jlc-cn-pcb-golden-targets.mjs` | 唯一 targets 生成源 |
| `scripts/jlc-cn-pcb-v4-smoke-targets.json` | 200×200mm/200片支持预检 |
| `scripts/jlc-cn-pcb-golden-v4-*-targets.json` | 按材料隔离的每规格 3 次 golden targets |
| `scripts/jlc-cn-pcb-exact-holdout-v4-targets.json` | 精确表独立 holdout |
| `scripts/jlc-cn-pcb-estimator-holdout-v4-targets.json` | 档间与边界 estimator holdout |
| `scripts/jlc-cn-pcb-golden-v4-samples.json` | 合并后的 v4 Golden DOM 样本 |
| `scripts/jlc-cn-pcb-v4-estimator.json` | 版本化 estimator 参数和门禁状态 |
| `scripts/jlc-cn-pcb-process-v5-options.json` | 分材料常用工艺、标准档和页面适用性 |
| `scripts/jlc-cn-pcb-process-v5-*-targets.json` | v5 单工艺三次复采 targets |
| `scripts/jlc-cn-pcb-process-holdout-v5-targets.json` | 未参与拟合的多工艺组合 holdout |
| `scripts/jlc-cn-pcb-v5-process-model.json` | 工艺调整模型、分材料开关和验证指标 |
| `scripts/jlc-cn-pcb-validation-report.json` | 分材料验证报告 |

采样器每条成功样本立即落盘。再次运行时，只跳过 ID、规格及 `samplingVersion` 均一致且 `priceSource=dom` 的样本；错误样本会重跑。

## 5. 命令

```powershell
node scripts/jlc-cn-pcb-golden-targets.mjs
$env:JLC_HEADLESS='false'
$env:JLC_CONTEXT_SCOPE='spec'
node scripts/jlc-cn-browser-sample.mjs scripts/jlc-cn-pcb-golden-v4-fr4-targets.json scripts/jlc-cn-pcb-golden-v4-fr4-samples.json
node scripts/jlc-cn-browser-sample.mjs scripts/jlc-cn-pcb-golden-v4-fpc-targets.json scripts/jlc-cn-pcb-golden-v4-fpc-samples.json
node scripts/jlc-cn-browser-sample.mjs scripts/jlc-cn-pcb-golden-v4-aluminum-targets.json scripts/jlc-cn-pcb-golden-v4-aluminum-samples.json
node scripts/jlc-cn-pcb-merge-v4-samples.mjs scripts/jlc-cn-pcb-golden-v4-samples.json scripts/jlc-cn-pcb-golden-v4-fr4-samples.json scripts/jlc-cn-pcb-golden-v4-fpc-samples.json scripts/jlc-cn-pcb-golden-v4-aluminum-samples.json
node scripts/jlc-cn-browser-sample.mjs scripts/jlc-cn-pcb-process-v5-fr4-targets.json scripts/jlc-cn-pcb-process-v5-fr4-samples.json
node scripts/jlc-cn-browser-sample.mjs scripts/jlc-cn-pcb-process-v5-fpc-targets.json scripts/jlc-cn-pcb-process-v5-fpc-samples.json
node scripts/jlc-cn-browser-sample.mjs scripts/jlc-cn-pcb-process-v5-aluminum-targets.json scripts/jlc-cn-pcb-process-v5-aluminum-samples.json
node scripts/jlc-cn-browser-sample.mjs scripts/jlc-cn-pcb-process-holdout-v5-targets.json scripts/jlc-cn-pcb-process-holdout-v5-samples.json
node scripts/jlc-cn-pcb-merge-v4-samples.mjs scripts/jlc-cn-pcb-process-v5-samples.json scripts/jlc-cn-pcb-process-v5-fr4-samples.json scripts/jlc-cn-pcb-process-v5-fpc-samples.json scripts/jlc-cn-pcb-process-v5-aluminum-samples.json
node scripts/jlc-cn-pcb-validate-samples.mjs scripts/jlc-cn-pcb-golden-v4-samples.json scripts/jlc-cn-pcb-exact-holdout-v4-samples.json scripts/jlc-cn-pcb-estimator-holdout-v4-samples.json scripts/jlc-cn-pcb-process-v5-samples.json scripts/jlc-cn-pcb-process-holdout-v5-samples.json
```

只有验证报告为 `passed` 时才继续：

```powershell
node scripts/jlc-cn-pcb-sync-table-data.mjs
docker compose exec backend python manage.py seed_quote_tables
```

## 6. 验证门禁

- 每个 golden 唯一规格重复 3 次；
- 有效价格必须来自 DOM；
- 材料、层数、尺寸、数量选中态必须与 target 一致；
- 重复价格 `CV <= 2%`；
- 整体及 FR-4、FPC、铝基板各自 `Hit@20% >= 80%`；
- 整体及分材料最大相对误差 `<= 100%`；
- v5 工艺样本还必须校验实际选中态；工艺组合 holdout 整体及各启用材料 `Hit@20% >= 80%`；
- 最低 live DOM 数：
  - FR-4：golden 60、holdout 10；
  - FPC：golden 30、holdout 8；
  - 铝基板：golden 20、holdout 8。

Exact 门禁失败时不覆盖当前生效表。Estimator 与 v5 工艺模型均按材料独立开关，失败材料保留标准工艺的 v4 报价，非标准工艺降级人工复核。跨规格共享 JLC 页面上下文可能残留隐藏工艺状态，因此所有 live 采样必须使用 `JLC_CONTEXT_SCOPE=spec`。

## 7. 不覆盖项

运费、税费、优惠券、账号活动、加急、孔数、V-CUT、铣边、沉金面积、测试点、阻抗、盲埋孔及其他依赖 Gerber 审核的工艺均不在公开页面精确表范围内。
