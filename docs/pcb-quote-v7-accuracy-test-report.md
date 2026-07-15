# PCB 报价第七版准确度测试报告

- 生成时间：2026-07-13T04:34:43.037091+00:00
- 价格版本：`jlc-cn-pcb-v7-20260713`
- 工艺模型：`jlc-cn-pcb-v7-process-20260713`（`validated_ofat_scale_segment_interaction_v1`）
- 验收状态：**failed**（独立大型实采门禁未全过）
- 独立性证明：`ok=true`（拟合 / 工艺 holdout / 最终验收规格键交集为 0）
- 验收目标：120；当前新鲜独立 DOM 唯一样本：**48**（实采仍在断点续采中）
- 主 exact/estimator 拟合门禁：此前已通过（三材料启用）
- 工艺启用材料：`aluminum`
- 工艺启用分区（FR-4 / FPC 局部放行）：
  - `fr4_boardThickness_1.0`
  - `fr4_surfaceFinish_OSP`
  - `fr4_panelDesignCount_2`
  - `fr4_solderColor_白色`
  - `fr4_surfaceFinish_无铅喷锡`
  - `fpc_boardThickness_0.20`
- SMT：`smt_required` 仅记录，`smt_price_included=false`（不计入制造费）

## 门禁对照

| 门禁 | 结果 |
|---|---|
| `independenceOk` | 通过 |
| `freshPerMaterialAtLeast40` | 未通过（FR-4 31 / FPC 6 / 铝基 11） |
| `overallHit10AtLeast90` | 未通过（75.00%） |
| `overallHit20AtLeast95` | 通过（95.83%） |
| `overallMapeAtMost8` | 通过（7.58%） |
| `overallMaxErrAtMost20` | 未通过（54.80%） |

## 总体指标（JLC 估算价，不含 10% margin）

| 指标 | 结果 |
|---|---:|
| 自动报价样本 | 48 |
| Hit@10% | 75.00% |
| Hit@20% | **95.83%** |
| MAPE | **7.58%** |
| 最大相对误差 | **54.80%** |

## 分材料

| 材料 | 新鲜 DOM | Hit@10% | Hit@20% | MAPE | 最大误差 |
|---|---:|---:|---:|---:|---:|
| FR-4 | 31 | 77.42% | 96.77% | 7.60% | 54.80% |
| FPC | 6 | 100% | 100% | 4.20% | 8.41% |
| 铝基板 | 11 | 54.55% | 90.91% | 9.38% | 25.27% |

## 最大误差锚点（仅报告，不回写拟合）

| 样本 | 规格 | 实价 CNY | 估算 CNY | 相对误差 |
|---|---|---:|---:|---:|
| `JLC-CN-PCB-V7-ACC-FR4-025-R1` | FR-4 2L 99×161×100 | 463.76 | 717.90 | 54.80% |
| `JLC-CN-PCB-V7-ACC-ALU-004-R1` | 铝基 1L 61×99×15 | 64.39 | 48.12 | 25.27% |

> 按 v7 防泄漏协议：**不得**用最终验收样本调参或新增风险区后再宣称验收通过。上述锚点仅用于后续独立迭代。

## 采样与数据协议

- 拟合 / holdout / 验收三套规格互斥，见 `scripts/jlc-cn-pcb-v7-assert-split-report.json`
- 采样器增强：页面指纹、DOM/API 双价格、失败分类、三次复采门槛；续采写回改为**合并**避免子集覆盖
- 工艺矩阵覆盖见 `scripts/jlc-cn-pcb-v7-process-coverage.json`（bootstrap + pending live）
- 续采命令：
  - `node scripts/jlc-cn-browser-sample.mjs pcb-acceptance-v7 scripts/jlc-cn-pcb-v7-acceptance-samples.json`
  - `python scripts/jlc-cn-pcb-v7-acceptance-score.py`

## 发布结论

- **独立大型验收未达门禁** → 按方案：正式“可认证发布”应回退/继续以 `jlc-cn-pcb-v6-20260712` 为准。
- 代码侧已落地 v7 能力，并写入 `table_data` 版本 `jlc-cn-pcb-v7-20260713`，同时标记：
  - `acceptance_status=failed`
  - `independence_proof.ok=true`
  - 工艺 `partial_pass` + 分区放行
- 标准工艺、10% margin、汇率、历史请求契约与 `smt_required` 不改价路径已通过单元测试（33）。
- 前端选项与四语文案已覆盖 OSP / 0.20mm / 拼板款数 / 阻焊覆盖等开放枚举；PDF 无新增字段，无需改版。
- 下一步：补齐每材料 ≥40 新鲜 DOM，对最大误差锚点做**新一轮独立 holdout**后再判定是否认证发布。
