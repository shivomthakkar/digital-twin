"""
Generic Lambda deployment packager.

Run from any Python service directory:
    uv run deploy.py

Dependency install: Docker (linux/amd64 Lambda image) if requirements.txt exists.
Source files: everything NOT excluded by the local .gitignore, or a built-in
default list when no .gitignore is found.
"""

import fnmatch
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Exclusion configuration
# ---------------------------------------------------------------------------

# Hard-excluded regardless of .gitignore — deploy artifacts and runtime noise.
ALWAYS_EXCLUDE = frozenset([
    "lambda-package",
    "lambda-deployment.zip",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "deploy.py",  # this script itself
])

# Patterns used when no local .gitignore is found.
# Covers standard files a Python Lambda service doesn't need at runtime.
DEFAULT_EXCLUDES = [
    "*.pyc", "*.pyo", "*.pyd",
    ".env", ".env.*",
    ".python-version",
    "uv.lock", "poetry.lock", "*.lock",
    "requirements.txt",
    "pyproject.toml",
    "run.sh",
    "test_events",
    "test_*.py", "*_test.py",
    "*.md",
    ".gitignore",
    "Makefile",
]

# ---------------------------------------------------------------------------
# Gitignore parser
# ---------------------------------------------------------------------------

def _parse_gitignore(path):
    """Return (exclude_patterns, include_patterns) from a .gitignore file."""
    excludes, includes = [], []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("!"):
                includes.append(line[1:].rstrip("/"))
            else:
                excludes.append(line.rstrip("/"))
    return excludes, includes


def _matches(name, rel_path, patterns):
    """Return True if name or any component of rel_path matches a pattern."""
    parts = Path(rel_path).parts
    for pat in patterns:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_path, pat):
            return True
        # Component-level match (e.g. "__pycache__" hits deeply nested paths)
        if "/" not in pat and any(fnmatch.fnmatch(p, pat) for p in parts):
            return True
    return False


def _should_exclude(abs_path, base, excludes, includes):
    """Return True if abs_path should be left out of the Lambda package."""
    name = abs_path.name
    if name in ALWAYS_EXCLUDE:
        return True
    rel = str(abs_path.relative_to(base))
    if _matches(name, rel, excludes):
        return not _matches(name, rel, includes)  # negation can rescue
    return False


def _load_exclusions(base):
    gitignore = base / ".gitignore"
    if gitignore.exists():
        excludes, includes = _parse_gitignore(gitignore)
        print(f"  Using .gitignore ({len(excludes)} exclude, {len(includes)} include patterns).")
    else:
        excludes, includes = DEFAULT_EXCLUDES, []
        print("  No .gitignore found — using built-in default exclude list.")
    return excludes, includes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    base = Path.cwd()
    pkg_dir = base / "lambda-package"
    zip_path = base / "lambda-deployment.zip"

    print(f"📦 Building Lambda package for: {base.name}")

    # Clean previous build
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    if zip_path.exists():
        zip_path.unlink()
    pkg_dir.mkdir()

    # Install dependencies via Docker using the Lambda runtime image
    req_file = base / "requirements.txt"
    if req_file.exists():
        print("🐳 Installing dependencies (linux/amd64 Lambda image)...")
        subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{base}:/var/task",
                "--platform", "linux/amd64",
                "--entrypoint", "",
                "public.ecr.aws/lambda/python:3.12",
                "/bin/sh", "-c",
                (
                    "pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org "
                    "--target /var/task/lambda-package "
                    "-r /var/task/requirements.txt "
                    "--platform manylinux2014_x86_64 --only-binary=:all: --upgrade"
                ),
            ],
            check=True,
        )
    else:
        print("  No requirements.txt — skipping dependency install.")

    # Patch dhanhq base_url based on DHAN_MODE environment variable
    dhan_mode = os.environ.get("DHAN_MODE", "sandbox")
    dhan_config = {
        "sandbox": "https://sandbox.dhan.co/v2",
        "prod": "https://api.dhan.co/v2",
    }
    dhan_base_url = dhan_config.get(dhan_mode, dhan_config["prod"])
    
    dhanhq_file = pkg_dir / "dhanhq" / "dhanhq.py"
    if dhanhq_file.exists():
        print(f"🔧 Patching dhanhq base_url to {dhan_base_url} (DHAN_MODE={dhan_mode})...")
        with open(dhanhq_file, "r") as f:
            content = f.read()
        
        # Use regex to find and replace the self.base_url line flexibly
        # Matches: self.base_url = 'https://...' or "https://..." with optional whitespace
        pattern = r'(self\.base_url\s*=\s*)["\']https://[^"\']*["\']'
        replacement = f'\\1\'{dhan_base_url}\''
        
        if re.search(pattern, content):
            new_content = re.sub(pattern, replacement, content)
            with open(dhanhq_file, "w") as f:
                f.write(new_content)
            print(f"  ✓ dhanhq patched for {dhan_mode} mode")
        else:
            # Provide diagnostics if pattern not found
            print(f"  ⚠ Warning: Could not find expected dhanhq base_url line to patch")
            # Try to find similar lines for debugging
            if "self.base_url" in content:
                print(f"    (Found 'self.base_url' in file but pattern didn't match)")
                for i, line in enumerate(content.split('\n'), 1):
                    if "self.base_url" in line and "dhan.co" in line:
                        print(f"    Line {i}: {line.strip()}")
    else:
        print(f"  ⚠ Warning: dhanhq module not found in lambda-package (not installed?)")

    # Collect source files
    print("📂 Collecting source files...")
    excludes, includes = _load_exclusions(base)

    copied = []
    for item in sorted(base.iterdir()):
        if item.name == "lambda-package":
            continue
        if _should_exclude(item, base, excludes, includes):
            print(f"  skip  {item.name}")
            continue

        dest = pkg_dir / item.name
        if item.is_dir():
            shutil.copytree(
                item, dest,
                ignore=lambda d, names: {
                    n for n in names
                    if _should_exclude(Path(d) / n, base, excludes, includes)
                },
            )
        else:
            shutil.copy2(item, dest)
        copied.append(item.name)
        print(f"  copy  {item.name}")

    # Zip
    print("🗜  Creating lambda-deployment.zip...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(pkg_dir):
            for fname in files:
                fpath = Path(root) / fname
                zf.write(fpath, fpath.relative_to(pkg_dir))

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n✓ lambda-deployment.zip ({size_mb:.2f} MB)")
    print(f"  Source files packaged: {', '.join(copied)}")


if __name__ == "__main__":
    main()
