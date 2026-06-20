# School Food Chain - 学校食材供应链管理平台

[![CI](https://github.com/whblcy/school-food-chain/actions/workflows/ci.yml/badge.svg)](https://github.com/whblcy/school-food-chain/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com/)

> 覆盖 **供应商 -> 学校 -> 教育局** 三方的食材供应链全链路管理平台，保障校园食品安全，实现从采购、配送、验收、入库、出库到财务结算的全流程数字化管理。

---

## 功能特性

### 供应商端

| 功能 | 说明 |
|------|------|
| 资质管理 | 营业执照、检测报告、HACCP/ISO22000 认证上传与审核 |
| 订单管理 | 在线接单、配送跟踪、签收确认 |
| 电子发票 | 自动生成发票、在线结算对账 |
| 评价考核 | 学校评价、教育局考核、信用评级 |

### 学校端

| 功能 | 说明 |
|------|------|
| 采购计划 | 食材需求提报、多级审批流程 |
| 入库验收 | 双人联检、影像记录、扫码追溯 |
| 库存管理 | 实时库存、保质期预警、自动补货 |
| 出库领用 | 领用登记、成本核算、损耗统计 |
| 财务报表 | 采购统计、成本分析、审计报表 |

### 教育局端

| 功能 | 说明 |
|------|------|
| 数据汇总 | 辖区学校采购数据实时汇总 |
| 安全监管 | 食品安全大屏、异常预警 |
| 黑名单管理 | 不合格供应商黑名单与预警 |
| 数据上报 | 一键上报、与上级系统对接 |

---

## 技术栈

| 模块 | 技术选型 |
|------|----------|
| **后端服务** | Python 3.11 / FastAPI / SQLAlchemy / Alembic |
| **数据库** | PostgreSQL 16 / Redis 7 |
| **任务队列** | Celery + Redis |
| **文件存储** | MinIO |
| **Web 管理后台** | Vue 3 / Element Plus / ECharts / Pinia / Vite |
| **桌面客户端** | PyQt6 / PyInstaller |
| **移动端** | 微信小程序（原生） |
| **部署** | Docker / Docker Compose / Nginx |

---

## 项目结构

```
school-food-chain/
├── backend/                    # FastAPI 后端服务
│   ├── app/
│   │   ├── main.py             # 应用入口
│   │   ├── config.py           # 配置管理（pydantic-settings）
│   │   ├── database.py         # 数据库连接
│   │   ├── models.py           # SQLAlchemy 数据模型
│   │   ├── schemas.py          # Pydantic 请求/响应模型
│   │   ├── auth.py             # JWT 认证逻辑
│   │   └── routers/            # API 路由模块
│   │       ├── auth.py         #   认证（登录/注册/Token刷新）
│   │       ├── users.py        #   用户管理
│   │       ├── orgs.py         #   组织（学校/教育局）
│   │       ├── suppliers.py    #   供应商管理
│   │       ├── ingredients.py  #   食材管理
│   │       ├── stock.py        #   库存（入库/出库）
│   │       ├── finance.py      #   财务结算
│   │       ├── reports.py      #   报表统计
│   │       ├── trace.py        #   溯源追踪
│   │       ├── audit.py        #   审计日志
│   │       └── gov.py          #   教育局监管
│   ├── Dockerfile
│   └── requirements.txt
│
├── web/                        # Vue3 管理后台
│   ├── src/
│   │   ├── main.js            # 应用入口
│   │   ├── App.vue             # 根组件
│   │   ├── api/                #   API 请求封装
│   │   ├── router/             #   路由配置
│   │   ├── stores/             #   Pinia 状态管理
│   │   └── views/              #   页面组件
│   │       ├── Login.vue       #     登录
│   │       ├── Layout.vue      #     布局框架
│   │       ├── Dashboard.vue   #     仪表盘
│   │       ├── Suppliers.vue   #     供应商管理
│   │       ├── Ingredients.vue #     食材管理
│   │       ├── StockIn.vue     #     入库管理
│   │       ├── StockOut.vue    #     出库管理
│   │       ├── Inventory.vue   #     库存管理
│   │       ├── Finance.vue     #     财务管理
│   │       ├── Trace.vue       #     溯源追踪
│   │       ├── Users.vue       #     用户管理
│   │       └── GovDashboard.vue#    教育局大屏
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── desktop/                    # PyQt6 桌面客户端
│   ├── main.py                 # 桌面端入口
│   ├── core/
│   │   ├── api_client.py       #   API 客户端
│   │   └── config.py           #   配置
│   ├── ui/
│   │   ├── main_window.py      #   主窗口
│   │   ├── login_dialog.py     #   登录对话框
│   │   ├── views/              #   功能视图
│   │   │   ├── dashboard_view.py
│   │   │   ├── suppliers_view.py
│   │   │   ├── ingredients_view.py
│   │   │   ├── stock_in_view.py
│   │   │   ├── stock_out_view.py
│   │   │   ├── inventory_view.py
│   │   │   ├── finance_view.py
│   │   │   ├── trace_view.py
│   │   │   └── users_view.py
│   │   └── widgets/            #   自定义控件
│   └── requirements.txt
│
├── mobile/                     # 微信小程序
│   ├── app.js / app.json / app.wxss
│   ├── pages/
│   │   ├── index/              #   首页
│   │   ├── ingredients/        #   食材列表
│   │   ├── stock/              #   库存查询
│   │   ├── trace/              #   溯源查询
│   │   └── profile/            #   个人中心
│   └── sitemap.json
│
├── docs/                       # 项目文档
│   ├── architecture.md         #   架构设计
│   └── deploy.md               #   部署指南
│
├── nginx.conf                  # Nginx 反向代理配置
├── docker-compose.yml          # Docker Compose 编排
├── .env.example                # 环境变量模板
├── .github/workflows/ci.yml    # GitHub Actions CI
└── README.md
```

---

## 快速开始（Docker Compose 一键部署）

### 前置条件

- [Docker](https://www.docker.com/get-started) >= 20.10
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.0
- [Git](https://git-scm.com/)

### 一键启动

```bash
# 1. 克隆仓库
git clone https://github.com/whblcy/school-food-chain.git
cd school-food-chain

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，修改 SECRET_KEY 等敏感配置

# 3. 构建并启动所有服务
docker-compose up -d --build

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f backend
```

启动后可访问：

| 服务 | 地址 |
|------|------|
| Web 管理后台 | http://localhost |
| API 服务 | http://localhost/api/v1 |
| API 文档（Swagger） | http://localhost:8000/docs |
| API 文档（ReDoc） | http://localhost:8000/redoc |
| MinIO 控制台 | http://localhost:9001 |

---

## 各端运行方式

### 后端服务（Backend）

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp ../.env.example .env

# 数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Web 管理后台

```bash
cd web

# 安装依赖
npm install

# 启动开发服务器（热更新）
npm run dev

# 生产构建
npm run build

# 预览生产构建
npm run preview
```

### 桌面客户端（Desktop）

```bash
cd desktop

# 安装依赖
pip install -r requirements.txt

# 启动桌面应用
python main.py

# 打包为可执行文件（可选）
pip install pyinstaller
pyinstaller --onefile --windowed --name "SchoolFoodChain" main.py
```

### 微信小程序（Mobile）

1. 使用 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) 打开 `mobile/` 目录
2. 在 `app.js` 中配置后端 API 地址
3. 点击编译预览，扫码在手机上调试

---

## API 文档

后端启动后，可通过以下地址访问交互式 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

主要 API 模块：

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 认证 | `/api/v1/auth` | 登录、注册、Token 刷新 |
| 用户 | `/api/v1/users` | 用户 CRUD、角色权限 |
| 组织 | `/api/v1/orgs` | 学校、教育局管理 |
| 供应商 | `/api/v1/suppliers` | 供应商资质、评价 |
| 食材 | `/api/v1/ingredients` | 食材分类、信息管理 |
| 库存 | `/api/v1/stock` | 入库、出库、盘点 |
| 财务 | `/api/v1/finance` | 结算、发票、对账 |
| 报表 | `/api/v1/reports` | 统计报表、导出 |
| 追溯 | `/api/v1/trace` | 食材溯源链路 |
| 审计 | `/api/v1/audit` | 操作日志、审计追踪 |
| 监管 | `/api/v1/gov` | 教育局数据汇总 |

---

## 截图

<!-- TODO: 替换为实际截图 -->

### Web 管理后台

| 仪表盘 | 供应商管理 | 库存管理 |
|--------|-----------|---------|
| ![仪表盘](docs/images/dashboard.png) | ![供应商](docs/images/suppliers.png) | ![库存](docs/images/inventory.png) |

### 桌面客户端

| 登录 | 主界面 | 入库验收 |
|------|--------|---------|
| ![登录](docs/images/desktop-login.png) | ![主界面](docs/images/desktop-main.png) | ![入库](docs/images/desktop-stockin.png) |

### 微信小程序

| 首页 | 溯源查询 | 个人中心 |
|------|--------|---------|
| ![首页](docs/images/mobile-home.png) | ![溯源](docs/images/mobile-trace.png) | ![个人](docs/images/mobile-profile.png) |

---

## 文档

- [架构设计](docs/architecture.md)
- [部署指南](docs/deploy.md)

---

## 许可证

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

```
MIT License

Copyright (c) 2024 School Food Chain Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
