"""PostgreSQL + pgvector 连通性测试脚本。

测试项：
  1. 基本连接
  2. pgvector 扩展可用性
  3. 核心表是否存在（users / contents / audit_logs）
  4. 用户表写入 / 查询 / 删除（CRUD）
  5. 内容表写入 / 查询 / 删除（含 JSONB 字段）
  6. pgvector 向量写入 + 余弦相似度搜索

用法（在项目根目录执行）：
    uv run --directory backend python ../scripts/test_db.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# ── 加载 .env ─────────────────────────────────────────────────────────────────
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ[key.strip()] = value.strip()

import asyncpg  # noqa: E402

# asyncpg 需要 postgresql:// 而不是 postgresql+asyncpg://
_raw_url: str = os.environ["DATABASE_URL"]
DSN = _raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)

# 测试数据标记，避免误删真实数据
TEST_OPEN_ID = "__test_db_script__"
TEST_UNION_ID = "__test_db_script_union__"
EMBEDDING_DIM = 1024


# ── 输出工具 ──────────────────────────────────────────────────────────────────
def ok(msg: str) -> None:
    print(f"  \033[32m[OK]\033[0m  {msg}")


def fail(msg: str) -> None:
    print(f"  \033[31m[FAIL]\033[0m {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"  \033[33m[WARN]\033[0m {msg}")


# ── 测试步骤 ──────────────────────────────────────────────────────────────────
async def main() -> None:
    print("\n=== PostgreSQL + pgvector 连通性测试 ===\n")

    conn: asyncpg.Connection = await asyncpg.connect(DSN)
    try:
        # 1. 基本连接
        print("1. 基本连接 ...")
        version: str = await conn.fetchval("SELECT version()")
        ok(f"已连接  {version.split(',')[0]}")

        # 2. pgvector 扩展
        print("2. pgvector 扩展可用性 ...")
        vec_ver = await conn.fetchval(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        )
        if vec_ver is None:
            fail("pgvector 扩展未安装，请执行 CREATE EXTENSION vector;")
        ok(f"pgvector 已安装  version={vec_ver}")

        # 3. 核心表存在性
        print("3. 核心表存在性检查 ...")
        expected_tables = ["users", "contents", "audit_logs"]
        existing = await conn.fetch(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND tablename = ANY($1::text[])
            """,
            expected_tables,
        )
        found = {row["tablename"] for row in existing}
        for tbl in expected_tables:
            if tbl in found:
                ok(f"表 {tbl!r} 存在")
            else:
                fail(f"表 {tbl!r} 不存在，请先运行 alembic upgrade head")

        # 4. 用户表 CRUD
        print("4. 用户表 CRUD ...")

        # 清理上次可能残留的测试数据
        await conn.execute(
            "DELETE FROM users WHERE feishu_open_id = $1", TEST_OPEN_ID
        )

        # 写入
        user_id: int = await conn.fetchval(
            """
            INSERT INTO users (feishu_open_id, feishu_union_id, name, role)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            TEST_OPEN_ID,
            TEST_UNION_ID,
            "测试用户_DB脚本",
            "employee",
        )
        ok(f"INSERT 成功  id={user_id}")

        # 查询
        row = await conn.fetchrow(
            "SELECT id, name, role, created_at FROM users WHERE id = $1", user_id
        )
        assert row is not None, "刚插入的用户查询不到"
        assert row["name"] == "测试用户_DB脚本"
        ok(f"SELECT 成功  name={row['name']}  role={row['role']}  created_at={row['created_at']}")

        # 更新
        await conn.execute(
            "UPDATE users SET name = $1 WHERE id = $2",
            "测试用户_DB脚本_已更新",
            user_id,
        )
        updated_name = await conn.fetchval(
            "SELECT name FROM users WHERE id = $1", user_id
        )
        assert updated_name == "测试用户_DB脚本_已更新"
        ok(f"UPDATE 成功  name={updated_name}")

        # 5. 内容表 CRUD（含 JSONB 字段，不含 embedding）
        print("5. 内容表 CRUD（JSONB 字段）...")
        import json

        tags_json = json.dumps(["健康", "推广", "测试"])
        content_id: int = await conn.fetchval(
            """
            INSERT INTO contents
                (title, description, tags, content_type, status, file_key, uploaded_by)
            VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7)
            RETURNING id
            """,
            "DB脚本测试素材",
            "这是由 test_db.py 自动创建的测试记录",
            tags_json,
            "image",
            "pending",
            "test/db_script_placeholder.png",
            user_id,
        )
        ok(f"INSERT 成功  id={content_id}")

        c_row = await conn.fetchrow(
            "SELECT id, title, tags, status FROM contents WHERE id = $1", content_id
        )
        assert c_row is not None
        assert c_row["title"] == "DB脚本测试素材"
        ok(f"SELECT 成功  title={c_row['title']}  status={c_row['status']}")

        # 6. pgvector 向量写入 + 相似度搜索
        print("6. pgvector 向量写入 + 余弦相似度搜索 ...")

        # 写入两条有 embedding 的内容（第二条用于相似度对比）
        vec_a = [0.1] * EMBEDDING_DIM          # embedding A
        vec_b_list = [0.1] * EMBEDDING_DIM
        vec_b_list[0] = 0.9                    # embedding B，偏离 A
        vec_b = vec_b_list

        # asyncpg 需要将 list 序列化为 pgvector 文本格式
        def to_pg_vec(v: list[float]) -> str:
            return "[" + ",".join(str(x) for x in v) + "]"

        cid_a: int = await conn.fetchval(
            """
            INSERT INTO contents
                (title, tags, content_type, status, file_key, uploaded_by, embedding)
            VALUES ($1, '[]'::jsonb, 'image', 'pending', 'test/vec_a.png', $2, $3::vector)
            RETURNING id
            """,
            "DB脚本向量测试_A",
            user_id,
            to_pg_vec(vec_a),
        )
        ok(f"向量 A 写入成功  id={cid_a}")

        cid_b: int = await conn.fetchval(
            """
            INSERT INTO contents
                (title, tags, content_type, status, file_key, uploaded_by, embedding)
            VALUES ($1, '[]'::jsonb, 'image', 'pending', 'test/vec_b.png', $2, $3::vector)
            RETURNING id
            """,
            "DB脚本向量测试_B",
            user_id,
            to_pg_vec(vec_b),
        )
        ok(f"向量 B 写入成功  id={cid_b}")

        # 余弦相似度搜索：用 vec_a 查询，期望 A 排在 B 前面
        query_vec = to_pg_vec([0.1] * EMBEDDING_DIM)
        results = await conn.fetch(
            """
            SELECT id, title, 1 - (embedding <=> $1::vector) AS cosine_sim
            FROM contents
            WHERE id = ANY($2::int[])
            ORDER BY embedding <=> $1::vector
            LIMIT 5
            """,
            query_vec,
            [cid_a, cid_b],
        )
        assert results[0]["id"] == cid_a, "相似度最高的应该是向量 A"
        for r in results:
            ok(f"  id={r['id']}  title={r['title']}  cosine_sim={r['cosine_sim']:.6f}")
        ok("余弦相似度搜索返回顺序正确（A > B）")

        # ── 清理测试数据 ──────────────────────────────────────────────────────
        print("7. 清理测试数据 ...")
        deleted_contents = await conn.fetchval(
            "DELETE FROM contents WHERE uploaded_by = $1 RETURNING id", user_id
        )
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        ok("测试数据已清理")

    finally:
        await conn.close()

    print("\n\033[32m所有检查通过，数据库配置正常！\033[0m\n")


if __name__ == "__main__":
    asyncio.run(main())
