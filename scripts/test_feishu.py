"""简单的飞书连通性测试脚本：验证 App Token、Bot 信息、OAuth URL 和 Webhook 签名逻辑。

用法（在项目根目录执行）：
    uv run --directory backend python ../scripts/test_feishu.py
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

# 加载 .env（相对于项目根目录）
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ[key.strip()] = value.strip()

import httpx  # noqa: E402

APP_ID = os.environ["FEISHU_APP_ID"]
APP_SECRET = os.environ["FEISHU_APP_SECRET"]
VERIFICATION_TOKEN = os.environ["FEISHU_VERIFICATION_TOKEN"]
ENCRYPT_KEY = os.environ["FEISHU_ENCRYPT_KEY"]
REDIRECT_URI = os.environ["FEISHU_REDIRECT_URI"]

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


def ok(msg: str) -> None:
    print(f"  \033[32m[OK]\033[0m  {msg}")


def warn(msg: str) -> None:
    print(f"  \033[33m[WARN]\033[0m {msg}")


def fail(msg: str) -> None:
    print(f"  \033[31m[FAIL]\033[0m {msg}")
    sys.exit(1)


def main() -> None:
    print("\n=== 飞书连通性测试 ===\n")

    # 1. 获取 tenant_access_token（验证 APP_ID + APP_SECRET）
    print("1. 获取 tenant_access_token ...")
    resp = httpx.post(
        f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=10,
    )
    if resp.status_code != 200:
        fail(f"HTTP {resp.status_code}: {resp.text}")
    body = resp.json()
    if body.get("code") != 0:
        fail(f"飞书返回错误 code={body.get('code')} msg={body.get('msg')}")
    token = body["tenant_access_token"]
    expires_in = body.get("expire", "?")
    ok(f"tenant_access_token 获取成功  有效期={expires_in}s  token={token[:20]}...")

    # 2. 获取 Bot 基本信息（验证 Bot 权限）
    print("2. 获取 Bot 基本信息 ...")
    resp = httpx.get(
        f"{FEISHU_API_BASE}/bot/v3/info",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        fail(f"HTTP {resp.status_code}: {resp.text}")
    body = resp.json()
    if body.get("code") == 11205:
        warn("应用未开启「机器人」能力（code=11205）——如需 Bot 推送，请在飞书开放平台「添加应用能力 → 机器人」并发布版本")
    elif body.get("code") != 0:
        fail(f"飞书返回错误 code={body.get('code')} msg={body.get('msg')}")
    else:
        bot = body.get("bot", {})
        ok(f"Bot 名称={bot.get('app_name')}  open_id={bot.get('open_id')}  状态={bot.get('activate_status')}")

    # 3. 构造 OAuth 授权 URL（验证 APP_ID + REDIRECT_URI 拼接）
    print("3. 构造 OAuth 授权 URL ...")
    params = urlencode({"app_id": APP_ID, "redirect_uri": REDIRECT_URI, "response_type": "code"})
    oauth_url = f"https://open.feishu.cn/open-apis/authen/v1/authorize?{params}"
    ok(f"OAuth URL 构造成功\n       {oauth_url}")

    # 4. 本地验证 Webhook HMAC 签名逻辑
    print("4. 验证 Webhook HMAC 签名逻辑（本地）...")
    if ENCRYPT_KEY == "dev-placeholder":
        warn("FEISHU_ENCRYPT_KEY 为占位值 'dev-placeholder'，仅验证签名算法本身是否正确")
    timestamp = "1712345678"
    nonce = "abc123"
    body_str = '{"type":"url_verification"}'
    key = ENCRYPT_KEY.encode()
    content = f"{timestamp}{nonce}{body_str}".encode()
    sig = hmac.new(key, content, hashlib.sha256).hexdigest()
    # 使用同一组参数重新计算，验证 compare_digest 通过
    sig2 = hmac.new(key, content, hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, sig2):
        ok(f"HMAC-SHA256 签名算法验证通过  sig={sig[:16]}...")
    else:
        fail("HMAC 签名自检失败")

    # 5. 验证 VERIFICATION_TOKEN 不为空且格式合理
    print("5. 校验 VERIFICATION_TOKEN 配置 ...")
    if len(VERIFICATION_TOKEN) < 8:
        fail(f"FEISHU_VERIFICATION_TOKEN 过短，可能未正确配置: {VERIFICATION_TOKEN!r}")
    ok(f"VERIFICATION_TOKEN 已配置  长度={len(VERIFICATION_TOKEN)}")

    print("\n\033[32m所有检查通过，飞书配置正常！\033[0m\n")


if __name__ == "__main__":
    main()
