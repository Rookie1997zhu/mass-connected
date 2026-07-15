# PCB 报价第八版准确度测试报告

- 生成时间：2026-07-14T00:26:22.786106+00:00
- 活动价格版本：`jlc-cn-pcb-v6-20260712`
- 验收状态：**failed**
- 独立性证明：`ok=True`
- 指纹冻结：`fnvish_4cd79a17`
- 验收目标：360；新鲜独立 DOM 唯一样本：119
- 当前 table_data acceptance_status：`failed`
- 运行时 estimator 配置审计：`ok=True`

## 门禁对照

| 门禁 | 结果 |
|---|---|
| `independenceOk` | 通过 |
| `fingerprintOk` | 通过 |
| `freshPerMaterialAtLeast40` | 未通过 |
| `overallHit10AtLeast90` | 未通过 |
| `overallHit20AtLeast95` | 未通过 |
| `overallMapeAtMost8` | 未通过 |
| `overallMaxErrAtMost20` | 未通过 |
| `materialsHit20Ok` | 未通过 |
| `materialsMaxErrOk` | 未通过 |

## 总体指标（JLC 估算价，不含 10% margin）

| 指标 | 结果 |
|---|---:|
| 自动报价样本 | 79 |
| Hit@10% | 83.54% |
| Hit@20% | 94.94% |
| MAPE | 35.19% |
| 最大相对误差 | 2161.42% |
| 隔离异常规格 | 2 |

## 分材料新鲜样本计数

| 材料 | 新鲜唯一 DOM |
|---|---:|
| FR-4 | 39 |
| FPC | 40 |
| 铝基板 | 40 |

## 发布结论

- 独立大型验收未达门禁。
- 保持活动版本：`jlc-cn-pcb-v6-20260712`。
