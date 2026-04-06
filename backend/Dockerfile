FROM python:3.11-slim

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 先复制依赖文件，利用 Docker 层缓存
COPY pyproject.toml uv.lock ./

# 安装生产依赖（不含 dev）
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
