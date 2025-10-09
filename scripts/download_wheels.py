# python scripts/download_wheels.py --platform win_amd64 --python-version 3.13 --abi cp313
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import tomllib


def read_project_dependencies(pyproject_path: Path) -> list[str]:
    with pyproject_path.open("rb") as fp:
        data = tomllib.load(fp)
    return list(data.get("project", {}).get("dependencies", []))


def deduplicate(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def build_pip_command(
    dest: Path,
    packages: list[str],
    *,
    platform_tag: str | None,
    python_version: str | None,
    abi_tag: str | None,
    implementation: str | None,
) -> list[str]:
    command: list[str] = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--dest",
        str(dest),
        "--only-binary",
        ":all:",
    ]
    if platform_tag:
        command.extend(["--platform", platform_tag])
    if python_version:
        command.extend(["--python-version", python_version])
    if abi_tag:
        command.extend(["--abi", abi_tag])
    if implementation:
        command.extend(["--implementation", implementation])
    command.extend(packages)
    return command


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download project wheels (including pip/setuptools/wheel) into resource/wheels."
    )
    parser.add_argument("--pyproject", default="pyproject.toml", type=Path)
    parser.add_argument("--dest", default=Path("resource") / "wheels", type=Path)
    parser.add_argument("--platform", dest="platform_tag")
    parser.add_argument("--python-version")
    parser.add_argument("--abi", dest="abi_tag")
    parser.add_argument("--implementation", default="cp")
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        help="Additional requirement specifiers to download.",
    )
    args = parser.parse_args()

    if not args.pyproject.is_file():
        parser.error(f"pyproject not found: {args.pyproject}")

    requirements = read_project_dependencies(args.pyproject)
    requirements.extend(["pip", "setuptools", "wheel"])
    requirements.extend(args.extra)
    packages = deduplicate(requirements)

    args.dest.mkdir(parents=True, exist_ok=True)

    command = build_pip_command(
        dest=args.dest,
        packages=packages,
        platform_tag=args.platform_tag,
        python_version=args.python_version,
        abi_tag=args.abi_tag,
        implementation=args.implementation,
    )

    print("Running:", " ".join(command))
    subprocess.check_call(command)


if __name__ == "__main__":
    main()