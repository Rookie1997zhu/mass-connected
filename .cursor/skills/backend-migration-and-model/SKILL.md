---
name: backend-migration-and-model
description: 数据库模型变更与迁移规范（Django Migrations & PHP/Laravel Migrations）。新增字段、修改表结构、删除字段或执行数据迁移前，按本技能执行，避免生产事故。
---

# 数据库迁移与模型变更规范

## 何时使用

- 新增 Model 或新增字段
- 修改字段类型、长度、默认值、nullable
- 删除字段或重命名字段
- 新增或删除索引、唯一约束
- 需要做存量数据的迁移/回填（data migration）

---

## 核心原则

1. **迁移必须可前进、尽量可回滚**：每次迁移写完后，先在本地验证 `migrate` → `migrate --fake-initial` 或 `migrate <app> <prev>` 可回退（Django），或 `migrate:rollback`（Laravel）。
2. **不在迁移文件中写业务逻辑**：迁移文件只做 schema 和数据变更，不调用 service、发邮件、触发外部请求。
3. **生产迁移前必须在测试库执行一遍**：本地或 staging 验证通过后再推生产。
4. **大表变更需评估锁影响**：行数超过百万的表，加字段/加索引前必须评估是否需要在线 DDL 方案（`pt-online-schema-change`、`gh-ost` 或 `CONCURRENTLY`）。

---

## Django / DRF

### 新增字段安全模式

```python
# ✅ 新增字段必须设 null=True 或 default，否则生产迁移会失败
class Order(models.Model):
    remark = models.TextField(null=True, blank=True)       # 可为空
    priority = models.IntegerField(default=0)              # 有默认值

# ❌ 禁止在已有表上新增没有 default 且 not null 的字段
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # 生产报错
```

### 删除字段安全流程（两步走）

```
第一步：先在代码中移除字段引用（序列化器、查询、业务逻辑），部署上线。
第二步：再生成并执行删除字段的迁移。
```

禁止一步到位删字段后立即部署，防止旧进程读取已删字段导致报错。

### 重命名字段

不要直接 `RenameField`，分两步：

1. 新增新名称字段，双写一段时间。
2. 代码全部切到新字段后，再删旧字段。

### 数据迁移（RunPython）

```python
from django.db import migrations

def fill_default_status(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    # ✅ 用 apps.get_model，不直接 import 当前 Model 类
    Order.objects.filter(status='').update(status='pending')

def reverse_fill(apps, schema_editor):
    pass  # 回滚操作，不需要可以留空但必须声明

class Migration(migrations.Migration):
    dependencies = [('orders', '0005_add_status')]
    operations = [
        migrations.RunPython(fill_default_status, reverse_fill),
    ]
```

### 执行前检查清单

- [ ] 新字段是否有 `null=True` 或 `default`？
- [ ] 是否在本地执行过 `python manage.py migrate`？
- [ ] 是否在本地执行过 `python manage.py migrate <app> <prev_migration>` 确认可回退？
- [ ] 删除字段是否已先移除所有代码引用？
- [ ] RunPython 是否用了 `apps.get_model` 而非直接 import Model？
- [ ] 是否评估了大表 DDL 锁影响？

---

## PHP / Laravel

### 新增字段安全模式

```php
// ✅ 新字段必须 nullable 或有默认值
Schema::table('orders', function (Blueprint $table) {
    $table->string('remark')->nullable();
    $table->integer('priority')->default(0);
});

// ❌ 禁止
$table->string('amount'); // 已有数据的表上新增非空无默认字段会报错
```

### 删除字段安全流程（同 Django，两步走）

```
第一步：部署代码移除字段引用，确认线上无读写。
第二步：再部署迁移删除字段。
```

### 数据迁移

```php
public function up(): void
{
    // Schema 变更
    Schema::table('orders', function (Blueprint $table) {
        $table->string('status', 20)->default('pending');
    });

    // ✅ 数据回填在同一迁移内，或单独写一个迁移
    DB::table('orders')->whereNull('status')->update(['status' => 'pending']);
}

public function down(): void
{
    Schema::table('orders', function (Blueprint $table) {
        $table->dropColumn('status');
    });
}
```

- `down()` 必须写，即使只是 `dropColumn`，确保 `migrate:rollback` 不报错。
- 禁止在迁移文件中使用 Eloquent Model 类（有可能因 Model 变更导致迁移文件失效），优先使用 `DB::table()`。

### 执行前检查清单

- [ ] 新字段是否 `nullable` 或有 `default`？
- [ ] 是否本地执行过 `php artisan migrate`？
- [ ] 是否执行过 `php artisan migrate:rollback` 确认 `down()` 可执行？
- [ ] 删除字段是否已先移除所有代码引用？
- [ ] 数据迁移是否用 `DB::table()` 而非 Eloquent Model？
- [ ] `down()` 是否已实现？

---

## 生产迁移前通用 SOP

1. **在 staging / 测试库先跑一遍**，确认无报错。
2. **备份或确认有近期备份**（大表必须）。
3. **评估执行时间**：超过 10 秒的迁移需在低峰期或维护窗口执行。
4. **通知相关协作方**（如有联调接口依赖变更）。
5. 执行后立即检查服务日志，确认无新报错。

---

## 常见错误与处理

| 问题 | 原因 | 处理方式 |
|---|---|---|
| 新增 NOT NULL 字段迁移失败 | 无 default 且表中有存量数据 | 先加 nullable，再回填数据，再加约束 |
| RunPython 报 ImportError | 直接 import 了当前 Model | 改用 `apps.get_model()` |
| migrate:rollback 报错 | `down()` 未实现 | 补写 `down()` |
| 迁移卡死（大表锁） | 全表 DDL 锁 | 使用在线 DDL 工具或维护窗口执行 |
