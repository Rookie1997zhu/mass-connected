---
name: 刀版精度升级
overview: 在现有刀版参数化模板库上做 A+B 组合升级：先补齐标准盒型的真实参数化几何与楞型/工艺参数，再预留真实刀版资产管理能力，为后续半自动参数化导入打基础。
todos:
  - id: contract
    content: 定义新增刀版参数契约与阶段边界
    status: completed
  - id: backend-model
    content: 设计后端模型字段、迁移与序列化更新
    status: completed
  - id: geometry-engine
    content: 补齐 0713/0716 前端真实刀版几何并升级容差逻辑
    status: completed
  - id: admin-user-ui
    content: 规划管理端和用户端字段展示、资产上传与提示文案
    status: completed
  - id: validation
    content: 设计测试、自检、验收与后续半自动导入边界
    status: completed
isProject: false
---

# 刀版精度升级 A+B 方案

## 目标与范围

目标：把当前「模板 + engine_key + 简化公式」升级为更接近 Pacdora 的「标准参数化引擎 + 真实刀版资产库」。短期解决 0713/0716 只显示空矩形、内/外/制造尺寸换算粗糙、模板缺少楞型/尺寸范围/工艺参数的问题。

本期做：
- 补齐 `tuck_end`、`auto_lock_bottom` 的真实 2D 刀版线段，取消外框占位预览。
- 新增楞型/材质相关参数，替代单一按厚度推算的内外尺寸容差。
- 增加模板级工艺参数，如开槽宽、工艺缝、粘口斜切、尺寸范围、默认尺寸口径。
- 增加真实刀版资产字段，允许后台上传/绑定 DXF/CF2/SVG/PDF/AI 作为生产参考资产。
- 用户端明确区分「参数化生成图」和「生产参考资产」。

本期不做：
- 不做全新拓扑表达式引擎。
- 不做管理员图形化模板编辑器。
- 不做 artwork 图案贴合。
- 不做 3D 预览和刀版转 GLTF。
- 不做完整半自动参数化导入器，只预留数据结构与上传入口。

## 实现步骤

1. 统一刀版参数契约
- 梳理现有 `[backend/apps/simplequote/models.py](backend/apps/simplequote/models.py)`、`[backend/apps/simplequote/packaging.py](backend/apps/simplequote/packaging.py)`、`[frontend/src/lib/packaging/boxEngine.ts](frontend/src/lib/packaging/boxEngine.ts)` 的尺寸、厚度、粘口参数。
- 定义新增字段：`flute_type`、`material_type`、`default_dimension_type`、`min/max L/W/H`、`slot_gap_mm`、`crease_gap_mm`、`flap_gap_mm`、`structure_params`、`production_asset_*`。
- 明确 `allowances` 用法：先作为模板级容差覆盖，不再只是空 JSON。

2. 后端模型与迁移
- 修改 `[backend/apps/simplequote/models.py](backend/apps/simplequote/models.py)` 的 `DielineTemplate`，增加楞型、材质、尺寸范围、工艺参数和真实刀版资产字段。
- 新增迁移，给既有模板回填默认值：0201/0210 默认 B 楞参考；0713/0716 默认纸卡或白卡参考，具体以现有模板设定为准。
- 更新 `[backend/apps/simplequote/serializers.py](backend/apps/simplequote/serializers.py)`，支持新字段读写、文件上传、JSON 参数校验。

3. 后端尺寸换算升级
- 将 `[backend/apps/simplequote/packaging.py](backend/apps/simplequote/packaging.py)` 中 `_board_allowances(thickness_mm)` 升级为「楞型/材质 + 厚度 + 模板覆盖」的容差解析。
- `manufacturing_dims` 和 `size_triple_from_manufacturing` 接收模板上下文，优先使用模板 `allowances`，否则按楞型表回退。
- 保持旧请求兼容：没有传楞型或模板无配置时使用当前默认逻辑。

4. 前端刀版引擎补齐
- 在 `[frontend/src/lib/packaging/boxEngine.ts](frontend/src/lib/packaging/boxEngine.ts)` 或拆分文件中补齐 `buildTuckEndSegments` 与 `buildAutoLockBottomSegments`。
- `buildPreview` 对 `tuck_end`、`auto_lock_bottom` 不再走 `buildBlankOutlineSegments`。
- 复用 `[frontend/src/lib/packaging/dielineUtils.ts](frontend/src/lib/packaging/dielineUtils.ts)` 的线段工具，补出插舌、摇盖、防尘翼、锁底切线/压线。

5. 前端目录与表单字段同步
- 扩展 `[frontend/src/lib/packaging/fefcoCatalog.ts](frontend/src/lib/packaging/fefcoCatalog.ts)` 类型，接收楞型、尺寸范围、默认尺寸口径、工艺参数和生产资产 URL。
- 更新 `[frontend/src/views/packaging/BoxGeneratorView.vue](frontend/src/views/packaging/BoxGeneratorView.vue)`：按模板默认尺寸口径预填，选择材质/楞型时更新容差；下载区显示「参数化导出」和「生产参考资产」区别。
- 更新 `[admin/src/views/DielineTemplatesView.vue](admin/src/views/DielineTemplatesView.vue)`：新增楞型、尺寸范围、工艺参数、真实刀版资产上传入口。

6. 真实刀版资产库第一版
- 后端仅保存和返回资产，不解析拓扑。
- 管理端可上传 DXF/CF2/SVG/PDF/AI 参考资产，前端用户端可查看/下载。
- 资产用途标注为「生产参考，参数化变尺寸仍以引擎生成图为准」。

7. 测试与验收准备
- 扩展 `[frontend/src/lib/packaging/dielineAssertions.ts](frontend/src/lib/packaging/dielineAssertions.ts)`，校验 0713/0716 不再是外框占位，cut/crease 数量、关键折线、插舌/锁底结构存在。
- 扩展 `[backend/apps/simplequote/tests/test_packaging.py](backend/apps/simplequote/tests/test_packaging.py)`，覆盖楞型容差、模板覆盖、尺寸范围错误。
- 构建与自检：后续实现阶段按 `self-check-after-change` 执行前后端测试、build 与部署验证。

## 风险与缓解

- 生产级准确性风险：参数化引擎仍不是盒厂验证图。缓解：页面和导出文案标注「结构参考，投产前需确认」，真实刀版资产作为生产参考库逐步积累。
- 0713/0716 几何复杂度风险：锁底结构可能与具体盒厂版本不完全一致。缓解：先做标准版，`structure_params` 预留比例参数，后续按真实样例微调。
- 新字段迁移风险：已有模板不能为空。缓解：迁移回填默认值，API 保持旧字段兼容。
- 前后端公式不一致风险：报价面积以后端为准，前端预览需同步同一套参数。缓解：新增测试固定样例，对比 blank 尺寸和关键结构点。
- 文件资产误用风险：用户可能把静态资产当成可变尺寸刀版。缓解：UI 明确区分「生产参考资产」与「当前尺寸参数化导出」。

## 验收标准

1. 选择 0713、0716 时，预览不再显示矩形加十字占位，而是出现对应插舌盒/自锁底盒的切线与折线。
2. 用户选择不同楞型或模板容差后，制造/内/外尺寸换算发生可解释变化，后端报价与前端展示口径一致。
3. 管理端可为模板维护楞型、尺寸范围、默认尺寸口径、工艺参数和生产参考资产。
4. 用户输入超出模板尺寸范围时，前端提示并阻止无效预览/报价；后端也返回稳定错误。
5. 用户端目录接口返回新增字段，旧模板在无新增配置时仍可正常预览与报价。
6. 后端包装测试、前端包装测试、前端/admin build 通过。

## 后续阶段

本计划完成后，再考虑阶段二：半自动参数化导入器。它会解析 DXF/CF2/SVG 线段，并由结构工程师人工标注 L/W/H 映射、固定边、比例边、工艺线类型。图形化拓扑编辑器、artwork 贴合和 3D 预览仍放在更后期。