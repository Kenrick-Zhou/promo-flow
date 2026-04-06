# 本地开发调试指南

## 前置条件

- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）
- Docker & Docker Compose（用于启动 PostgreSQL）

---

## 第一步：启动数据库

使用 Docker Compose 启动 PostgreSQL（含 pgvector 扩展）：

```bash
docker-compose up -d postgres
```

数据库默认配置：

| 参数 | 值 |
|------|----|
| Host | `localhost:5432` |
| User | `promoflow` |
| Password | `promoflow` |
| Database | `promoflow` |

---

## 第二步：启动后端

```bash
cd backend

# 首次克隆后安装依赖
uv sync --dev

# 执行数据库迁移
uv run alembic upgrade head

# 启动开发服务器（支持热重载）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端运行于 `http://localhost:8000`，API 文档见 `http://localhost:8000/docs`。

> 所有后端命令必须在 `backend/` 目录下通过 `uv run` 执行，禁止直接调用系统 `python` / `pip`。

---

## 第三步：启动前端

```bash
cd frontend

# 首次克隆后安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行于 `http://localhost:5173`。Vite dev server 已配置 proxy，将以下路径自动转发到后端：

| 前缀 | 转发至 |
|------|--------|
| `/api` | `http://localhost:8000` |
| `/bot` | `http://localhost:8000` |

---

## 运行测试

```bash
# 后端测试
cd backend
uv run pytest

# 一键运行所有测试（项目根目录）
python scripts/run_all_tests.py
```

---

## 常用调试命令

```bash
# 查看后端日志（实时）
uv run uvicorn app.main:app --reload --log-level debug

# 重置数据库并重新迁移
uv run alembic downgrade base
uv run alembic upgrade head

# 写入测试种子数据
uv run python ../scripts/seed_data.py
```
