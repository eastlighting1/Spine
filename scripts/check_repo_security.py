from __future__ import annotations

import argparse
import ast
import re
import sys
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ["src", "tests", "examples", "docs", "scripts"]
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".pyi",
    ".toml",
    ".json",
    ".txt",
    ".yaml",
    ".yml",
}
BLOCKED_DIST_PATTERNS = ("__pycache__", ".pyc", ".pyo", ".venv", ".pytest_cache")
SECRET_PATTERNS = [
    re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"token\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
]
BLOCKED_IMPORTS = {"pickle", "marshal"}
BLOCKED_CALLS = {
    "eval",
    "exec",
    "os.system",
    "os.popen",
    "subprocess.run",
    "subprocess.call",
    "subprocess.Popen",
    "subprocess.check_call",
    "subprocess.check_output",
}


def iter_repo_files() -> list[Path]:
    files: list[Path] = []
    for dirname in SCAN_DIRS:
        base = ROOT / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {"__pycache__", ".venv", ".git", ".pytest_cache", "dist"} for part in path.parts):
                continue
            files.append(path)
    return files


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_files(errors: list[str], warnings: list[str]) -> None:
    if not (ROOT / "SECURITY.md").exists():
        errors.append("Missing SECURITY.md")
    if not (ROOT / "uv.lock").exists():
        errors.append("Missing uv.lock")
    if not (ROOT / "README.md").exists():
        errors.append("Missing README.md")
    if not (ROOT / "LICENSE").exists() and not (ROOT / "LICENSE.md").exists():
        warnings.append("Missing LICENSE file")


def check_for_secrets(files: list[Path], errors: list[str]) -> None:
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = read_text(path)
        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                errors.append(f"Potential secret pattern in {path.relative_to(ROOT)}: {match.group(0)[:80]}")


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def check_for_blocked_apis(files: list[Path], errors: list[str]) -> None:
    python_files = [path for path in files if path.suffix == ".py"]
    for path in python_files:
        tree = ast.parse(read_text(path), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in BLOCKED_IMPORTS:
                        errors.append(f"Blocked import '{alias.name}' in {path.relative_to(ROOT)}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                if node.module in BLOCKED_IMPORTS:
                    errors.append(f"Blocked import '{node.module}' in {path.relative_to(ROOT)}:{node.lineno}")
            elif isinstance(node, ast.Call):
                name = dotted_name(node.func)
                if name in BLOCKED_CALLS:
                    errors.append(f"Blocked call '{name}' in {path.relative_to(ROOT)}:{node.lineno}")


def function_contains_call(tree: ast.AST, func_name: str, target_name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and dotted_name(inner.func) == target_name:
                    return True
    return False


def check_deserializer_validation(errors: list[str]) -> None:
    canonical = ROOT / "src" / "spine" / "serialization" / "canonical.py"
    tree = ast.parse(read_text(canonical), filename=str(canonical))
    deserialize_functions = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("deserialize_")
    ]
    for name in deserialize_functions:
        if not function_contains_call(tree, name, "_validate_deserialized"):
            errors.append(f"{name} does not call _validate_deserialized in {canonical.relative_to(ROOT)}")


def check_compat_validation(errors: list[str]) -> None:
    reader = ROOT / "src" / "spine" / "compat" / "reader.py"
    text = read_text(reader)
    if "validate_project(project).raise_for_errors()" not in text:
        errors.append("read_compat_project is missing explicit validation")
    if "validate_artifact_manifest(manifest).raise_for_errors()" not in text:
        errors.append("read_compat_artifact_manifest is missing explicit validation")


def inspect_dist(errors: list[str], warnings: list[str]) -> None:
    dist_dir = ROOT / "dist"
    if not dist_dir.exists():
        warnings.append("dist/ not found; skipping distribution artifact inspection")
        return

    for artifact in dist_dir.iterdir():
        if artifact.suffix == ".whl":
            with zipfile.ZipFile(artifact) as zf:
                names = zf.namelist()
        elif artifact.suffixes[-2:] == [".tar", ".gz"]:
            with tarfile.open(artifact, "r:gz") as tf:
                names = tf.getnames()
        else:
            continue

        for name in names:
            if any(blocked in name for blocked in BLOCKED_DIST_PATTERNS):
                errors.append(f"Blocked artifact content '{name}' found in dist/{artifact.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-dist", action="store_true", help="Inspect built artifacts in dist/")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    files = iter_repo_files()
    check_required_files(errors, warnings)
    check_for_secrets(files, errors)
    check_for_blocked_apis(files, errors)
    check_deserializer_validation(errors)
    check_compat_validation(errors)
    if args.check_dist:
        inspect_dist(errors, warnings)

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("Security policy checks failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Repository security checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
