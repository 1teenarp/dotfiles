"""Cache scanner, grouping, orphan detection, and deletion."""

import os
from collections import defaultdict
from pathlib import Path

from config import CACHE_DIR
from registry import load


def _human_size(nbytes: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


def _extract_repo_group(filename: str) -> str:
    """Extract owner/repo-name from a flat cache filename.

    llama.cpp caches files as: owner_repo-name_quant_actual-file.gguf
    The first underscore-separated segment is owner, the second is repo-name.
    E.g. "unsloth_Qwen3.5-0.8B-GGUF_UD-Q8_K_XL_..." -> "unsloth/Qwen3.5-0.8B-GGUF"

    We detect the repo segment by looking for the GGUF-containing part.
    """
    parts = filename.split("_")
    if len(parts) < 2:
        return "(unknown)"

    owner = parts[0]
    # Find the repo segment — usually ends with -GGUF or contains GGUF
    # Reconstruct: some owners have nested names like "bartowski_Qwen_Qwen3.5-27B-GGUF"
    # Strategy: find the part containing "GGUF" or "-GGUF" and include everything up to it
    for i in range(1, len(parts)):
        if "GGUF" in parts[i]:
            repo = "_".join(parts[1:i+1])
            # Some repo names have nested owner like "bartowski_Qwen_Qwen3.5-27B-GGUF"
            # The first part is the HF owner, rest is the actual repo name
            return f"{owner}/{repo}"

    # Fallback: use first two segments
    return f"{owner}/{parts[1]}"


def scan_cache() -> dict[str, dict]:
    """Scan the llama.cpp cache directory and group files by repo.

    Handles both flat layout (files directly in cache dir with _ separators)
    and nested layout (owner/repo/file).

    Returns dict: {
        "owner/repo-name": {
            "files": [Path, ...],
            "size": int (bytes),
        }
    }
    """
    groups: dict[str, dict] = defaultdict(lambda: {"files": [], "size": 0})

    if not CACHE_DIR.exists():
        return dict(groups)

    # Check if files are flat (directly in cache dir) or nested
    for entry in CACHE_DIR.iterdir():
        if entry.is_file():
            # Flat layout — extract repo from filename
            group_key = _extract_repo_group(entry.name)
            groups[group_key]["files"].append(entry)
            groups[group_key]["size"] += entry.stat().st_size
        elif entry.is_dir():
            # Nested layout — walk subdirectories
            owner = entry.name
            for sub in entry.iterdir():
                if sub.is_dir():
                    group_key = f"{owner}/{sub.name}"
                    for f in sub.rglob("*"):
                        if f.is_file():
                            groups[group_key]["files"].append(f)
                            groups[group_key]["size"] += f.stat().st_size
                elif sub.is_file():
                    group_key = f"{owner}/{_extract_repo_group(sub.name).split('/', 1)[-1] if '/' in _extract_repo_group(sub.name) else sub.name}"
                    groups[group_key]["files"].append(sub)
                    groups[group_key]["size"] += sub.stat().st_size

    return dict(groups)


def _registered_repos(data: dict) -> set[str]:
    """Extract the set of repo prefixes (owner/name) from the registry."""
    repos = set()
    for cfg in data["models"].values():
        repo = cfg.get("repo", "")
        if "/" in repo:
            # Strip quant suffix
            base = repo.split(":")[0]
            repos.add(base)
    return repos


def find_orphans() -> list[tuple[str, dict]]:
    """Find cache groups not referenced by any registered model."""
    data = load()
    registered = _registered_repos(data)
    groups = scan_cache()

    orphans = []
    for group_key, info in sorted(groups.items()):
        if group_key not in registered:
            orphans.append((group_key, info))
    return orphans


def list_cache():
    """Print a table of all cached model groups with sizes and status."""
    data = load()
    registered = _registered_repos(data)
    groups = scan_cache()

    if not groups:
        print("Cache directory is empty or does not exist.")
        return

    total_size = 0
    total_registered = 0
    total_orphaned = 0

    print(f"{'REPO':<50} {'FILES':>5}  {'SIZE':>10}  {'STATUS'}")
    print("-" * 85)

    for group_key in sorted(groups.keys()):
        info = groups[group_key]
        size = info["size"]
        total_size += size
        n_files = len(info["files"])

        if group_key in registered:
            status = "REGISTERED"
            total_registered += 1
        else:
            status = "ORPHANED"
            total_orphaned += 1

        print(f"{group_key:<50} {n_files:>5}  {_human_size(size):>10}  {status}")

    print("-" * 85)
    print(f"Total: {_human_size(total_size)} ({total_registered} registered, {total_orphaned} orphaned)")


def list_orphans():
    """Print only orphaned cache entries."""
    orphans = find_orphans()
    if not orphans:
        print("No orphaned cache entries found.")
        return

    total_size = 0
    print(f"{'REPO':<50} {'FILES':>5}  {'SIZE':>10}")
    print("-" * 70)

    for group_key, info in orphans:
        size = info["size"]
        total_size += size
        print(f"{group_key:<50} {len(info['files']):>5}  {_human_size(size):>10}")

    print("-" * 70)
    print(f"Total orphaned: {_human_size(total_size)} ({len(orphans)} groups)")


def clean_orphans(dry_run: bool = False):
    """Delete orphaned cache groups."""
    orphans = find_orphans()
    if not orphans:
        print("No orphaned cache entries to clean.")
        return

    total_size = sum(info["size"] for _, info in orphans)
    total_files = sum(len(info["files"]) for _, info in orphans)

    print(f"Found {len(orphans)} orphaned groups ({total_files} files, {_human_size(total_size)})")

    if dry_run:
        print("\nDry run — would delete:")
        for group_key, info in orphans:
            print(f"  {group_key} ({len(info['files'])} files, {_human_size(info['size'])})")
        return

    confirm = input(f"\nDelete {total_files} files ({_human_size(total_size)})? [y/N] ")
    if confirm.lower() != "y":
        print("Aborted.")
        return

    deleted = 0
    for group_key, info in orphans:
        for fp in info["files"]:
            try:
                fp.unlink()
                deleted += 1
            except OSError as e:
                print(f"  Error deleting {fp}: {e}")

        # Try to remove empty parent directories
        if info["files"]:
            parent = info["files"][0].parent
            try:
                # Remove empty dirs up to cache root
                while parent != CACHE_DIR:
                    parent.rmdir()  # only succeeds if empty
                    parent = parent.parent
            except OSError:
                pass  # directory not empty, that's fine

    print(f"Deleted {deleted} files.")
