# PCB 报价第六版准确度测试报告

- 生成时间：2026-07-12
- 价格版本：`jlc-cn-pcb-v6-20260712`
- 工艺模型：`jlc-cn-pcb-v6-process-20260712`
- 样本：120 独立规格（不参与拟合），有效 DOM 120，自动报价 61，人工复核 59

## 总体指标（JLC 估算价，不含 10% margin）

| 指标 | 结果 |
|---|---:|
| Hit@10% | 83.61% |
| Hit@20% | **100.00%** |
| MAPE | 6.08% |
| 中位相对误差 | 4.61% |
| P90 | 11.16% |
| 最大相对误差 | **19.03%**（较 v5 大型验收 31.29% 明显下降） |

## 纯估算 vs 工艺组合

| 类别 | n | Hit@10% | Hit@20% | MAPE | 最大误差 |
|---|---:|---:|---:|---:|---:|
| 纯估算 | 49 | 85.71% | 100.00% | 5.94% | 19.03% |
| 工艺组合 | 12 | 75.00% | 100.00% | 6.67% | 16.04% |

## 客户价（含 10% margin）

| 指标 | 结果 |
|---|---:|
| Hit@10% | 55.74% |
| Hit@20% | 95.08% |
| MAPE | 9.61% |
| 最大相对误差 | 30.93% |

## 分材料（自动报价子集）

| 材料 | 自动报价 | Hit@10% | Hit@20% | MAPE | 最大误差 |
|---|---:|---:|---:|---:|---:|
| FR-4 | 12 | 66.67% | 100.00% | 7.74% | 13.04% |
| FPC | 34 | 94.12% | 100.00% | 5.21% | 19.03% |
| 铝基板 | 15 | 73.33% | 100.00% | 6.74% | 16.08% |

## v6 发布结论

- exact / estimator 主门禁：通过（`jlc-cn-pcb-v6-20260712`）
- 工艺自动报价启用材料：**aluminum**（FR-4 / FPC 工艺 holdout 未达门禁，非标准工艺继续人工复核）
- 风险分区已启用：
  - `fr4_4l_small_low_qty`：FR-4 4 层、面积 ≤4500mm²、数量 ≤20 → 人工复核
  - `fpc_nonstd_thickness_mid`：FPC 非标准板厚中等面积/数量区间 → 人工复核
- 扩展字段：阻焊覆盖、拼板款数、OSP（焊盘喷镀合并入 `surface_finish`）；铜厚公开页仍仅稳定发布 **1oz**
- `smt_required` 仅记录需求，`smt_price_included=false`，不改变 PCB 制造费
- 金手指斜边与钢网继续排除
- 标准工艺与 v5 基准 exact/estimator 无回归；最大自动报价误差由 31.29% 压到 19.03%

## 验证动作

- 后端单元测试：25 passed
- Django check（容器）：通过
- QuoteTable seed：`jlc-cn-pcb-v6-20260712`，risk_zones=2，process_enabled=`aluminum`
- 前端 / 后端 Compose 已重建部署

## 机器可读产物

- `scripts/jlc-cn-pcb-v6-accuracy-merged.json`
- `scripts/jlc-cn-pcb-v6-accuracy-report.json`
- `scripts/jlc-cn-pcb-v6-process-model.json`
- `scripts/jlc-cn-pcb-validation-report.json`
