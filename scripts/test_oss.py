"""简单的 OSS 连通性测试脚本：上传、读取、删除。"""

import os
import sys
from pathlib import Path

# 加载 .env（相对于项目根目录）
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ[key.strip()] = value.strip()  # 强制覆盖 shell 中的旧值

import oss2  # noqa: E402

ACCESS_KEY_ID = os.environ["OSS_ACCESS_KEY_ID"]
ACCESS_KEY_SECRET = os.environ["OSS_ACCESS_KEY_SECRET"]
BUCKET_NAME = os.environ["OSS_BUCKET_NAME"]
ENDPOINT = os.environ["OSS_ENDPOINT"]
BUCKET_DOMAIN = os.environ.get("OSS_BUCKET_DOMAIN", "")

TEST_KEY = "test/oss_connectivity_check.txt"
TEST_CONTENT = b"PromoFlow OSS connectivity test - OK"


def ok(msg: str) -> None:
    print(f"  \033[32m[OK]\033[0m  {msg}")


def fail(msg: str) -> None:
    print(f"  \033[31m[FAIL]\033[0m {msg}")
    sys.exit(1)


def main() -> None:
    print("\n=== OSS 连通性测试 ===\n")

    auth = oss2.Auth(ACCESS_KEY_ID, ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, ENDPOINT, BUCKET_NAME)

    # 1. 上传
    print("1. 上传测试文件 ...")
    result = bucket.put_object(TEST_KEY, TEST_CONTENT)
    if result.status == 200:
        ok(f"上传成功  key={TEST_KEY}")
    else:
        fail(f"上传失败，HTTP {result.status}")

    # 2. 读取并校验内容
    print("2. 读取并校验内容 ...")
    obj = bucket.get_object(TEST_KEY)
    body = obj.read()
    if body == TEST_CONTENT:
        ok(f"内容一致  ({len(body)} bytes)")
    else:
        fail(f"内容不匹配: {body!r}")

    # 3. 获取元信息（head）
    print("3. 获取对象元信息 ...")
    meta = bucket.head_object(TEST_KEY)
    ok(f"Content-Type={meta.headers.get('Content-Type')}  ETag={meta.etag}")

    # 4. 生成预签名下载 URL（验证签名逻辑）
    print("4. 生成预签名下载 URL ...")
    url = bucket.sign_url("GET", TEST_KEY, 60)
    ok(f"预签名 URL 生成成功（60s）\n       {url[:80]}...")

    # 5. 公网 URL（如果配置了自定义域名）
    if BUCKET_DOMAIN:
        public_url = f"{BUCKET_DOMAIN.rstrip('/')}/{TEST_KEY}"
        ok(f"公网 URL: {public_url}")

    # 6. 删除测试文件
    print("5. 删除测试文件 ...")
    del_result = bucket.delete_object(TEST_KEY)
    if del_result.status == 204:
        ok("文件已删除")
    else:
        fail(f"删除失败，HTTP {del_result.status}")

    print("\n\033[32m所有检查通过，OSS 配置正常！\033[0m\n")


if __name__ == "__main__":
    main()
