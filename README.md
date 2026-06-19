# School Food Chain - 学校食堂食材全链路管理平台

覆盖供应商、学校、教育局三方的食材供应链管理平台。

## 架构

```
school-food-chain/
├── backend/          # Python FastAPI 后端服务
│   ├── app/          # 核心应用
│   ├── alembic/      # 数据库迁移
│   └── tests/        # 单元测试
├── web/              # Vue3 + Element Plus 管理后台
│   ├── src/          # 源码
│   └── public/       # 静态资源
├── desktop/          # PyQt6 桌面客户端（食堂现场操作）
│   ├── src/          # 源码
│   └── assets/       # 资源文件
├── mobile/           # 微信小程序（供应商/家长端）
│   ├── pages/        # 页面
│   └── utils/        # 工具
├── docs/             # 文档
└── scripts/          # 部署脚本
```

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, Redis |
| Web后台 | Vue 3, Element Plus, ECharts, Pinia |
| 桌面端 | PyQt6, PyInstaller |
| 移动端 | 微信小程序原生 |
| 部署 | Docker, Docker Compose, Nginx |

## 核心功能

### 供应商端
- 资质管理（营业执照、检测报告、HACCP/ISO22000认证）
- 订单接单与配送跟踪
- 电子发票与结算
- 评价与考核

### 学校端
- 食材采购计划与审批
- 入库验收（双人联检、影像记录、扫码追溯）
- 库存管理与预警
- 出库领用与成本核算
- 财务统计与审计报表

### 教育局端
- 辖区学校数据汇总
- 食品安全监管大屏
- 供应商黑名单管理
- 一键上报与数据对接

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/whblcy/school-food-chain.git
cd school-food-chain

# 启动后端
cd backend
cp .env.example .env
docker-compose up -d

# 启动Web后台
cd ../web
npm install
npm run dev

# 启动桌面端
cd ../desktop
pip install -r requirements.txt
python main.py
```

## 文档

- [架构设计](docs/architecture.md)
- [API文档](docs/api.md)
- [部署指南](docs/deployment.md)
- [开发规范](docs/development.md)

## License

MIT
