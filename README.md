# Seller Copilot Agent

一个以 mock-first 为核心的多模态电商智能体演示项目，用于商品主图诊断、规则检索、工具调用，以及可追踪结果输出。

## 架构

```
用户查询 + 图片
        |
        v
     CLI 演示
        |
        v
      Planner
   /     |      \
  v      v       v
 RAG   Prompt   模型（mock/swift）
  |                 |
  v                 v
检索到的规则      JSON 工具调用
        \         /
         v       v
         工具执行器
               |
               v
          FastAPI 工具服务
               |
               v
             最终响应
               |
               v
           runs/* 轨迹记录
```

## 功能特性

- 基于 FastAPI 的 mock 工具服务，支持商品信息查询、库存查询、整改任务创建和广告文案生成
- 新增库存平台 API：商品模板、SKU、渠道刊登、多仓库存、库存流水、销售订单、采购、收货、调拨、调整、盘点、审批、审计和同步监控
- legacy `/product/{product_id}` 和 `/inventory/{product_id}` 保持稳定，内部从 SKU + warehouse 库存模型聚合
- React 前端提供 catalog、库存总览、多仓明细、库存流水、采购、调拨、盘点、调整和同步监控页面
- 基于 `data/kb` 的本地确定性 Markdown 检索
- 输出严格 JSON 的 mock 运行时模型
- 具备模块化终端输出的 CLI 演示
- 在 `runs/` 目录下持久化保存运行轨迹

## 安装

```bash
pip install -r requirements.txt
```

## 启动工具服务

```bash
uvicorn tools.app:app --reload --port 8000
```

## 启动前端

```bash
cd web
npm install
npm run dev
```

打开 `http://localhost:5173`。默认 API 地址是 `http://localhost:8000`，可通过 `VITE_API_BASE_URL` 覆盖。

## PostgreSQL 本地运行

创建数据库：

```bash
export PGPASSWORD=qwer5358
createdb -h localhost -p 5432 -U postgres seller_copilot
```

如果数据库已存在，可以跳过创建。复制本地环境文件后确认使用 postgres 存储：

```bash
cp .env.example .env
```

`.env` 中应包含：

```env
SELLER_COPILOT_STORAGE=postgres
DATABASE_URL=postgresql://postgres:qwer5358@localhost:5432/seller_copilot
```

执行 migration 并插入 100 条演示数据：

```bash
export DATABASE_URL=postgresql://postgres:qwer5358@localhost:5432/seller_copilot
alembic upgrade head
python -m tools.seed_postgres --reset --count 100
```

启动 API：

```bash
uvicorn tools.app:app --reload --port 8000
```

验证 legacy 聚合接口：

```bash
curl http://127.0.0.1:8000/product/SKU_001
curl http://127.0.0.1:8000/inventory/SKU_001
curl http://127.0.0.1:8000/api/inventory/balances
```

## 一键本地栈

```bash
cp .env.example .env
docker compose up --build
```

服务地址：

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Web: `http://localhost:5173`
- PostgreSQL: `localhost:5432`, database/user/password 均见 `.env.example`

Docker Compose 默认使用 PostgreSQL 模式，并在 API 容器启动时执行 `alembic upgrade head` 和 `python -m tools.seed_postgres --count 100`。

如果旧的 Docker volume 已经用 `seller/seller` 初始化过，Postgres 不会自动改成新的 `postgres/qwer5358`。先检查：

```bash
docker compose down
docker volume ls
```

只有确认要清空本地容器数据库时，再执行：

```bash
docker compose down -v
```

## 运行 CLI 演示

```bash
python -m demo.cli_demo \
  --image data/images/sku_001_main.jpg \
  --product-id SKU_001 \
  --query "请分析这张商品主图是否适合美国站投放，如不适合请直接创建整改任务并生成两条广告文案。"
```

## 训练脚本

参见 `train/README.md`。

## 库存平台 API

主数据 CRUD：

```text
GET/POST /api/product-templates
GET/POST/PATCH/DELETE /api/skus
GET/POST/PATCH /api/warehouses
GET/POST /api/suppliers
GET/POST /api/channel-accounts
GET/POST /api/channel-listings
GET/POST /api/inventory-policies
```

库存业务命令：

```text
POST /api/inventory/receive
POST /api/inventory/allocate
POST /api/inventory/release
POST /api/inventory/ship
POST /api/inventory/adjust
POST /api/inventory/damage
POST /api/inventory/return
GET  /api/inventory/balances
GET  /api/inventory/movements
```

业务流程：

```text
POST /api/sales-orders
POST /api/sales-orders/{id}/cancel
POST /api/sales-orders/{id}/ship
POST /api/purchase-orders
POST /api/receipts
POST /api/stock-transfers
POST /api/stock-transfers/{id}/ship
POST /api/stock-transfers/{id}/receive
POST /api/inventory-adjustments
GET/POST /api/stock-counts
GET/POST /api/sync/jobs
GET /api/audit-logs
```

## 评估

评估脚本计划在下一轮迭代中补充。

## 项目亮点

- 默认采用 mock 模式，因此即使没有 GPU 也可以直接运行演示
- 工具 schema 统一集中在 `agent/tool_registry.py`
- 训练协议与运行时协议被有意解耦，便于维护与扩展
