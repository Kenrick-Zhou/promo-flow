# 方小集（PromoFlow）常用命令
# 使用方式：just <命令>
# 安装 just：brew install just

# 默认列出所有可用命令
default:
    @just --list

# ============================================================
# 数据库 / Docker
# ============================================================

# 启动 PostgreSQL 容器
db-up:
    docker-compose up -d postgres

# 停止并移除所有容器
db-down:
    docker-compose down

# 查看容器状态
db-status:
    docker-compose ps

# ============================================================
# 后端（backend/）
# ============================================================

# 安装/同步后端依赖
be-sync:
    cd backend && uv sync --dev

# 启动后端开发服务器（热重载）
be-dev:
    cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 执行数据库迁移（升级到最新）
be-migrate:
    cd backend && uv run alembic upgrade head

# 对测试数据库执行迁移（读取 .env.test）
be-test-migrate:
    cd backend && uv run alembic -x db=test upgrade head

# 回滚所有迁移
be-migrate-down:
    cd backend && uv run alembic downgrade base

# 重置数据库并重新迁移
be-db-reset: be-migrate-down be-migrate

# 写入测试种子数据
be-seed:
    cd backend && uv run python ../scripts/seed_data.py

# 运行后端测试
be-test *args:
    cd backend && uv run pytest {{ args }}

# 后端代码格式化（black + isort）
be-fmt:
    cd backend && uv run black app tests
    cd backend && uv run isort app tests

# 后端静态检查（ruff + mypy）
be-lint:
    cd backend && uv run ruff check --fix app
    cd backend && uv run mypy app

# ============================================================
# 前端（frontend/）
# ============================================================

# 安装前端依赖
fe-install:
    cd frontend && npm install

# 启动前端开发服务器
fe-dev:
    cd frontend && npm run dev

# 构建前端生产包
fe-build:
    cd frontend && npm run build

# 构建前端 test 环境包
fe-build-test:
    cd frontend && npm run build-test

# 构建前端 dev 环境包（部署到开发服务器）
fe-build-dev:
    cd frontend && npm run build-dev

# 前端代码格式化（prettier）
fe-fmt:
    cd frontend && npm run format

# 查看 prettier 格式问题（不修改）
fe-fmt-check:
    cd frontend && npm run format:check

# 前端 ESLint 检查
fe-lint:
    cd frontend && npm run lint

# 前端 TypeScript 类型检查
fe-typecheck:
    cd frontend && npx tsc --noEmit

# ============================================================
# 全局
# ============================================================

# 运行 pre-commit（仅暂存文件）
pre-commit:
    pre-commit run

# 运行 pre-commit（所有文件）
pre-commit-all:
    pre-commit run --all-files

# 格式化全部代码（后端 + 前端）
fmt: be-fmt fe-fmt

# 静态检查全部代码（后端 + 前端）
lint: be-lint fe-lint fe-typecheck

# 统计项目代码总量（排除虚拟环境、构建产物和缓存目录）
cloc:
    cloc . --exclude-dir=.venv,node_modules,dist,build,coverage,.pytest_cache,.mypy_cache,__pycache__,.git,.vite

# 运行所有测试
test: be-test

# 完整检查：pre-commit + 后端测试
check:
    pre-commit run --all-files
    cd backend && uv run pytest -n 8

# ============================================================
# 首次初始化（clone 后一键配置）
# ============================================================

# 一键初始化开发环境
setup: db-up be-sync be-migrate fe-install
    @echo "✅ 开发环境初始化完毕"
    @echo "   后端：just be-dev"
    @echo "   前端：just fe-dev"
