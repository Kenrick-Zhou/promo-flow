"""检查后端源码中使用的第三方依赖是否都已声明。

默认扫描：
  - backend/app/**/*.py
  - backend/alembic/**/*.py
  - scripts/*.py

规则：
  - 跳过标准库、相对导入、以及本地包（app / alembic）
  - 只校验 `backend/pyproject.toml` 的生产依赖
  - 若某个 import 对应的顶层模块没有被任何已声明依赖提供，则视为遗漏

用法：
    uv run --directory backend python ../scripts/check_backend_dependencies.py
    uv run --directory backend python ../scripts/check_backend_dependencies.py --verbose
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
PYPROJECT_FILE = BACKEND_ROOT / "pyproject.toml"

# 扫描后端运行时会触达的源码区域
SCAN_ROOTS: tuple[Path, ...] = (
    BACKEND_ROOT / "app",
    BACKEND_ROOT / "alembic",
    PROJECT_ROOT / "scripts",
)

# 本地模块名：这些不是第三方依赖
LOCAL_TOP_LEVEL_MODULES = {"app", "alembic"}


@dataclass(frozen=True)
class ImportFinding:
    module: str
    path: Path
    line: int


def canonical_dist_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_declared_distribution_name(requirement: str) -> str:
    """从 `pyproject.toml` dependency 字符串里提取发行包名。"""

    raw = requirement.split(";", 1)[0].strip()
    if not raw:
        return ""

    # 先去掉 extras，例如 `sqlalchemy[asyncio]>=2.0.36`
    raw = raw.split("[", 1)[0].strip()

    stop_chars = set("<>=!~ ")
    end = len(raw)
    for idx, ch in enumerate(raw):
        if ch in stop_chars:
            end = idx
            break

    return canonical_dist_name(raw[:end].strip())


def load_declared_distributions(pyproject_file: Path) -> set[str]:
    data = tomllib.loads(pyproject_file.read_text())
    project = data.get("project", {})
    deps = project.get("dependencies", [])
    return {
        dist
        for dist in (parse_declared_distribution_name(dep) for dep in deps)
        if dist
    }


def iter_python_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".py":
            yield root
            continue
        yield from root.rglob("*.py")


def top_level_name(module_name: str) -> str:
    return module_name.split(".", 1)[0]


def collect_imports(paths: Iterable[Path]) -> list[ImportFinding]:
    findings: list[ImportFinding] = []
    for path in paths:
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as exc:
            raise SystemExit(f"无法解析 {path}: {exc}") from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = top_level_name(alias.name)
                    findings.append(ImportFinding(module, path, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0 or not node.module:
                    continue
                module = top_level_name(node.module)
                findings.append(ImportFinding(module, path, node.lineno))
    return findings


def build_module_to_distributions() -> dict[str, set[str]]:
    mapping = metadata.packages_distributions()
    normalized: dict[str, set[str]] = {}
    for module, distributions in mapping.items():
        normalized[module] = {canonical_dist_name(dist) for dist in distributions}
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="检查后端源码是否遗漏生产依赖")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印每个 import 的解析结果",
    )
    args = parser.parse_args()

    declared_dists = load_declared_distributions(PYPROJECT_FILE)
    module_to_dists = build_module_to_distributions()
    stdlib_modules = set(sys.stdlib_module_names)

    python_files = list(iter_python_files(SCAN_ROOTS))
    findings = collect_imports(python_files)

    problems: list[str] = []
    seen_modules: set[str] = set()

    for finding in sorted(findings, key=lambda x: (x.module, str(x.path), x.line)):
        module = finding.module
        if module in seen_modules:
            # 仍然允许 verbose 输出，但问题只记录一次。
            pass
        seen_modules.add(module)

        if module in stdlib_modules or module in LOCAL_TOP_LEVEL_MODULES:
            continue

        providers = module_to_dists.get(module, set())
        declared_matches = providers & declared_dists

        if args.verbose:
            provider_text = ", ".join(sorted(providers)) if providers else "<未知>"
            declared_text = ", ".join(sorted(declared_matches)) if declared_matches else "<未声明>"
            print(
                f"{finding.path.relative_to(PROJECT_ROOT)}:{finding.line}  "
                f"import {module!r} -> providers={provider_text}  declared={declared_text}"
            )

        if not providers:
            problems.append(
                f"{finding.path.relative_to(PROJECT_ROOT)}:{finding.line} 使用了 {module!r}，"
                f"但当前环境里找不到它对应的发行包"
            )
            continue

        if not declared_matches:
            problems.append(
                f"{finding.path.relative_to(PROJECT_ROOT)}:{finding.line} 使用了 {module!r}，"
                f"对应发行包 {', '.join(sorted(providers))} 未在 backend/pyproject.toml 中声明"
            )

    if problems:
        print("\n依赖检查失败，发现以下遗漏：\n")
        for item in problems:
            print(f"- {item}")
        print("\n建议：使用 `uv add <package>` 补充依赖，然后重新生成 uv.lock。")
        return 1

    print(
        f"已检查 {len(python_files)} 个 Python 文件，"
        "未发现遗漏的生产依赖。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
