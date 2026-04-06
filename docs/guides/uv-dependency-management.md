# Python 依赖管理（uv）

后端使用 [uv](https://docs.astral.sh/uv/) 管理 Python 依赖。所有依赖声明在 `backend/pyproject.toml`，精确版本锁定在 `backend/uv.lock`（需提交到 git）。

## 初始化（首次克隆后）

```bash
cd backend
uv sync --dev
```

这会自动创建 `backend/.venv` 并安装所有依赖（含 dev）。

## 常用命令

### 运行项目命令

```bash
cd backend

# 启动开发服务器
uv run uvicorn app.main:app --reload

# 运行测试
uv run pytest

# 执行数据库迁移
uv run alembic upgrade head
```

`uv run` 会自动使用 `.venv` 中的解释器，无需手动 `source .venv/bin/activate`。

### 管理依赖

```bash
# 添加生产依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>

# 移除依赖
uv remove <package>

# 同步依赖（拉取他人更改后执行）
uv sync --dev
```

### 更新依赖版本

```bash
# 更新单个包
uv lock --upgrade-package <package>

# 更新所有包到最新兼容版本
uv lock --upgrade

# 更新后重新同步
uv sync --dev
```

## 文件说明

| 文件 | 说明 | 是否提交 git |
|------|------|:---:|
| `pyproject.toml` | 依赖声明（版本约束） | ✅ |
| `uv.lock` | 精确锁定版本（可复现构建） | ✅ |
| `.venv/` | 本地虚拟环境 | ❌（已 gitignore） |

## Docker

Dockerfile 已配置使用 uv，构建时自动读取 `uv.lock` 安装生产依赖：

```bash
# 在项目根目录
docker compose up --build backend
```
