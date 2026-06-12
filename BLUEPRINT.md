# BLUEPRINT - M2 库存权限三层系统

## 1. 项目定位

- 项目编号：`M2`
- 路线：改造
- 来源：https://github.com/akashroshan135/inventory-management （改造）
- 技术栈：后端 Django，前端 Django 模板 + 图表（Chart.js），数据库 SQLite/MySQL
- 识别到的框架信号：Django
- 入口页/入口命令：manage.py
- 业务域：Django 库存系统的角色表、后端装饰器、模板显隐和部门图表范围

本蓝图由确定性脚本生成，作为后续实现唯一事实来源。实现阶段仍需读取 `plan.md`、`generation-spec.md` 和原仓库关键文件，但不得绕开本蓝图锁定的数据模型、状态机、端点、权限和运行约束。

## 2. plan.md 锁定的 0 分结构

- 主靶子：**逻辑链断裂=0分** —— 权限三层（DB Role 表 + 后端装饰器 + 前端模板 if + 路由守卫）任一未联动则越权或入口残留
- 副靶子：**UI 未适配=0分** —— 无权限的按钮/菜单必须在页面上消失，仅后端拦截不算完成
- 第三靶子：**隐含联动遗漏=0分** —— 图表数据需随权限范围（部门）实时刷新

实施事项摘要：

- [ ] 阅读 `code-map.md`，定位现有视图与 URL 配置
- [ ] 新增 `Role` 模型（admin / manager / staff）+ 用户-角色关联
- [ ] 后端：自定义权限装饰器/Mixin，按角色限制增删改端点
- [ ] 前端：模板按角色 `{% if %}` 控制按钮/菜单显隐
- [ ] 图表：按当前用户部门聚合并实时刷新（非全量）
- [ ] 补 Dockerfile 与 fixtures 种子
- [ ] 跑 jz-docker-env 验证

闭环验证场景：

1. 正向：staff 登录 → 删除按钮在页面**不可见**，且直接调删除端点返回 403
2. 反向：manager 仅能操作本部门数据，跨部门返回 403 且图表只统计本部门
3. 联动：admin 修改某用户部门后，该用户图表统计范围随之变化

## 3. 原仓库/源码地图理解

源码地图摘要：

未发现 repo/code-map.md，脚本使用 plan.md 与仓库文件信号生成蓝图。

当前 repo 文件信号（截断）：

```text
.gitignore
.jz-clone-complete
.jz-handoff/HANDOFF.md
.jz-source.json
.jz-workflow-state.json
README.md
core/__init__.py
core/asgi.py
core/settings.py
core/urls.py
core/wsgi.py
homepage/__init__.py
homepage/apps.py
homepage/static/bootstrap/bootstrap.min.css
homepage/static/bootstrap/bootstrap.min.js
homepage/static/bootstrap/jquery-3.3.1.slim.min.js
homepage/static/bootstrap/popper.min.js
homepage/static/css/bill.css
homepage/static/css/dialogbox.css
homepage/static/css/main.css
homepage/static/css/sidebar.css
homepage/static/js/Chart.min.js
homepage/static/js/dialogbox.js
homepage/static/js/jquery-3.2.1.slim.min.js
homepage/templates/about.html
homepage/templates/base.html
homepage/templates/home.html
homepage/templates/login.html
homepage/templates/logout.html
homepage/tests.py
homepage/urls.py
homepage/views.py
inventory/__init__.py
inventory/admin.py
inventory/apps.py
inventory/filters.py
inventory/forms.py
inventory/models.py
inventory/templates/delete_stock.html
inventory/templates/edit_stock.html
inventory/templates/inventory.html
inventory/tests.py
inventory/urls.py
inventory/views.py
manage.py
requirements.txt
transactions/__init__.py
transactions/admin.py
transactions/apps.py
transactions/forms.py
transactions/models.py
transactions/templates/bill/bill_base.html
transactions/templates/bill/purchase_bill.html
transactions/templates/bill/sale_bill.html
transactions/templates/purchases/delete_purchase.html
transactions/templates/purchases/new_purchase.html
transactions/templates/purchases/purchases_list.html
transactions/templates/purchases/select_supplier.html
transactions/templates/sales/delete_sale.html
transactions/templates/sales/new_sale.html
transactions/templates/sales/sales_list.html
transactions/templates/suppliers/delete_supplier.html
transactions/templates/suppliers/edit_supplier.html
transactions/templates/suppliers/supplier.html
transactions/templates/suppliers/suppliers_list.html
transactions/tests.py
transactions/urls.py
transactions/views.py
```

改造/生成边界：

- 最小侵入改造：保留原仓库目录、认证、模板和主要入口；禁止拆成全新的 backend/frontend 两套项目，禁止改写无关业务区域。
- README.md、依赖文件、seed/fixtures 应补齐；Dockerfile、docker-compose.yml、完整测试体系不是当前开发阶段的硬性交付，除非 plan.md 明确要求或仓库现状强依赖。
- 真实业务代码不得出现 demo/tutorial/example/sample/foo/bar/test_only 等红线词。

## 4. 完整数据模型

核心实体：`UserRole`

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | integer/bigint | PRIMARY KEY, NOT NULL |
| `status` | varchar/enum | NOT NULL, 合法值 `active` / `suspended` / `revoked` |
| `created_at` | datetime | NOT NULL |
| `updated_at` | datetime | NOT NULL |
| `created_by/requested_by` | integer | NOT NULL, FK users.id 或原仓库用户表 |
| `approved_by/reviewed_by` | integer | NULL, FK users.id |
| `deleted_at` | datetime | NULL, 软删除和恢复的双向操作口径 |

DDL/迁移约束草案：

```sql
CREATE TABLE userrole (
  id INTEGER PRIMARY KEY,
  status VARCHAR(32) NOT NULL,
  created_by INTEGER NOT NULL,
  approved_by INTEGER NULL,
  deleted_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  CONSTRAINT ck_userrole_status CHECK (status IN ('active', 'suspended', 'revoked'))
);
CREATE INDEX idx_userrole_status ON userrole(status);
```

M 系列按原仓库数据库方言落地：Django 用 migration，Laravel 用 migration，PHP 原生用 SQL 文件，Flask 用模型/迁移或初始化 SQL。

关联实体：
| 1 | `User` |
| 2 | `Department` |
| 3 | `Role` |
| 4 | `UserRole` |
| 5 | `Stock` |
| 6 | `Transaction` |


通用业务校验：

- 所有数量、金额、比例字段必须有非负、上限或精度校验。
- 外键必须指向真实业务实体，删除策略需明确为 RESTRICT、CASCADE 或软删除。
- 状态字段 `status` 是业务闭环的唯一状态源，页面徽标、统计聚合和后端可操作按钮都必须来自同一状态。
- 审计字段必须记录操作者与时间，便于测试定位非法跳转和越权操作。

## 5. 状态机与 transition() 契约

合法流转表：

| 当前状态 | 操作 | 目标状态 | 副作用 |
|---|---|---|---|
| `active` | `grant_role` | `suspended` | 校验角色、业务前置条件，通过后写入审计日志 |
| `suspended` | `revoke_role` | `revoked` | 校验角色、业务前置条件，通过后写入审计日志 |
| 任意终态 | 非法操作 | 保持原状态 | 拒绝，返回 403/409 或原仓库 msg-d/redirect |

`transition(actor, target, action, payload)` 契约：
- 统一读取当前 `status`，按合法流转表判断。
- 非法跳转必须拒绝，不允许部分写入。
- 通过后在同一事务中更新主表、审计字段、统计或库存/预算/台账副作用。
- 对应测试必须覆盖至少一个非法跳转、一个正向闭环、一个双向回退。


## 6. 端点契约

| method | path | 请求字段 | 响应/跳转 | 权限 | 错误 |
|---|---|---|---|---|---|
| GET | `/` 或入口页 | 无 | 原仓库首页/列表页 | 登录用户 | redirect/login |
| POST | 原仓库路由 `grant_role` | id + 表单字段 | redirect 或 JSON | 角色矩阵允许者 | 403/redirect/msg-d |
| POST | 原仓库路由 `revoke_role` | id + 表单字段 | redirect 或 JSON | 角色矩阵允许者 | 403/redirect/msg-d |
| POST | 原仓库路由 `guard_delete` | id + 表单字段 | redirect 或 JSON | 角色矩阵允许者 | 403/redirect/msg-d |
| POST | 原仓库路由 `department_chart` | id + 表单字段 | redirect 或 JSON | 角色矩阵允许者 | 403/redirect/msg-d |
| POST | 原仓库路由 `change_department` | id + 表单字段 | redirect 或 JSON | 角色矩阵允许者 | 403/redirect/msg-d |
| GET | 原仓库统计/图表端点 | 部门/日期范围 | 按部门过滤后的库存数量、流水数量、图表数据 | 管理/主管角色 | 403 |

统一约定：

- G 系列 REST API 使用统一响应包裹：`{"code":0,"data":...,"message":"ok"}`，错误时 code 非 0。
- M 系列按原仓库风格实现，可能是 PHP 页面、Django view、Flask route、Laravel controller 或 Livewire action；必须写清 method、path、POST 字段、跳转或 JSON 响应。
- 所有写操作必须校验 CSRF/session/token 和角色。

## 7. 权限矩阵

| 角色 | 查看 | 创建/提交 | 审批/管理 | 删除/恢复/回退 | 统计 |
|---|---|---|---|---|---|
| `admin` | 是 | 是 | 是 | 是 | 是 |
| `manager` | 是 | 是 | 是 | 按业务范围 | 是，限制范围 |
| `staff` | 仅本人/本范围 | 是 | 否 | 否 | 仅个人/本范围 |

权限实现要求：
- DB/模型层必须有 role 或 user-role 关联。
- 后端必须在装饰器、依赖注入、中间件或控制器入口拒绝越权。
- 前端必须用 router.beforeEach、模板 if、v-if 或菜单判断隐藏入口。
- 越权拒绝行为：原仓库拒绝方式：403 或 page_require_level/redirect/session->msg('d')，模板入口同步隐藏。
- 关键操作：`grant_role`, `revoke_role`, `guard_delete`, `department_chart`, `change_department`。


## 8. 依赖与精确版本

- 后端：按 `Django` 固定依赖版本；Python 项目写 `requirements.txt`，PHP/Laravel 写 `composer.json`，Node 前端写 `package.json`。
- 前端：`Django 模板 + Chart.js`；Vue 项目必须有 `vite`、路由、状态管理/API 层；模板项目必须在模板中显隐按钮与状态徽标。
- 数据库：`SQLite/MySQL`；迁移和种子数据必须可重复执行。
- 基础验证：如需补测试，只保留最小可运行、最有信号的验证；Python 优先 pytest/Django TestCase，PHP/Laravel 优先 PHPUnit，前端不强制自动化测试，只需保证最基本的可验证入口与构建信号。

## 9. 端口、运行与基础验证

保留原仓库运行方式，入口页/入口命令为 manage.py；如需本地启动，沿用原技术栈最直接方式；当前开发阶段不要求补 Docker 封装。

如后续需要容器化，可参考 plan.md 中的 Docker 方案；本 workflow 当前阶段不要求实现或启动该方案：

- 原项目可能无 Dockerfile，需新建：`python:3.11` + Django runserver/gunicorn
- 端口：Web 8000
- 启动：migrate → loaddata fixtures → runserver

运行要求：

- README 写清安装、启动、基础验证、账号和验证路径。
- `.env.example` 若项目确实需要，再补最小必要配置；不要求为了本轮开发额外构建完整部署体系。
- 验证目标是确认新增逻辑没有明显 bug；优先使用轻量命令、最小数据和局部路径，不做深度、全面测试。

## 10. 目录结构与可修改范围

```text
.gitignore
.jz-clone-complete
.jz-handoff/HANDOFF.md
.jz-source.json
.jz-workflow-state.json
README.md
core/__init__.py
core/asgi.py
core/settings.py
core/urls.py
core/wsgi.py
homepage/__init__.py
homepage/apps.py
homepage/static/bootstrap/bootstrap.min.css
homepage/static/bootstrap/bootstrap.min.js
homepage/static/bootstrap/jquery-3.3.1.slim.min.js
homepage/static/bootstrap/popper.min.js
homepage/static/css/bill.css
homepage/static/css/dialogbox.css
homepage/static/css/main.css
homepage/static/css/sidebar.css
homepage/static/js/Chart.min.js
homepage/static/js/dialogbox.js
homepage/static/js/jquery-3.2.1.slim.min.js
homepage/templates/about.html
homepage/templates/base.html
homepage/templates/home.html
homepage/templates/login.html
homepage/templates/logout.html
homepage/tests.py
homepage/urls.py
homepage/views.py
inventory/__init__.py
inventory/admin.py
inventory/apps.py
inventory/filters.py
inventory/forms.py
inventory/models.py
inventory/templates/delete_stock.html
inventory/templates/edit_stock.html
inventory/templates/inventory.html
inventory/tests.py
inventory/urls.py
inventory/views.py
manage.py
requirements.txt
transactions/__init__.py
transactions/admin.py
transactions/apps.py
transactions/forms.py
transactions/models.py
transactions/templates/bill/bill_base.html
transactions/templates/bill/purchase_bill.html
transactions/templates/bill/sale_bill.html
transactions/templates/purchases/delete_purchase.html
transactions/templates/purchases/new_purchase.html
transactions/templates/purchases/purchases_list.html
transactions/templates/purchases/select_supplier.html
transactions/templates/sales/delete_sale.html
transactions/templates/sales/new_sale.html
transactions/templates/sales/sales_list.html
transactions/templates/suppliers/delete_supplier.html
transactions/templates/suppliers/edit_supplier.html
transactions/templates/suppliers/supplier.html
transactions/templates/suppliers/suppliers_list.html
transactions/tests.py
transactions/urls.py
transactions/views.py
```

实现约束：

- G 系列必须建立 backend/ 与 frontend/，前后端通过 `/api` 交互。
- M 系列必须保留原仓库主体结构，只在模型/迁移/路由/模板/服务/基础验证必要位置改造。
- 原认证、菜单、布局、数据库连接、入口文件尽量复用；必要修改需小而清晰。

## 11. 种子数据规格

- 账号：至少 3 个角色账号，用户名与密码写入 README。
- 业务数据：覆盖 `active`, `suspended`, `revoked` 各状态。
- 统计数据：能让 `按部门过滤后的库存数量、流水数量、图表数据` 在页面或端点中看见变化。
- 时间字段：使用 2026 年附近的近期待办、历史完成和未来计划数据，避免全部落在久远年份。

## 12. 鉴权方案

- 登录后保存 session/token，后端每个受保护端点读取当前用户。
- 角色来自 DB/模型，不允许只在前端硬编码。
- 后端鉴权位于依赖注入、decorator、middleware、controller guard 或 `page_require_level` 入口。
- 前端按 role 和业务范围控制菜单、按钮、路由入口；越权直接调用后端仍必须被拒绝。

## 13. 基础验证与交付验收

基础验证至少要覆盖核心高风险路径，但以“发现明显 bug”为目标，不追求深度、全面覆盖。可使用最小单测、轻量集成测试、smoke 脚本或少量命令行验证：

1. 状态机非法跳转被拒绝，`status` 不变。
2. 关键双向操作或反向回退至少抽查一个，确认核心数据能回补或回退。
3. 角色越权返回 403 或原仓库拒绝方式，且页面入口隐藏。
4. 一条主流程 happy path 能从初始状态推进到终态。
5. 统计聚合只做最小抽查，确认关键数字会随核心业务操作变化：按部门过滤后的库存数量、流水数量、图表数据。

额外约束：

- 不要求前端自动化、性能压测、长链路回归、全量矩阵测试。
- 不要求为了验证而引入 Docker、docker-compose、浏览器自动化或额外复杂环境。
- 若环境依赖受限导致无法执行某项验证，必须在 README 或交付报告中明确记录原因与风险。

模拟质检 grep 锚点：

- `status`
- `transition`
- `403` 或 `page_require_level` / permission decorator
- `stats` / `aggregate` / `GROUP BY` / 图表数据
- 状态徽标 class 或模板条件渲染
