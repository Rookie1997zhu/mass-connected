# MASS CONNECTED 平台开发完成清单

> 依据 [MASS CONNECTED 平台文档.md](MASS%20CONNECTED%20%E5%B9%B3%E5%8F%B0%E6%96%87%E6%A1%A3.md) 与 `project/` 目录 7 份需求书，以及开发路线图（P0–P9）整理。  
> 更新日期：2026-07-07（含 P9 平台化改版 + 纸盒包装生成器 paper_box）

## 阶段总览

- [x] **P0** 基础设施与脚手架
- [x] **P1** 后端基础层与鉴权
- [x] **P2** 后端业务模块 API
- [x] **P3** 管理后台 admin
- [x] **P4** 官网前台 frontend
- [x] **P4+** 首页重设计与设计系统
- [x] **P5** 集成联调与验收
- [x] **P6** RFQ 平台化改造（退役电商，新增按工艺在线询价）
- [x] **P7** 制造撮合平台 + 自营商城（重建 catalog/order）
- [x] **P8** 个人/企业会员体系 + 生产订单
- [x] **P9** MASS CONNECTED 平台化改版（供应商指派制 + 简单/详细报价 + 积分 + MY PAGE + 项目进度 + 合同/付款 + 通知 + PDF）

> **说明**：P7/P8 中「供应商自助入驻 + 公开需求大厅抢单 + 单层报价直达客户 + 生产订单」等能力已在 **P9 改版**，相关旧条目已按新模型更新，历史保留不再适用的部分见各节标注。

---

## P0 基础设施与脚手架

- [x] Monorepo 目录：`frontend/`、`admin/`、`backend/`、`caddy/`
- [x] `docker-compose.yml`、`.env.example`、`README.md`
- [x] Django + DRF 初始化，`INSTALLED_APPS` 不含 `django.contrib.admin`
- [x] 不注册 Django `/admin/` 路由
- [x] MySQL、Redis 容器与健康检查
- [x] Caddy 反向代理：`/` → frontend、`/admin` → admin、`/api/*` → backend、`/media/*` → 媒体卷
- [x] Caddy 使用标准 `caddy/Caddyfile`（修复 JSON 配置未加载导致 API 404 的问题）
- [x] Docker volumes：`mysql_data`、`media_data`、`caddy_data`、`caddy_config`
- [x] `docker compose up` 全栈启动验证通过
- [x] Django migrations 已生成并应用（accounts / catalog / content / inquiry / order）

---

## P1 后端基础层与鉴权

- [x] 统一响应包：`code` / `message` / `data` / `request_id`
- [x] 全局异常处理器
- [x] `request_id` 中间件 + 结构化日志
- [x] 错误码体系（`MODULE_SCENARIO_REASON`）
- [x] 分页基类（`items` + `pagination`）
- [x] `django-cors-headers` 跨域配置
- [x] 多语言字段策略（`I18nJSONField` JSON 字段）
- [x] `accounts` 模块：User + role（super_admin / operator / sales / member）
- [x] JWT 登录 / 注册 / 刷新 / 登出（simplejwt）
- [x] 权限类：`/api/public` / `/api/member` / `/api/admin`
- [x] `GET /api/health`（DB + Redis 连通检查）
- [x] 默认管理员：`create_default_admin`（admin@oem.co / Admin123!）

---

## P2 后端业务模块 API

> **注**：`catalog`（商品目录）与 `order`（购物车/订单）已在 **P6** 退役，下列条目保留为历史记录。当前业务模块以 `rfq`（询价）为核心，见 P6。

### catalog（已退役，见 P6）

- [x] Category / Product / ProductImage 模型与迁移
- [x] 公共读：`/api/public/categories`、`/api/public/products`
- [x] 管理端 CRUD：`/api/admin/categories`、`/api/admin/products`
- [x] 媒体上传：`/api/admin/media/upload`、商品图片上传

### content

- [x] Case / News / FAQ / Download / ContentPage 模型
- [x] 公共读：cases、news、faqs、downloads、content-pages
- [x] 管理端 CRUD：cases、news、faqs、downloads、content-pages

### inquiry

- [x] `POST /api/public/inquiries` 询盘提交
- [x] 管理端列表与状态流转

### order（已退役，见 P6）

- [x] CartItem / Order / OrderItem 模型
- [x] 会员购物车：`/api/member/cart`、`/api/member/cart/items`
- [x] 会员下单与 My Orders：`/api/member/orders`
- [x] 管理端订单管理与状态更新
- [x] 询盘转订单：`/api/admin/orders/from-inquiry`
- [x] 价格金额统一 **KRW 整数**

### 演示数据

- [x] `seed_demo_data`：默认分类、商品、内容页、案例、资讯、FAQ

---

## P3 管理后台 admin

- [x] Vue 3 + Vite + Element Plus + Pinia 脚手架
- [x] JWT 登录页与路由守卫
- [x] 基础布局与侧边导航
- [x] 商品 CRUD
- [x] 分类 CRUD
- [x] 订单列表与状态更新
- [x] 询盘列表与状态更新
- [x] 案例 CRUD
- [x] 资讯 CRUD
- [x] FAQ CRUD
- [x] 内容页 CRUD
- [x] 管理员账号 CRUD
- [x] 多语言字段编辑（ko / en 等 JSON 字段，基础版）
- [x] `npm run build` 构建通过
- [ ] 下载资源上传管理页（后端 API 已有，前端管理页待补）
- [ ] Refresh Token HttpOnly Cookie（当前 Access Token 存内存）

---

## P4 官网前台 frontend

- [x] Vue 3 + Vite + vue-i18n + Pinia 脚手架
- [x] 默认语言 **韩语（ko）**，支持 ko / zh / en / ja 切换
- [x] 封装请求层，对接真实 API（无 mock）
- [x] 公共布局与导航（含 sticky 顶栏、移动端 hamburger 菜单、多列页脚）
- [x] Home / About / Products（含详情）
- [x] Capabilities / OEM-ODM
- [x] Cases（含详情）/ News（含详情）
- [x] Support（Download / FAQ）
- [x] Contact 询盘表单 → `/api/public/inquiries`
- [x] Shop：商品列表 / 详情
- [x] 会员注册 / 登录
- [x] 购物车 / 结账 / My Orders
- [x] 未登录访问购物车 / 结账 / 订单 → 跳转登录页
- [x] `npm run build` 构建通过

---

## P4+ 首页重设计与设计系统

> 对应项目书 10.1 Home 首页、第 15 章 UI/视觉要求；审美方向：premium + industrial（黑白灰 + 深钢蓝）。

### 设计系统

- [x] 重写 `frontend/src/style.css`：颜色 / 间距 / 圆角 / 阴影 / 字体 token
- [x] 清理 Vite 模板残留（1126px 窄栏、紫色 `--accent`、`#next-steps` 等）
- [x] 全局可复用样式：`.container`、`.section`、`.btn`、`.card`、`.grid-*` 等
- [x] 更新 `frontend/src/App.vue` 使用新 token

### 导航与页脚（MainLayout）

- [x] Sticky 顶栏 + 毛玻璃背景
- [x] 桌面端完整导航（Home / Products / Capabilities / OEM-ODM / Cases / News / Shop / Contact）
- [x] 移动端 hamburger 抽屉菜单
- [x] 四列深色页脚 + 版权信息
- [x] 语言切换（ko / zh / en / ja）样式统一

### 首页八分区（HomeView，对应项目书 10.1）

- [x] **Hero**：大标题 + 副标题 + 双 CTA（Contact / Products）
- [x] **Hero 主视觉**：纯 CSS/SVG 蓝图网格几何风（无图片依赖）
- [x] **Hero 指标条**：月产能 / 出口市场 / 制造经验 / 质量认证
- [x] **Company Intro**：公司能力简介 + About 入口
- [x] **Featured Products**：核心产品卡片（接 API，含 loading / 空态）
- [x] **Capabilities Preview**：产线 / 品控 / 认证三卡片
- [x] **OEM-ODM Services Preview**：代工服务摘要 + 三步流程
- [x] **Cases Preview**：成功案例卡片（接 API）
- [x] **News Preview**：最新资讯卡片（接 API）
- [x] **CTA Banner**：引导 Contact / Shop

### 多语言与响应式

- [x] `i18n/index.js` 新增 `home` 文案命名空间（ko / zh / en / ja）
- [x] 扩展 `nav` / `footer` 文案 key
- [x] 多语言字段按当前 locale 读取，兜底 ko
- [x] 响应式三档：Desktop / Tablet / Mobile（Hero 非对称、卡片单列、导航折叠）
- [x] Hero 入场动效 + 卡片 hover 过渡（克制）
- [x] `npm run build` 验证通过

### 部署更新

- [x] `docker compose up -d --build frontend caddy` 已执行
- [x] 六服务正常运行，官网与 API 可访问

---

## P5 集成联调与验收

### 已验证流程

- [x] `GET /api/health` 返回 healthy（database / redis ok）
- [x] 管理员登录 API（admin@oem.co）
- [x] 会员注册 → 加购 → 下单完整闭环（KRW 整数金额正确）
- [x] 询盘提交并在后台可查看
- [x] Caddy 路由：官网 / 管理后台 / API 均可访问
- [x] 全栈 Docker Compose 六服务正常运行
- [x] 首页重设计部署后验证：http://localhost/ 可访问，`/api/health` 正常

### 项目书第 29 章验收标准

- [x] 项目书已切换到 OEM 官网 + 自研电商/管理后台方案
- [x] 前端已清除虚拟 mock 数据，对接真实接口
- [x] 前端多语言 UI 切换，**官网默认韩语**
- [x] `backend` Django + DRF 基线，Django Admin 已禁用
- [x] Vue Admin 可登录并维护内容、商品、订单、询盘等基础数据
- [x] Shop 会员注册 / 登录；未登录购物车 / 结账 / 订单正确引导登录
- [x] JWT 登录流程可用；越权返回 401 / 403
- [x] Contact 询盘表单可提交并在后台查看
- [x] 电商会员购物车 / 下单 / My Orders 完整闭环（不含在线支付、不含匿名下单）
- [x] 商品价格与订单金额以 KRW 整数存储与展示
- [x] 列表 API 支持分页，响应含 `items` + `pagination`
- [x] 错误响应返回稳定 `code`
- [x] `GET /api/health` 可用，响应含 `request_id`
- [x] `docker-compose.yml` 描述完整服务拓扑（含 Caddy）
- [x] MySQL、Redis、Backend、Frontend、Admin、Caddy 均有容器配置
- [x] 本地启动说明（README.md）
- [x] 首页首屏突出公司实力与 CTA，工业科技感视觉（项目书 15 章）
- [x] 全站全宽布局，无 Vite 模板 1126px 窄栏限制
- [ ] 媒体文件 `/media/` 端到端上传访问（API 已有，管理端上传 UI 待完善）
- [ ] 生产域名 Caddy 自动 HTTPS（本地 `:80` 已验证，生产域名待部署）

---

## P6 RFQ 平台化改造

> 历史阶段（RFQ 平台化改造）。采用 **A 路线（单公司 RFQ）+ B-ready 架构**，服务按**制造工艺**组织；退役零售商城与产品目录。当前平台形态见 [MASS CONNECTED 平台文档.md](MASS%20CONNECTED%20%E5%B9%B3%E5%8F%B0%E6%96%87%E6%A1%A3.md)。  
> 关键决策：工艺分类**下线（软删除）而非物理删除**；保留会员体系，**游客必须注册登录后方可提交询价**。

### 后端：新增 rfq 模块

- [x] `apps/rfq` 应用：注册 `INSTALLED_APPS`、`core/urls.py`，迁移已生成并应用
- [x] `ServiceCategory` 模型：树形 `parent`、`name`（I18nJSONField）、`slug`、`icon`、`sort_order`、`is_active`（软删除）
- [x] `RFQ` 模型：`rfq_no`、`buyer`、联系人信息、`service_category`、规格字段（材料/数量/公差/表面处理/交期/预算/币种）、`status`、`scope`（B-ready 预留）
- [x] `RFQAttachment` 模型：图纸/STEP/PDF 附件（类型与 20MB 大小校验）
- [x] `Quote` 模型：`supplier`、报价金额、交期、有效期、状态（B-ready 预留多供应商）
- [x] 公共读：`GET /api/public/service-categories`（仅返回启用项）
- [x] 会员端：`/api/member/rfqs`（提交/列表，`IsMemberRole`）、详情、附件上传、`quotes/<id>/accept` 接受报价
- [x] 管理端：`/api/admin/service-categories`（列表/创建/改）、`/api/admin/rfqs`（列表/详情，支持 status 筛选）、`/api/admin/rfqs/<id>/status`、`/api/admin/rfqs/<id>/quotes`、`/api/admin/quotes/<id>`
- [x] 未登录访问会员询价接口返回 **401**；越权按角色返回 401/403
- [x] 列表接口统一 `items` + `pagination`；响应统一 `code`/`message`/`request_id`

### 后端：退役电商

- [x] 卸载 `catalog`、`order` 迁移并从 `INSTALLED_APPS`、`core/urls.py` 移除
- [x] 通用媒体上传 `AdminMediaUploadView` 迁移至 `content` 应用（`/api/admin/media/upload` 保留）
- [x] 重写 `seed_demo_data`：播种 6 大工艺分类（CNC/钣金/注塑/压铸/表面处理/3D 打印）+ 内容演示数据
- [x] 删除 `apps/catalog`、`apps/order` 目录；`/api/public/products` 等旧接口返回 404

### 管理后台：改造

- [x] 侧边导航移除「商品/分类/订单」，删除对应视图与 API 调用
- [x] 新增「工艺分类」页：树形 CRUD、`MultiLangInput` 名称、父级选择、启用/停用（软删除）
- [x] 新增「询价单」页：列表 + 状态筛选 + 分页，详情弹窗查看规格/附件/报价
- [x] 询价单详情内可**变更状态**与**创建/更新报价**
- [x] i18n 三语（ko/zh/en）补齐 `serviceCategories`、`rfqs` 文案
- [x] `npm run build` 构建通过

### 官网前台：改造

- [x] 移除 `/products`、`/shop/*` 路由与所有商城/商品视图
- [x] 账户路由迁移到顶层：`/login`、`/register`，未登录访问询价 → 跳转 `/login?redirect=...`
- [x] 新增 RFQ 三步向导 `/rfq/new`（选工艺→填规格→联系方式），支持 `?category=slug` 预选
- [x] 新增「我的询价单」列表 `/my/rfqs` 与详情 `/my/rfqs/:id`（附件下载、报价列表、接受报价）
- [x] 首页「Featured Products」替换为「按工艺在线询价」，能力页对接工艺分类
- [x] 导航/页脚 CTA 改为「在线询价」，移除 products/shop
- [x] i18n 四语（ko/zh/en/ja）补齐 `rfq`、`myRfqs`、`account`、`processes` 文案
- [x] `npm run build` 构建通过

### 部署与验收

- [x] 重建镜像与容器（`--build --renew-anon-volumes` 修复 node_modules 卷缓存，wangEditor/dompurify 生效）
- [x] `migrate` + `seed_demo_data` 执行成功，六服务正常运行
- [x] `GET /api/health` healthy（database/redis ok）
- [x] **浏览器端到端**：注册 → 登录 → RFQ 向导（预选 CNC）→ 提交 → 详情页显示 submitted
- [x] **管理端浏览器**：登录 → 工艺分类页（6 项）→ 询价单列表（含前台提交单 + 状态筛选）
- [x] **API 验证**：公共工艺分类、会员登录列表（租户隔离）、管理端列表筛选、401 守卫、旧接口 404

---

## P7 制造撮合平台 + 自营商城

> 在 P6 基础上激活 **阶段 B（多供应商撮合）** 核心能力，并**重建自营电商**（catalog + order）。导航重构为平台化：**制造报价 / 商城 / 关于**。

### 后端：工厂角色与入驻审核

- [x] `User.role` 新增 `factory`；`FactoryProfile`（公司名/地区/简介/工艺 M2M/审核状态）
- [x] `POST /api/factory/auth/register` 入驻申请（`is_active=false`，待审核）
- [x] 前台登录支持 `member` + `factory`；待审核返回 `FACTORY_PENDING_REVIEW`
- [x] `IsFactoryRole` 权限；`GET/PATCH /api/admin/factories` 管理员审核通过/拒绝

### 后端：需求大厅与工厂报价（激活 B 路线）

> ⚠️ **已被 P9 改版取代**：原「公开需求大厅 + 工厂自由抢单」模式已下线，改为「管理员指派制」。以下条目保留为历史，不再作为当前行为，详见 P9「供应商体系改版」与「详细报价改版」。

- [x] ~~RFQ `scope=public|internal`~~ → RFQ 由管理员指派，不再依赖公开抢单
- [x] ~~工厂端 `/api/factory/rfqs` 抢单式报价~~ → 改为 `/api/supplier/quote-requests`（仅见被指派）
- [x] `QuoteSerializer` 增加 `supplier_name` / `supplier_type`（platform/factory，保留）
- [x] ~~买家可接受任意来源报价~~ → 改为「平台汇总方案 A/B/C，客户仅确认平台可见方案」

### 后端：重建 catalog + order

- [x] 重建 `apps/catalog`：`Category` / `Product` / `ProductImage`；公共读 + 管理端 CRUD
- [x] 重建 `apps/order`：`CartItem` / `Order` / `OrderItem`；会员购物车/下单/我的订单 + 管理端订单
- [x] `seed_demo_data` 扩展：2 商品分类 + 2 演示商品
- [x] 迁移已生成并应用

### 管理后台

- [x] 新增「工厂管理」：列表 + 审核通过/拒绝
- [x] 重建「商品分类 / 商品 / 订单」管理页 + API + 侧边栏 + i18n
- [x] RFQ 详情报价列表显示报价来源（platform/factory）

### 官网前台

- [x] 导航重构：**制造报价**（发布请求/寻找需求/合作伙伴）+ **商城**（产品分类）+ **关于**（能力/OEM-ODM/案例/资讯/支持/联系）
- [x] 账户区按角色：member→我的RFQ/我的订单/购物车；factory→需求大厅/我的报价（**P8 已演进**，见 P8 节）
- [x] 工厂页：入驻申请 `/partners`、需求大厅 `/demand-hall`、需求详情+报价、我的报价 `/factory/quotes`（**P8**：`/partners` 改为企业目录，入驻合并至企业注册）
- [x] RFQ 向导增加「公开到需求大厅」开关；我的 RFQ 详情显示多供应商报价来源
- [x] 商城：分类列表 `/shop`、商品详情、购物车/结算/我的订单
- [x] i18n 四语补齐导航/工厂/大厅/入驻/商城文案

### 部署与验收

- [x] `migrate` + `seed_demo_data`；`GET /api/health` healthy
- [x] `frontend` + `admin` `npm run build` 通过
- [x] 端到端冒烟：公开 RFQ → 工厂入驻审核 → 工厂报价 → 买家接受；商城加购下单闭环

---

## P8 个人/企业会员体系 + 生产订单

> 对应 [.cursor/plans/会员类型拆分方案_79d8b7c1.plan.md](.cursor/plans/会员类型拆分方案_79d8b7c1.plan.md)。前台会员统一 `role=member`，以 `member_type` 区分个人/企业；企业注册即含入驻申请，审核通过后同一账号具备买方 + 卖方双能力；接受工厂报价后生成生产订单，卖方需显式接单。

### 后端：会员类型与权限

- [x] `User.member_type`：`individual`（个人会员）/ `enterprise`（企业会员）
- [x] 数据迁移：存量 `role=member` → `individual`；存量 `role=factory` → `member` + `enterprise`（保留 `FactoryProfile`）
- [x] `IsBuyerRole`：所有前台 `role=member` 用户（个人 + 企业）可使用买方 API
- [x] `IsSupplierRole`：企业会员且 `FactoryProfile.status=approved`（兼容 legacy `role=factory`）
- [x] `UserSerializer` 增加 `member_type`、`factory_profile` 摘要
- [x] 合并注册：`POST /api/member/auth/register` 支持 `member_type`；企业注册创建 `FactoryProfile(pending)` 并返回 JWT
- [x] 企业会员 **pending 可登录** 使用买方能力；卖方 API 未审核返回 403
- [x] `POST /api/factory/auth/register` 废弃（返回 **410** `FACTORY_REGISTER_DEPRECATED`）

### 后端：公开需求大厅与入驻企业目录

> ⚠️ **部分已被 P9 改版取代**：需求大厅由「供应商自由抢单入口」降级为内部/可选展示；供应商报价改为指派制。

- [x] `GET /api/public/demand-hall`、`GET /api/public/demand-hall/{id}`（AllowAny，保留为展示，非抢单入口）
- [x] `GET /api/public/partners`（AllowAny，已审核 `FactoryProfile`，脱敏展示企业名/地区/工艺/简介）
- [x] ~~工厂报价 API `/api/factory/*`~~ → P9 改为 `/api/supplier/quote-requests`（指派制，`IsSupplierRole`）

### 后端：生产订单（ProductionOrder）

> 🔄 **P9 演进**：`ProductionOrder` 保留为报价确认后的成交凭据，并在付款确认后**升级/触发**生成 `Project`（项目/生产进度体系，见 P9）。

- [x] `ProductionOrder` 模型：`order_no`、关联 RFQ/Quote/buyer/supplier、状态机（`pending_confirm` → `confirmed` → `in_production` → `completed` / `cancelled`）
- [x] 接受报价（`POST .../quotes/{id}/accept`）在事务中创建 `ProductionOrder(pending_confirm)`（平台报价无 supplier 时返回错误）
- [x] 买家：`GET /api/member/production-orders`、详情
- [x] 卖方：`GET /api/supplier/production-orders`、`POST .../confirm`、`POST .../reject`
- [x] 管理端：`GET/PATCH /api/admin/production-orders`
- [x] 迁移：`accounts.0003_user_member_type_migrate_factory`、`rfq.0002_productionorder`

### 管理后台

- [x] 工厂管理列表增加 **会员类型**（`member_type`）列
- [x] 新增 **生产订单** 页（`/admin/production-orders`）：列表、状态筛选、运营改状态
- [x] i18n 补齐 `productionOrders`、`factories.memberType`（ko/zh/en）

### 官网前台

- [x] 注册页 Tab：**个人会员** / **企业会员**（企业含公司名/地区/简介/工艺多选）
- [x] `/partners` 改为 **入驻企业目录**（调用 `/api/public/partners`），移除入驻申请表单，引导企业会员注册
- [x] 需求大厅 `/demand-hall` 保留展示；~~公开报价表单~~ → P9 改为供应商在「我的报价请求」中对被指派项目报价
- [x] ~~RFQ 向导默认 `scope=public`~~ → P9 改为管理员指派供应商
- [x] Auth Store：`isBuyer` / `isEnterprise` / `isSupplier` / `isFactoryPending`；路由 `requiresSupplier` 守卫
- [x] 买家生产订单：`/my/production-orders`、详情；接受报价后提示并跳转
- [x] 卖方接单：`/supplier/orders`（确认/拒绝待接单生产订单）
- [x] 导航：需求大厅、生产订单、接单管理（卖方）；审核中显示「入驻审核中」
- [x] i18n 四语补齐 `register.*`、`partners.directory*`、`productionOrder.*`、`nav.partnersDirectory` 等

### 部署与验收

- [x] `docker compose` 迁移已应用（`accounts.0003`、`rfq.0002`）；`backend` 重启后 `manage.py check` 通过
- [x] 六服务（mysql/redis/backend/frontend/admin/caddy）重启后正常运行
- [x] `frontend` + `admin` 本地 `npm run build` 通过（2026-07-03）
- [ ] 浏览器端到端：个人注册 → RFQ → 企业报价 → 接受 → 生产订单 → 卖方 confirm（待人工复测）
- [ ] 浏览器端到端：企业注册 → 后台审核 → 同一账号买方+卖方能力（待人工复测）

---

## P9 MASS CONNECTED 平台化改版

> 对应 [MASS CONNECTED 平台文档.md](MASS%20CONNECTED%20%E5%B9%B3%E5%8F%B0%E6%96%87%E6%A1%A3.md) 与 `project/` 7 份需求书。将平台改造为「管理员居中运营的制造服务撮合平台」：供应商指派制、双通道报价、方案 A/B/C、积分、MY PAGE、项目进度、合同/付款、通知、PDF。

### 供应商体系改版（指派制）

- [x] 供应商账号由**管理员建号**（`/api/admin/suppliers` 列表/创建），停用供应商自助注册
- [x] `QuoteRequest` 指派记录模型（`request_no`、rfq、supplier、status、deadline、admin_note、is_urgent、created_by），`unique_together=(rfq, supplier)`
- [x] 管理端指派：`POST /api/admin/rfqs/{id}/assign`、`GET /api/admin/rfqs/{id}/quote-requests`
- [x] 供应商端：`GET /api/supplier/quote-requests[/{id}]`、`POST .../quotes`（仅见被指派项目）
- [x] 前台需求大厅降级为展示；`DemandDetailView` 移除公开抢单表单，引导供应商到「我的报价请求」
- [x] admin 新增「供应商」页 + 侧边导航 + i18n；前台新增 `/supplier/quote-requests[/{id}]`

### 详细报价改版（方案 A/B/C + 加价）

- [x] `RFQ` 扩展 9.6 状态机：新增 `pending_review`/`assigned`/`comparing`/`customer_confirming`
- [x] `RFQ.markup_percent` 平台加价率；`PATCH /api/admin/rfqs/{id}/status` 支持同时更新状态与加价率
- [x] `Quote` 增加 `quote_request`、`is_customer_visible`、`plan_label`（A/B/C）
- [x] `CustomerPlanSerializer` / `MemberRFQDetailSerializer`：对客户加价、**隐藏供应商身份**，以方案卡片展示
- [x] 会员接受方案校验 `is_customer_visible`；接受后更新 `QuoteRequest` 状态并发通知
- [x] admin RFQ 详情：加价率编辑、指派供应商、Quote 方案标签与对客户可见开关
- [x] 前台 `MyRfqDetailView` 改为方案 A/B/C 卡片确认

### 简单报价引擎（simplequote）

- [x] `QuoteParam`（后台参数）、`SimpleQuote`（自动估价，inputs/result JSON、PDF、积分消耗）模型
- [x] `calculator.py` 参数驱动引擎：注塑模具 / 3D 打印 / PCB / 软件 / IC / **纸盒包装 paper_box**，含费用明细
- [x] 会员：`GET/POST /api/member/simple-quotes`、详情、`POST .../convert`（转详细报价，消耗积分）
- [x] 管理：`GET/POST /api/admin/quote-params`、`PATCH /api/admin/quote-params/{id}`
- [x] 前台 `/simple-quote` 动态表单 + 结果 + PDF 下载 + 转 RFQ；admin「报价参数」页 + i18n

### 纸盒包装生成器（paper_box）

- [x] 后端 `packaging.py`：`unfold_by_code` 权威展开（0201/0427/0713/0716）；内/外/制造尺寸换算
- [x] `calc_paper_box` + `build_paper_box_quotation_pdf`；`quote_type=paper_box`；币种 CNY + KRW 换算
- [x] `GET /api/packaging/fefco-catalog`（DB 驱动）；`DielineTemplate` 模型 + admin CRUD `/api/admin/dieline-templates`
- [x] 前端 `/packaging/box`：`BoxGeneratorView.vue` + `lib/packaging/*`（Maker.js 刀版引擎）
- [x] P0 盒型 0201/0427 详细刀版预览；0713/0716 展开轮廓预览；0201 CAD 标尺 + 点击编辑尺寸
- [x] 0201 圆角开槽、`npm run test:packaging` 几何断言；客户端 PDF / Illustrator (.ai) / DXF 导出
- [x] FEFCO 侧栏 hover/图钉折叠；MY PAGE 简单报价跳转 `/packaging/box`；i18n `packaging.*` 四语
- [x] admin「报价参数」类型下拉含 `paper_box`；admin「刀版模板」页 `/dieline-templates`

### 积分系统（points）

- [x] `PointWallet` / `PointTransaction` / `PointRule` / `RechargeOrder` 模型
- [x] `services.py`：`ensure_wallet` / `get_rule_amount` / `add_points` / `spend_points`（余额不足抛错）/ `grant_register_bonus`
- [x] 注册赠送积分（接入 `MemberRegisterView`）、报价消耗积分
- [x] 会员：钱包 / 流水 / 充值（`/api/member/points/*`）
- [x] 管理：积分规则、用户积分调整、充值人工确认（`/api/admin/points/*`）
- [x] admin「积分」页（规则 + 充值确认）+ 侧边导航 + i18n

### MY PAGE 个人中心（前台）

- [x] `/my` 统一个人中心：概览 / 简单报价 / 详细报价 / 项目 / 合同 / 付款 / 积分 / 通知 / 企业资料 / 账户设置 / 退出登录
- [x] 各标签按需拉取数据；新增会员 dashboard 聚合接口调用
- [x] i18n 四语补齐 `mypage.*`、`simpleQuote.*`、`quoteRequest.*`、`myRfqs.plans/plan/confirmPlan` 等

### 项目 / 生产进度（project）

- [x] `Project` / `ProjectStage` / `ProjectUpdate` / `ProjectTodo` / `ProjectIssue` 模型
- [x] `services.py`：`recalc_progress`、`create_project_from_production_order`（默认阶段 + 通知）
- [x] 会员：`GET /api/member/projects[/{id}]`、`POST .../todos/{id}/toggle`
- [x] 供应商：`GET /api/supplier/projects[/{id}]`、`POST .../updates`、`PATCH .../stages/{id}`、`POST .../issues`
- [x] 管理：`GET /api/admin/projects[/{id}]`、`POST .../todos`、`POST .../stages`
- [x] 前台 `MyProjectDetailView`（阶段/时间轴/进度/待办勾选）；admin「项目」页 + i18n

### 合同 / 付款（contract / payment）

- [x] `Contract` 模型（`contract_no`、关联 rfq/quote/production_order、buyer/supplier、amount、status、PDF）
- [x] `Payment` 模型（`payment_no`、contract、buyer、amount、method、status、proof）
- [x] 报价确认后在事务中生成 `ProductionOrder` → `Contract` → `Payment` 并发通知
- [x] 付款 V1 **人工确认**：会员上传凭证，管理员 `POST /api/admin/payments/{id}/confirm`，确认后触发转项目
- [x] 会员：`/api/member/contracts[/{id}]`、`/api/member/payments`、`POST .../{id}/proof`
- [x] admin「合同」「付款」页 + i18n

### 通知中心（notification）

- [x] `Notification` 模型（user、type、title、content、related_type、related_id、is_read）
- [x] `services.notify` 服务；接入报价确认、供应商指派、项目创建、付款、积分调整等事件
- [x] 会员：列表 / 未读数 / 标记已读 / 全部已读（`/api/member/notifications/*`）
- [x] MY PAGE 通知标签页

### PDF 基础设施

- [x] `requirements.txt` 引入 `reportlab>=4.2,<5`
- [x] `core/pdf.py`：`build_quotation_pdf` 通用 PDF 生成（简单报价书、合同）
- [x] 简单报价书、合同 PDF 落地 `/media/`，可下载

### 部署与验收（P9）

- [x] 6 个新 app 迁移已生成并应用（notification/points/simplequote/project/contract/payment + rfq 0003）
- [x] `manage.py check` 通过；`makemigrations --check` 无遗漏
- [x] `frontend` + `admin` `npm run build` 通过
- [x] 六服务重启后正常运行；`GET /api/health` healthy（database/redis ok）
- [x] 新接口路由冒烟：13 个新端点返回 401（鉴权拦截，非 404）
- [x] 端到端冒烟：注册→赠送积分→简单报价（PDF + 扣积分）→钱包扣减正确；3D 打印估价计算正确
- [x] 浏览器详细测试前端显示与样式（见测试报告）

---

## 本期明确不做（维持范围外）

- [ ] 在线支付接入
- [ ] 匿名下单 / 匿名购物车
- [ ] 多币种 / 多货币换算
- [ ] 云对象存储（MinIO / S3 / OSS）
- [ ] SEO 服务端渲染（SSR）
- [ ] 在线客服 / 实时聊天
- [ ] 生产级监控告警体系
- [ ] Django Admin

---

## 快速启动

```bash
cp .env.example .env
docker compose up --build -d
```

| 入口 | 地址 |
|------|------|
| 官网 | http://localhost/ |
| 管理后台 | http://localhost/admin/ |
| API 健康检查 | http://localhost/api/health |

**默认管理员**：`admin@oem.co` / `Admin123!`  
**会员注册**：`/register` 选择 **个人会员** 或 **企业会员**；注册即赠送积分，可在 `/simple-quote` 自动估价或 `/rfq/new` 提交详细询价，并在 `/my`（MY PAGE）跟踪报价、项目、合同、付款与积分。  
**供应商**：由管理员在后台「供应商」建号；供应商在 `/supplier/quote-requests` 对**被指派**的报价请求报价，不再公开抢单。
