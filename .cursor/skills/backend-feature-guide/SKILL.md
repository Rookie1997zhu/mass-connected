---
name: backend-feature-guide
description: 后端新功能开发指引（Django/DRF & PHP）。新增接口、模型字段、业务逻辑或模块时，按本技能执行，确保接口设计、权限校验、数据边界（多租户/组织级，按项目约定）、序列化与错误处理符合项目规范。
---

# 后端新功能开发指引

## 何时使用

- 新增接口（ViewSet action / APIView / PHP Controller 方法）
- 新增或修改业务逻辑模块
- 新增序列化器 / 表单验证 / DTO
- 新增模型字段或关联关系（迁移相关另见 `backend-migration-and-model` 技能）

---

## 第一步：明确任务边界

开始写代码前先确认：

1. **资源归属**：这个接口/模块属于哪个业务域？不跨域混写。
2. **是否需要新文件**：复用现有 ViewSet/Controller 还是新建？不要无谓拆碎，也不要无限叠加到同一个大文件。
3. **依赖关系**：是否依赖还未存在的数据结构或权限点？先补齐依赖，再写业务逻辑。

---

## 第二步：接口设计检查

### 路由与命名

- 路由使用**资源化命名**，不混用动词路径（禁止 `/do_something`，应为 `/resources/{id}/action`）。
- 方法名遵循「资源 + 动作」：`projectList`、`projectCreate`、`projectUpdate`、`projectDestroy`。
- DRF：新 action 用 `@action(detail=True/False, methods=[...])` 而不是单独注册路由。
- PHP：Controller 方法名遵循 `index / show / store / update / destroy` 或项目约定。

### 请求与响应

- 请求参数验证必须走序列化器（DRF Serializer）或表单验证（PHP Request 类），不在 View/Controller 内手写 `request.data.get(...)` 裸取值。
- 成功响应统一使用项目封装的响应包结构（参见 `01-foundation-api-contract` 规则）。
- 错误响应统一返回结构化 `errors`，不直接返回裸字符串。

---

## 第三步：权限与数据边界（必查）

若项目存在**多租户、组织、工作区**等数据边界，字段名以仓库约定为准（如 `tenant_id`、`org_id`、`workspace_id`）；单租户项目则重点做**认证、授权与资源归属**校验。

### Django/DRF

```python
# ✅ 必须显式声明权限类
permission_classes = [IsAuthenticated, YourCustomPermission]

# ✅ 有数据边界时：查询须与当前主体作用域一致（以下为示意，字段名按项目替换）
scope_id = getattr(request.user, "tenant_id", None)  # 或 org_id / workspace_id 等
queryset = Model.objects.filter(tenant_id=scope_id)

# ❌ 禁止：在应隔离的场景下返回全表
queryset = Model.objects.all()
```

### PHP（Laravel 示例）

```php
// ✅ 必须显式鉴权
$this->authorize('view', $resource);

// ✅ 有数据边界时：查询须与当前主体作用域一致（字段名按项目替换）
$items = Model::where('tenant_id', auth()->user()->tenant_id)->get();

// ❌ 禁止：在应隔离的场景下返回全表
$items = Model::all();
```

**强制检查项**：

- [ ] 接口是否声明了权限类/中间件？
- [ ] 凡存在多租户/组织级边界时，查询是否都带了项目约定的**作用域字段**过滤？
- [ ] 有无直接用 URL 参数 `id` 查询而未校验归属的情况（需配合 `get_object_or_404` 或 `findOrFail` + 归属/策略校验）？

---

## 第四步：序列化与字段验证（DRF）

```python
class ExampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Example
        fields = ['id', 'name', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_status(self, value):
        allowed = ['active', 'inactive']
        if value not in allowed:
            raise serializers.ValidationError(f'状态必须是 {allowed} 之一')
        return value
```

- `read_only_fields` 必须显式声明，避免外部写入不可变字段。
- 跨模型关联字段建议用 `PrimaryKeyRelatedField` 或嵌套序列化器，不手写 `validated_data['xxx_id']`。

---

## 第五步：异常处理

### Django/DRF

```python
from rest_framework.response import Response
from rest_framework import status

# ✅ 业务异常显式返回，不吞
try:
    result = some_service(data)
except SomeBusinessError as e:
    return Response(
        {'code': 'MODULE_ACTION_REASON', 'message': str(e)},
        status=status.HTTP_400_BAD_REQUEST
    )
```

- **导入必查**：使用 `Response` 前确认同文件有 `from rest_framework.response import Response`；使用 `status.HTTP_*` 前确认有 `from rest_framework import status`。
- 不使用裸 `except:` 或空 `except Exception: pass`。

### PHP（Laravel）

```php
// ✅ 业务异常统一抛出自定义 Exception 或用 abort()
throw new BusinessException('MODULE_ACTION_REASON', '描述信息');

// ✅ 在 Handler 统一格式化响应，不在 Controller 内重复写响应结构
```

---

## 第六步：新功能完成前必查清单

- [ ] 路由命名是否资源化、无动词路径？
- [ ] 权限类/中间件是否已声明？
- [ ] 在需要隔离的场景下，查询是否带了项目约定的数据边界过滤？
- [ ] 是否有用 URL id 直接查库而未校验归属？
- [ ] 序列化器是否声明了 `read_only_fields`？
- [ ] 异常处理是否显式，无吞异常？
- [ ] Response 与 status 导入是否完整（DRF）？
- [ ] 新接口是否补了权限点注册（若项目有权限点管理）？
- [ ] 列表接口是否支持分页？

---

## 接口级冒烟（必须）

新增或修改接口完成后，至少验证：

1. **未登录请求** → 预期 401/403
2. **已登录但无权限的请求** → 预期 403
3. **已登录有权限的请求** → 预期 2xx 或明确的业务态
4. **参数缺失或非法的请求** → 预期 400 + 结构化 errors

`manage.py check` 通过不等于接口运行路径正确，必须实际调用验证。
