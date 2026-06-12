# 库存权限三层系统

这是一个基于原仓库改造的 Django 库存系统，保留了 `manage.py` 启动方式、Django 模板页面和原有库存/采购/销售主流程，在原目录结构内补了角色表、部门范围、状态机守卫、双向回退和统计看板。

## 本次改造内容

- 角色与部门：新增 `Department / Role / UserRole` 三张业务表，角色固定为 `admin / manager / staff`
- 权限三层：数据库角色关联 + `RoleContextMiddleware` + 视图装饰器/控制器范围拒绝
- 状态机：`UserRole.transition()` 管理 `active -> suspended -> revoked`
- 双向操作：采购单/销售单删除时反向回补库存；库存支持 `guard_delete` 和恢复
- 统计聚合：首页图表和卡片通过 `department_chart` 端点按部门范围刷新
- 模板联动：菜单、按钮、归档入口、角色工作台、状态徽标全部按权限显隐

## 环境要求

- Python 3.11
- SQLite（默认）

依赖安装：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 启动方式

首次运行：

```bash
python manage.py migrate
python manage.py loaddata fixtures/seed_data.json
python manage.py runserver
```

访问地址：

- 首页：`http://127.0.0.1:8000/`
- 库存列表：`http://127.0.0.1:8000/inventory/`
- 采购列表：`http://127.0.0.1:8000/transactions/purchases/`
- 销售列表：`http://127.0.0.1:8000/transactions/sales/`

## 测试账号

- `admin_ops / Admin123!`
- `north_manager / Manager123!`
- `north_staff / Staff123!`
- `south_manager / South123!`
- `ops_hold / Hold123!`：状态为 `suspended`
- `legacy_user / Legacy123!`：状态为 `revoked`

## 基础验证

1. `north_staff` 登录后看不到库存删除按钮，直接 POST `/inventory/stock/<pk>/guard-delete` 返回 403
2. `north_manager` 登录后首页图表只看到 `North Hub` 数据，删除 `South Hub` 采购单返回 403
3. `admin_ops` 在首页工作台把 `north_staff` 调到 `South Hub` 后，该用户重新打开首页，图表切换到南区库存
4. 删除采购单或销售单后，相关库存数量会自动回补

自动化验证：

```bash
python manage.py test tests.test_monolith_flow -v 2
```

## 关键路由

- `GET/POST /dashboard/department-chart/`
- `POST /memberships/<pk>/grant-role/`
- `POST /memberships/<pk>/revoke-role/`
- `POST /memberships/<pk>/change-department/`
- `POST /inventory/stock/<pk>/guard-delete`
- `POST /inventory/stock/<pk>/restore`
- `POST /transactions/purchases/<pk>/delete`
- `POST /transactions/sales/<pk>/delete`

## 说明

- 保留了原项目的 `manage.py runserver` 运行方式，没有拆成前后端双项目
- 没有引入 Docker、前端构建链或额外服务编排
- fixtures 已覆盖 `active / suspended / revoked` 三种状态和跨部门业务数据
