"""简单的 DashScope 多模态 AI 连通性测试脚本。

测试 qwen3-vl-plus 图像理解能力：识别 logo / 文字。

用法（在项目根目录执行）：
    uv run --directory backend python ../scripts/test_ai.py [图片路径或URL]

示例：
    uv run --directory backend python ../scripts/test_ai.py scripts/youxiaofang_logo.png
    uv run --directory backend python ../scripts/test_ai.py https://example.com/logo.png

不传参数时，默认使用 scripts/youxiaofang_logo.png。
"""

from __future__ import annotations

import base64
import json
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
            os.environ[key.strip()] = value.strip()

import dashscope  # noqa: E402
from dashscope import MultiModalConversation  # noqa: E402

DASHSCOPE_API_KEY = os.environ["DASHSCOPE_API_KEY"]
QIANWEN_MODEL = os.environ.get("DASHSCOPE_VISION_MODEL", "qwen3-vl-plus")

dashscope.api_key = DASHSCOPE_API_KEY

# 默认图片路径（项目根目录相对）
DEFAULT_IMAGE = Path(__file__).parent / "youxiaofang_logo.png"


def ok(msg: str) -> None:
    print(f"  \033[32m[OK]\033[0m  {msg}")


def fail(msg: str) -> None:
    print(f"  \033[31m[FAIL]\033[0m {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"  \033[33m[WARN]\033[0m {msg}")


def resolve_image(arg: str | None) -> tuple[str, str]:
    """
    返回 (image_ref, display_name)。
    image_ref 可以是 URL 或 file:// 绝对路径 或 base64 data URI。
    """
    path_str = arg or str(DEFAULT_IMAGE)

    # 如果是 http/https URL，直接使用
    if path_str.startswith(("http://", "https://")):
        return path_str, path_str

    # 本地文件
    p = Path(path_str)
    if not p.is_absolute():
        # 相对路径以项目根目录为基准
        p = Path(__file__).parent.parent / path_str
    if not p.exists():
        fail(
            f"图片文件不存在: {p}\n"
            "  请将 logo 图片保存为 scripts/youxiaofang_logo.png，或传入路径/URL 作为参数。"
        )

    # 读取并 base64 编码
    suffix = p.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
    mime = mime_map.get(suffix, "image/png")
    b64 = base64.b64encode(p.read_bytes()).decode()
    data_uri = f"data:{mime};base64,{b64}"
    return data_uri, str(p)


def call_multimodal(image_ref: str, prompt: str) -> dict:
    """调用 qwen3-vl-plus，返回解析后的 JSON 或原始文本。"""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image_ref},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    response = MultiModalConversation.call(
        model=QIANWEN_MODEL,
        messages=messages,
    )
    if response.status_code != 200:
        fail(f"API 返回错误 code={response.status_code} message={response.message}")

    raw_text: str = response.output.choices[0].message.content[0]["text"]
    # 尝试剥离 <think>...</think>（qwen3 thinking 模式）
    if "<think>" in raw_text and "</think>" in raw_text:
        raw_text = raw_text[raw_text.index("</think>") + len("</think>"):].strip()
    return {"raw": raw_text}


def main() -> None:
    print(f"\n=== DashScope 多模态 AI 测试（{QIANWEN_MODEL}）===\n")

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    image_ref, display_name = resolve_image(arg)

    print(f"图片来源: {display_name}\n")

    # --- 测试 1：自由描述图片 ---
    print("1. 图像自由描述 ...")
    result = call_multimodal(image_ref, "请描述这张图片的内容，包括文字和视觉元素。")
    description = result["raw"]
    ok(f"模型回答:\n\n{description}\n")

    # --- 测试 2：识别品牌/文字 ---
    print("2. 品牌 & 文字识别 ...")
    result2 = call_multimodal(image_ref, "图片中包含哪些文字？如果是品牌 logo，请说明品牌名称。")
    text_result = result2["raw"]
    ok(f"模型回答:\n\n{text_result}\n")

    # --- 测试 3：营销素材摘要 + 关键词（正式业务 prompt）---
    print("3. 营销素材分析（业务 prompt）...")
    biz_prompt = (
        "请分析以下营销素材，输出一段简洁的摘要（100字以内）和5个关键词。"
        '以JSON格式返回：{"summary": "...", "keywords": ["..."]}'
    )
    result3 = call_multimodal(image_ref, biz_prompt)
    raw3 = result3["raw"]
    # 尝试提取 JSON
    json_start = raw3.find("{")
    json_end = raw3.rfind("}") + 1
    if json_start != -1 and json_end > json_start:
        try:
            parsed = json.loads(raw3[json_start:json_end])
            ok(f"摘要: {parsed.get('summary', '（空）')}")
            ok(f"关键词: {parsed.get('keywords', [])}")
        except json.JSONDecodeError:
            warn(f"JSON 解析失败，原始输出:\n{raw3}")
    else:
        warn(f"未找到 JSON，原始输出:\n{raw3}")

    # --- 基本断言：检查关键文字是否被识别 ---
    print("4. 断言：是否识别出「有小方」或相关品牌 ...")
    combined = (description + text_result).lower()
    keywords_hit = any(kw in combined for kw in ["有小方", "youxiaofang", "有方", "小方"])
    if keywords_hit:
        ok("模型识别出品牌关键词「有小方」✓")
    else:
        warn("未在回答中找到「有小方」——请检查图片是否正确传入，或模型输出格式")

    print(f"\n\033[32m测试完成！\033[0m\n")


if __name__ == "__main__":
    main()
