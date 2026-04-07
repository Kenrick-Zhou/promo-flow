"""汇总测试脚本：依次运行 test_feishu.py / test_oss.py / test_db.py / test_ai.py，
收集每个脚本的退出码与输出，最后打印汇总报告。

用法（在项目根目录执行）：
    uv run --directory backend python ../scripts/run_all_tests.py [--skip ai]

可选参数：
    --skip <name1,name2,...>   跳过指定测试（逗号分隔），可用名称：feishu oss db ai
    --only <name1,name2,...>   只运行指定测试

示例：
    uv run --directory backend python ../scripts/run_all_tests.py
    uv run --directory backend python ../scripts/run_all_tests.py --skip ai
    uv run --directory backend python ../scripts/run_all_tests.py --only db,oss
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

# 测试套件定义（顺序有意义：先基础设施再 AI）
ALL_TESTS: list[tuple[str, Path]] = [
    ("feishu", SCRIPTS_DIR / "test_feishu.py"),
    ("oss",    SCRIPTS_DIR / "test_oss.py"),
    ("db",     SCRIPTS_DIR / "test_db.py"),
    ("ai",     SCRIPTS_DIR / "test_ai.py"),
]

# ── ANSI 颜色 ────────────────────────────────────────────────────────────────
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def parse_args() -> tuple[set[str], set[str]]:
    """返回 (skip_set, only_set)。"""
    skip: set[str] = set()
    only: set[str] = set()
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--skip" and i + 1 < len(args):
            skip = {s.strip() for s in args[i + 1].split(",")}
            i += 2
        elif args[i] == "--only" and i + 1 < len(args):
            only = {s.strip() for s in args[i + 1].split(",")}
            i += 2
        else:
            print(f"未知参数: {args[i]}", file=sys.stderr)
            sys.exit(1)
    return skip, only


def run_script(name: str, script: Path) -> tuple[bool, float, str]:
    """运行单个脚本，返回 (passed, elapsed_s, output)。"""
    # 以项目根目录为 cwd，与其他脚本保持一致
    project_root = SCRIPTS_DIR.parent
    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - start
    output = result.stdout + (("\n" + result.stderr) if result.stderr.strip() else "")
    return result.returncode == 0, elapsed, output


def main() -> None:
    skip_set, only_set = parse_args()

    # 筛选要运行的测试
    tests_to_run = [
        (name, script)
        for name, script in ALL_TESTS
        if name not in skip_set and (not only_set or name in only_set)
    ]

    if not tests_to_run:
        print(f"{YELLOW}没有需要运行的测试。{RESET}")
        sys.exit(0)

    print(f"\n{BOLD}{'=' * 54}{RESET}")
    print(f"{BOLD}  方小集（PromoFlow）— 集成连通性测试汇总{RESET}")
    print(f"{BOLD}{'=' * 54}{RESET}\n")

    results: list[tuple[str, bool, float, str]] = []

    for name, script in tests_to_run:
        label = f"{CYAN}[{name.upper():^8}]{RESET}"
        print(f"{label} 运行中 → {script.name} ...")
        passed, elapsed, output = run_script(name, script)

        # 缩进输出（便于阅读）
        indented = "\n".join("    " + ln for ln in output.splitlines())
        print(indented)

        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"{label} {status}  ({elapsed:.1f}s)\n")
        results.append((name, passed, elapsed, output))

    # ── 汇总报告 ─────────────────────────────────────────────────────────────
    total = len(results)
    passed_count = sum(1 for _, p, _, _ in results if p)
    failed_count = total - passed_count
    total_time = sum(e for _, _, e, _ in results)

    print(f"{BOLD}{'=' * 54}{RESET}")
    print(f"{BOLD}  测试结果汇总{RESET}")
    print(f"{BOLD}{'=' * 54}{RESET}")
    for name, passed, elapsed, _ in results:
        icon  = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        color = GREEN if passed else RED
        print(f"  {icon}  {color}{name:<10}{RESET}  {elapsed:.1f}s")
    print(f"{BOLD}{'-' * 54}{RESET}")

    summary_color = GREEN if failed_count == 0 else RED
    print(
        f"  {summary_color}{BOLD}共 {total} 项  "
        f"通过 {passed_count}  失败 {failed_count}  "
        f"总耗时 {total_time:.1f}s{RESET}"
    )
    print(f"{BOLD}{'=' * 54}{RESET}\n")

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
