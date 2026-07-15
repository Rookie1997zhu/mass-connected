---
name: PCB报价第二版
overview: 第二版先不扩展材料或复杂工艺，聚焦修正 JLC 实时采样可靠性、完成 FR-4/FPC 复采门禁、更新精确价格表，并在 Docker 恢复后做浏览器端到端验收。
todos:
  - id: fix-sampler-price-source
    content: 修复 JLC 采样脚本价格读取竞态，DOM 最终价优先并记录 API 差异
    status: completed
  - id: strengthen-validation-gates
    content: 加强样本质量门禁，校验材料、层数、尺寸、数量和 DOM/API 差异
    status: completed
  - id: resample-golden-holdout
    content: 重新采集 golden 与 holdout 样本并生成验证报告
    status: in_progress
  - id: sync-price-table
    content: 将通过门禁的精确价格表同步到后端 seed 与元数据
    status: completed
  - id: update-docs-ui-notices
    content: 同步报价文档与必要的前端状态提示
    status: completed
  - id: run-regression-deploy-e2e
    content: 执行回归测试、Docker 部署和浏览器端到端对比验收
    status: completed
isProject: false
---

# PCB 制造费精确报价第二版计划

## 目标与范围

做：
- 修复 JLC 采样脚本的价格读取竞态，确保 DOM「预估支付总价」为最终权威值，API 只做辅助校验。
- 对 FR-4/FPC 自动报价范围重新复采，生成可启用的精确价格表和验证报告。
- 将通过门禁的价格表同步到后端 seed/文档，并保持未通过材料或规格自动降级人工复核。
- Docker 恢复后完成部署、seed、浏览器端到端对比。

不做：
- 不新增铝基板、罗杰斯、HDI 等材料自动报价。
- 不做最近邻、面积系数、复杂工艺外推。
- 不改变 PCB 开发原有基础报价、服务费、配送费计算口径。

## 现状依据

- 方案文件：[.cursor/plans/pcb制造费精确报价_cc823b16.plan.md](.cursor/plans/pcb制造费精确报价_cc823b16.plan.md)
- 当前验证报告：[scripts/jlc-cn-pcb-validation-report.json](scripts/jlc-cn-pcb-validation-report.json) 仍为 `pending_live_resample`，`pass=false`。
- 实时对比样本：[scripts/jlc-cn-browser-compare-live.json](scripts/jlc-cn-browser-compare-live.json) 显示 `FR-4 4层 100×150 qty5` JLC 实时价为 `265`，当前 legacy 表为 `212.5`。
- 同一对比文件中 FPC 样本存在 `displayedPriceCny=221.5` 但 `priceText` 中页面最终价为 `¥406`，说明采样脚本需要等待配置稳定并优先解析 DOM 最终价。

## 实现步骤

1. 修复采样价格读取
   - 修改 [scripts/jlc-cn-browser-sample.mjs](scripts/jlc-cn-browser-sample.mjs)。
   - 调整 `setQuote()` 的等待顺序：配置材料、层数、尺寸、数量、工艺后，再等待一次与当前规格匹配的报价稳定。
   - 调整 `readPrice()`：优先从页面「预估支付总价(不含运费)」解析最终价；API 的 `internetPayTotalmoney` 仅保存为 `apiPriceCny` 或 `priceBreakdown`，不覆盖 DOM 最终价。
   - 增加校验字段：`domPriceCny`、`apiPriceCny`、`apiDomDiff`、`priceSource`、`selectedQuantity`，方便后续剔除异常样本。

2. 加强采样有效性校验
   - 修改 [scripts/jlc-cn-pcb-validate-samples.mjs](scripts/jlc-cn-pcb-validate-samples.mjs)。
   - 对 `priceText` 与 API 不一致的样本不再静默采用 API 价；若 DOM 有最终价但 API 旧值不一致，标记 `api_dom_mismatch`，并按策略重试或剔除。
   - 对数量、层数、材料、尺寸误触增加硬校验，避免 FPC qty20 读成 qty5 价格。
   - 继续剔除特价样本，除非后续明确要把 JLC 特价作为标准报价口径。

3. 复采 golden 与 holdout 数据
   - 运行 `node scripts/jlc-cn-browser-sample.mjs pcb-golden scripts/jlc-cn-pcb-golden-samples.json`。
   - 运行 `node scripts/jlc-cn-browser-sample.mjs pcb-holdout scripts/jlc-cn-pcb-holdout-samples.json`。
   - 运行 `node scripts/jlc-cn-pcb-validate-samples.mjs` 生成新的 [scripts/jlc-cn-pcb-manufacturing-price-list.json](scripts/jlc-cn-pcb-manufacturing-price-list.json) 和 [scripts/jlc-cn-pcb-validation-report.json](scripts/jlc-cn-pcb-validation-report.json)。

4. 更新后端精确价格表
   - 若验证通过，将机器表同步到 [backend/apps/simplequote/table_data.py](backend/apps/simplequote/table_data.py) 的 `PCB_MANUFACTURING_PRICE_LIST` 与 `PCB_MANUFACTURING_PRICE_META`。
   - 明确 `validation_status`、`generated_at`、`valid_until`、`source`、`enabled_materials`。
   - 若某材料未通过门禁，仅启用通过材料；未通过材料继续 `requires_manual_review`。

5. 同步文档和前端提示
   - 更新 [docs/jlc-pcb-price-list.md](docs/jlc-pcb-price-list.md)、[docs/jlc-pcb-pricing-sampling.md](docs/jlc-pcb-pricing-sampling.md)、[docs/jlc-pcb-quote-standard.md](docs/jlc-pcb-quote-standard.md)。
   - 若价格表仍未通过，则前端 [frontend/src/views/quote/SimpleQuoteView.vue](frontend/src/views/quote/SimpleQuoteView.vue) 只展示人工复核或未启用提示。
   - 若价格表通过，则保持当前 FR-4/FPC 精确命中自动报价展示，不扩大表单能力。

6. 回归与部署后验收
   - 后端：运行 PCB 制造费单测、`py_compile`，Docker 恢复后补跑 `manage.py check` 和 PDF 冒烟。
   - 前端：运行 `npm run build`，必要时补跑 lint。
   - 部署：`docker compose up -d --build backend frontend caddy`，再执行 `seed_quote_tables`。
   - 浏览器验收：打开 `/simple-quote`，至少验证 FR-4 2层、FR-4 4层、FPC 2层三个命中规格；逐项对比系统 `JLC CNY 原价` 与 JLC 页面最终价。

## 风险与缓解

- JLC 页面状态异步导致旧报价混入：用 DOM 最终价优先、规格确认、稳定等待和重试剔除降低风险。
- JLC 活动价频繁变化：价格表记录采样时间和有效期，过期或验证失败自动降级人工复核。
- 特价是否应纳入报价口径不明确：第二版默认仍剔除特价样本，保持报价保守。
- Docker 当前不可用：实现和本地脚本可先做，部署验收必须等 Docker Desktop Linux 引擎恢复。
- 价格表替换影响报价金额：保留单测覆盖关闭开关金额不变、命中才计费、未命中不计入总额。

## 验收标准

1. FPC `100×150 qty20` 采样结果中最终 DOM 价应为 `406`，不得被旧 API 值 `221.5` 覆盖。
2. `FR-4 4层 100×150 qty5` 复采后后端价格表不再保留过期 `212.5`，应与 JLC 当前最终价一致或在验证失败时不启用自动报价。
3. [scripts/jlc-cn-pcb-validation-report.json](scripts/jlc-cn-pcb-validation-report.json) 输出真实 golden/holdout 统计，不再是 `pending_live_resample`。
4. 整体、FR-4、FPC 的 `Hit@20%` 均不低于 `80%`，且最大相对误差不超过 `100%`；未达标材料不启用自动报价。
5. 后端结果保存 JLC CNY 原价、客户价、KRW 换算价、价格版本、有效期和人工复核原因。
6. 关闭制造费开关时，现有 PCB 开发报价总额、PDF 和历史记录行为不变。
7. Docker 恢复后，浏览器页面 `/simple-quote` 的 FR-4/FPC 命中规格展示价与 JLC 页面最终价可逐项对上。

## 建议下一步

确认该计划后进入实现阶段；实现时先修采样脚本，再复采和更新价格表，最后做部署验收。