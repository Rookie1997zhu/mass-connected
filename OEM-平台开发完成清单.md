# OEM 平台开发完成清单

> 依据 [OEM Manufacturing Company Website & Platform (Multi-language).md](OEM%20Manufacturing%20Company%20Website%20&%20Platform%20(Multi-language).md)、[RFQ 平台化演进方案.md](RFQ%E5%B9%B3%E5%8F%B0%E5%8C%96%E6%BC%94%E8%BF%9B%E6%96%B9%E6%A1%88.md) 与开发路线图（P0–P6）整理。  
> 更新日期：2026-07-02（含 P7 制造撮合平台 + 自营商城）

## 阶段总览

- [x] **P0** 基础设施与脚手架
- [x] **P1** 后端基础层与鉴权
- [x] **P2** 后端业务模块 API
- [x] **P3** 管理后台 admin
- [x] **P4** 官网前台 frontend
- [x] **P4+** 首页重设计与设计系统
- [x] **P5** 集成联调与验收
- [x] **P6** RFQ 平台化改造（退役电商，新增按工艺在线询价）
- [x] **P7** 制造撮合平台 + 自营商城（工厂入驻/需求大厅/多供应商报价 + 重建 catalog/order）

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

> 对应 [RFQ 平台化演进方案.md](RFQ%E5%B9%B3%E5%8F%B0%E5%8C%96%E6%BC%94%E8%BF%9B%E6%96%B9%E6%A1%88.md)。采用 **A 路线（单公司 RFQ）+ B-ready 架构**，服务按**制造工艺**组织；退役零售商城与产品目录。  
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

- [x] RFQ 提交支持 `scope=public|internal`（买家 opt-in 公开到需求大厅）
- [x] 工厂端：`GET /api/factory/rfqs`（公开需求列表，脱敏）、`GET /api/factory/rfqs/{id}`、`POST .../quotes`（`Quote.supplier=工厂`）、`GET /api/factory/quotes`
- [x] `QuoteSerializer` 增加 `supplier_name` / `supplier_type`（platform/factory）
- [x] 买家「我的 RFQ」可接受任意来源报价；接受后 RFQ→won

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
- [x] 账户区按角色：member→我的RFQ/我的订单/购物车；factory→需求大厅/我的报价
- [x] 工厂页：入驻申请 `/partners`、需求大厅 `/demand-hall`、需求详情+报价、我的报价 `/factory/quotes`
- [x] RFQ 向导增加「公开到需求大厅」开关；我的 RFQ 详情显示多供应商报价来源
- [x] 商城：分类列表 `/shop`、商品详情、购物车/结算/我的订单
- [x] i18n 四语补齐导航/工厂/大厅/入驻/商城文案

### 部署与验收

- [x] `migrate` + `seed_demo_data`；`GET /api/health` healthy
- [x] `frontend` + `admin` `npm run build` 通过
- [x] 端到端冒烟：公开 RFQ → 工厂入驻审核 → 工厂报价 → 买家接受；商城加购下单闭环

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
**会员注册**：通过 `/register` 注册后可在 `/rfq/new` 提交询价
