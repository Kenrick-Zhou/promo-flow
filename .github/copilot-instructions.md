# PromoFlow — 营销内容管理系统

## 项目简介
PromoFlow 是一个基于飞书工作台的营销内容管理系统，服务于有方大健康公司。员工可上传图片/视频/文档等营销素材，系统利用 AI 自动分析生成摘要和关键词，审核人员审批后通过飞书机器人推送通知，并支持语义检索和 AI 问答。

## 用户角色
- **employee**（普通员工）：上传素材、浏览、搜索
- **reviewer**（审核人员）：审核待发布内容
- **admin**（管理员）：用户管理、系统设置

## 技术栈
| 层 | 技术 |
|----|------|
| 前端 | React 19 + TypeScript + Vite 8 + Tailwind CSS v4 + Zustand + HyperUI（组件模式参考） |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + Alembic |
| 数据库 | PostgreSQL 16 + pgvector（向量检索） |
| 认证 | 飞书 OAuth 2.0 → JWT（无密码体系） |
| 存储 | 阿里云 OSS（presigned URL 直传） |
| AI | 通义千问多模态（DashScope）+ OpenAI（embeddings / RAG） |
| 机器人 | 飞书 Bot（审核通知 + 群内问答） |
| 后台任务 | FastAPI BackgroundTasks（无 Redis / Celery） |

## Mono-repo 结构
```
promo-flow/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── bot/          # 飞书机器人 webhook
│   │   ├── core/         # 配置、安全、依赖注入
│   │   ├── db/           # 数据库 session
│   │   ├── domains/      # 纯领域类型（dataclass / enum）
│   │   ├── models/       # SQLAlchemy ORM
│   │   ├── routers/      # API 路由
│   │   ├── schemas/      # Pydantic 请求/响应模型
│   │   ├── services/     # 业务逻辑（按领域分包）
│   │   │   ├── auth/
│   │   │   ├── content/
│   │   │   ├── search/
│   │   │   └── infrastructure/  # AI、OSS 适配器
│   │   └── workers/      # 后台任务
│   ├── migrations/       # Alembic 迁移
│   └── tests/
├── frontend/         # React 前端
│   └── src/
│       ├── components/   # 可复用组件（content/, layout/）
│       ├── hooks/        # 自定义 hooks
│       ├── pages/        # 路由页面
│       ├── services/     # Axios API 客户端
│       ├── store/        # Zustand 全局状态
│       └── types/        # TypeScript 类型定义
├── docs/             # 设计文档
└── .github/instructions/  # AI coding agent 指令
    ├── backend/          # 后端编码规范（11 文件）
    └── frontend/         # 前端编码规范（7 文件）
```

## 关键约定
- **后端 Python 环境**：使用 `uv` 管理依赖，虚拟环境位于 `backend/.venv/`。所有后端命令必须在 `backend/` 目录下通过 `uv run <cmd>` 执行（如 `uv run pytest`、`uv run alembic upgrade head`），**禁止**直接调用系统 `python` / `pip` / `pytest`，否则会使用错误解释器。添加依赖用 `uv add <pkg>`，开发依赖用 `uv add --dev <pkg>`。
- **语言**：后端 Python，前端 TypeScript。用户界面文案使用中文。
- **认证**：飞书 OAuth → JWT，无密码体系。`get_current_user` 依赖返回 User ORM 对象。
- **前后端类型同步**：后端 `schemas/` 与前端 `types/` 需保持字段一致。
- **API 路径**：统一 `/api/v1/` 前缀，Vite dev proxy 转发到后端 `localhost:8000`。
- **分层边界**：后端 `routers → services → domains`，前端 `pages → hooks → services/store`。不跨层调用。
