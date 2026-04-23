#!/usr/bin/env bash
# PromoFlow 部署脚本：打 tag + 推送到 test 或 release 固定分支
# 使用：./deploy.sh <env> <tag> [remote]
#   env:    test | prod | both
#   tag:    vX.Y.Z 或 vX.Y.Z-rc.N
#   remote: 默认 origin

set -euo pipefail

usage() {
    cat >&2 <<EOF
用法: $0 <env> <tag> [remote]
  env:    test | prod | both
  tag:    ^v[0-9]+\\.[0-9]+\\.[0-9]+(-rc\\.[0-9]+)?\$
  remote: 默认 origin
EOF
    exit 2
}

[[ $# -lt 2 || $# -gt 3 ]] && usage

ENV="$1"
TAG="$2"
REMOTE="${3:-origin}"

# ---- 校验 ----
case "$ENV" in
    test|prod|both) ;;
    *) echo "❌ env 非法: $ENV（需为 test/prod/both）" >&2; exit 2 ;;
esac

if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]]; then
    echo "❌ tag 不合规: $TAG（期望 vX.Y.Z 或 vX.Y.Z-rc.N）" >&2
    exit 2
fi

if [[ "$ENV" == "both" && "$TAG" == *-rc.* ]]; then
    echo "❌ 同时发测试和生产时 tag 不应带 -rc 后缀（请用 vX.Y.Z）" >&2
    exit 2
fi

# ---- 远程存在性 ----
if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
    echo "❌ 远程 $REMOTE 不存在。可用远程：" >&2
    git remote -v >&2
    exit 2
fi

# ---- 工作树干净 ----
if ! git diff-index --quiet HEAD --; then
    echo "❌ 工作树不干净，请先提交或 stash：" >&2
    git status --short >&2
    exit 2
fi

HEAD_SHA=$(git rev-parse HEAD)
echo "▶ 当前 HEAD: $HEAD_SHA"
echo "▶ 环境:      $ENV"
echo "▶ Tag:       $TAG"
echo "▶ 远程:      $REMOTE"

# ---- Tag 创建（幂等） ----
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    EXISTING_SHA=$(git rev-list -n 1 "$TAG")
    if [[ "$EXISTING_SHA" != "$HEAD_SHA" ]]; then
        echo "❌ 本地 tag $TAG 已存在且指向 $EXISTING_SHA（≠ HEAD $HEAD_SHA）" >&2
        echo "   请显式决定是否 git tag -d $TAG 后重建。" >&2
        exit 2
    fi
    echo "ℹ️  本地 tag $TAG 已存在且指向 HEAD，跳过创建。"
else
    git tag -a "$TAG" -m "release $TAG"
    echo "✅ 已创建本地 tag $TAG"
fi

# ---- 远程 tag 冲突检查 ----
REMOTE_TAG_SHA=$(git ls-remote --tags "$REMOTE" "refs/tags/$TAG" | awk '{print $1}' || true)
if [[ -n "$REMOTE_TAG_SHA" && "$REMOTE_TAG_SHA" != "$HEAD_SHA" ]]; then
    # ls-remote 对 annotated tag 返回的是 tag object sha，需要解引用比较
    REMOTE_TAG_TARGET=$(git ls-remote --tags "$REMOTE" "refs/tags/${TAG}^{}" | awk '{print $1}' || true)
    if [[ -n "$REMOTE_TAG_TARGET" && "$REMOTE_TAG_TARGET" != "$HEAD_SHA" ]]; then
        echo "❌ 远程 $REMOTE 上 tag $TAG 已存在且指向不同 commit ($REMOTE_TAG_TARGET)" >&2
        exit 2
    fi
fi

# ---- 推送 ----
push_branch() {
    local branch="$1"  # test 或 release
    echo "▶ 推送 HEAD → $REMOTE refs/heads/${branch}"
    git push "$REMOTE" "HEAD:refs/heads/${branch}"
    echo "✅ 已推送 ${branch}"
}

case "$ENV" in
    test) push_branch test ;;
    prod) push_branch release ;;
    both) push_branch test; push_branch release ;;
esac

echo "▶ 推送 tag $TAG → $REMOTE"
git push "$REMOTE" "$TAG"
echo "✅ 已推送 tag $TAG"

echo
echo "🎉 部署推送完成"
echo "   环境:   $ENV"
echo "   Tag:    $TAG"
case "$ENV" in
    test) echo "   分支:   $REMOTE/test" ;;
    prod) echo "   分支:   $REMOTE/release" ;;
    both) echo "   分支:   $REMOTE/test + $REMOTE/release" ;;
esac
