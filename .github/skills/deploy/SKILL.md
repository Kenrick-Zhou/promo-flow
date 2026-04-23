---
name: deploy
description: '部署 PromoFlow 到测试或生产环境。当用户说"发测试"、"发生产"、"发测试和生产"、"上测试环境"、"上线"、"release"、"deploy to test/prod"等话术时触发。负责：1) 执行 `just check` 质量门禁；2) 规范化分支命名（小写、横线、可选类型前缀 feat/fix/chore/...）；3) 基于当前 HEAD 打 tag；4) 推送到 `test/<name>` 或 `release/<name>` 远程分支触发部署。'
argument-hint: '[test|prod|both] [可选分支名] [可选tag]'
---

# PromoFlow 部署（测试 / 生产）

## 触发词（示例）

- "发测试" / "发生产" / "发测试和生产" / "同时发测试和生产"
- "上测试" / "上线" / "发布"
- "deploy to test" / "release to prod" / "ship it"

## 仓库约定（写死，不要让模型再猜）

- 默认远程：`origin`（codeup.aliyun.com，CI/CD 目标）。用户未提及远程时一律使用 `origin`，不主动推送到其他远程。
- **测试分支（固定）**：`test` — 推送此分支触发测试流水线。
- **生产分支（固定）**：`release` — 推送此分支触发生产流水线。
- Tag 风格：语义化版本带 `v` 前缀。
  - 生产：`vX.Y.Z`（如 `v0.1.0`、`v1.2.3`）
  - 测试：`vX.Y.Z-rc.N`（如 `v0.2.0-rc.1`）
  - "测试+生产同发"：共用一个 `vX.Y.Z`，两个分支都推。

## 完整流程（必须按顺序执行，不要跳步）

### 第 1 步 · 解析用户意图

从用户消息中提取以下要素，缺什么就向用户确认什么，**不要自己编造**：

| 要素 | 必填 | 默认 / 推断方式 |
|------|------|-----------------|
| 环境 `env` | ✅ | 从"发测试/发生产/都发"判断，二义时询问 |
| tag | ✅ | 见第 2 步 |
| 远程 `remote` | ❌ | 默认 `origin` |

> 部署分支已固定（`test` / `release`），无需用户指定分支名。

### 第 2 步 · 确定 tag

- 本仓库当前**尚无任何 tag**。首次发版默认建议：
  - 生产首发：`v1.0.0`
  - 测试首发：`v1.0.0-rc.1`
- 后续：基于 `git describe --tags --abbrev=0` 自增（rc 递增 N；prod 递增 patch/minor 由用户决定）。
- 用户显式给了 tag 就用用户的，不合规（不以 `v` 开头、非 semver）则建议修正并确认。
- **测试+生产同发**：共用一个 `vX.Y.Z`，不用 rc 后缀。

### 第 3 步 · 质量门禁（不可跳过）

执行：

```bash
just check
```

失败则**立即停止**，把错误摘要报给用户，不得继续打 tag 或推送。

### 第 4 步 · 调用部署脚本

使用 [scripts/deploy.sh](./scripts/deploy.sh)。脚本参数：

```
./scripts/deploy.sh <env> <tag> [remote]
  env:     test | prod | both
  tag:     形如 v0.1.0 或 v0.1.0-rc.1
  remote:  默认 origin
```

脚本行为（幂等、带 dry-run 提示）：

1. 校验工作树干净、当前 HEAD、tag 语法。
2. 若 tag 已存在：
   - 同名同 commit → 跳过创建，继续推送。
   - 同名不同 commit → 报错退出，请用户显式处理。
3. 创建带 annotation 的 tag：`git tag -a <tag> -m "release <tag>"`。
4. 根据 `env` 推送：
   - `test`  → `git push <remote> HEAD:refs/heads/test` + `git push <remote> <tag>`
   - `prod`  → `git push <remote> HEAD:refs/heads/release` + `git push <remote> <tag>`
   - `both`  → 以上两条都执行，tag 只推一次。
5. 打印最终的远程分支和 tag URL 提示。

### 第 5 步 · 汇报

给用户简短确认：推送了哪些远程分支、哪个 tag、下一步在哪里看部署状态（例如 CodeUp/CI 流水线）。

## 决策边界

- **禁止**：自动 `git push --force`、修改历史、跳过 `just check`、用非 `v` 前缀的 tag。
- **需用户确认**：tag 不合规、工作树不干净、tag 已在远程存在且指向不同 commit。
- **可直接执行**：`just check`、`git tag -a`、`git push <remote> HEAD:refs/heads/test`、`git push <remote> HEAD:refs/heads/release`。

## 常见用法示例

| 用户说 | 执行 |
|--------|------|
| "发测试" | 建议 tag `vX.Y.Z-rc.1`（待确认），然后 `deploy.sh test vX.Y.Z-rc.1` → 推 `test` 分支 |
| "发生产 v0.2.0" | tag 用用户给的；`deploy.sh prod v0.2.0` → 推 `release` 分支 |
| "测试和生产一起发 v1.0.0" | env=both；推 `test` 和 `release` 分支，tag 一次 |

## 相关文件

- [scripts/deploy.sh](./scripts/deploy.sh) — 打 tag + 推送的幂等脚本
