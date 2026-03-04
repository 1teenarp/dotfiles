#!/usr/bin/env python3
"""CLI entry point for the inference manager."""

import argparse
import os
import sys
import tempfile
import subprocess

# Ensure the v2 directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registry
from backends import get_backend, load_all_backends
from config import LOG_DIR


def cmd_add(args):
    flags = {}
    if args.flag:
        for f in args.flag:
            if "=" in f:
                k, v = f.split("=", 1)
                flags[k] = v
            else:
                flags[f] = ""
    key = registry.add_model(
        repo=args.repo,
        backend=args.backend,
        key=args.key,
        port=args.port,
        flags=flags,
    )
    data = registry.load()
    model = data["models"][key]
    print(f"Added '{key}' (port {model['port']}, backend {model['backend']})")


def cmd_remove(args):
    load_all_backends()
    data = registry.load()
    if args.key in data["models"]:
        backend = get_backend(args.key, data["models"][args.key])
        if backend.is_running():
            backend.stop()
    registry.remove_model(args.key)
    print(f"Removed '{args.key}'")


def cmd_edit(args):
    flags = {}
    if args.flag:
        for f in args.flag:
            if "=" in f:
                k, v = f.split("=", 1)
                flags[k] = v
            else:
                flags[f] = ""
    registry.edit_model(args.key, flags=flags or None, port=args.port)
    print(f"Updated '{args.key}'")


def cmd_start(args):
    load_all_backends()
    data = registry.load()
    if args.key not in data["models"]:
        print(f"Model '{args.key}' not found")
        sys.exit(1)
    backend = get_backend(args.key, data["models"][args.key])
    backend.start()
    print(f"Started '{args.key}' on port {data['models'][args.key]['port']}")


def cmd_stop(args):
    load_all_backends()
    data = registry.load()
    if args.key not in data["models"]:
        print(f"Model '{args.key}' not found")
        sys.exit(1)
    backend = get_backend(args.key, data["models"][args.key])
    backend.stop()
    print(f"Stopped '{args.key}'")


def cmd_restart(args):
    load_all_backends()
    data = registry.load()
    if args.key not in data["models"]:
        print(f"Model '{args.key}' not found")
        sys.exit(1)
    backend = get_backend(args.key, data["models"][args.key])
    backend.stop()
    backend.start()
    print(f"Restarted '{args.key}'")


def cmd_status(args):
    load_all_backends()
    data = registry.load()
    models = data.get("models", {})

    if args.key:
        if args.key not in models:
            print(f"Model '{args.key}' not found")
            sys.exit(1)
        models = {args.key: models[args.key]}

    print(f"{'KEY':<25} {'BACKEND':<8} {'PORT':>5}  {'STATUS'}")
    print("-" * 55)
    for key, cfg in models.items():
        backend = get_backend(key, cfg)
        status = "\033[32mACTIVE\033[0m" if backend.is_running() else "\033[90mIDLE\033[0m"
        print(f"{key:<25} {cfg['backend']:<8} {cfg['port']:>5}  {status}")


def cmd_list(args):
    data = registry.load()
    models = data.get("models", {})
    if not models:
        print("No models registered.")
        return

    print(f"{'KEY':<25} {'BACKEND':<8} {'PORT':>5}  {'REPO'}")
    print("-" * 80)
    for key, cfg in models.items():
        star = "\u2605 " if cfg.get("starred") else "  "
        print(f"{star}{key:<23} {cfg['backend']:<8} {cfg['port']:>5}  {cfg['repo']}")


def cmd_console(args):
    from console import launch
    launch()


def cmd_cache(args):
    import cache
    if args.cache_cmd == "list":
        cache.list_cache()
    elif args.cache_cmd == "orphans":
        cache.list_orphans()
    elif args.cache_cmd == "clean":
        cache.clean_orphans(dry_run=args.dry_run)


CATALOG_SESSION = "svc-catalog"


def _is_catalog_running() -> bool:
    result = subprocess.run(
        ["tmux", "list-sessions"], capture_output=True, text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith(f"{CATALOG_SESSION}:"):
            return True
    return False


def cmd_serve_catalog(args):
    action = getattr(args, "catalog_action", None)

    if action == "stop":
        if _is_catalog_running():
            subprocess.run(["tmux", "kill-session", "-t", CATALOG_SESSION], capture_output=True)
            print("Catalog server stopped.")
        else:
            print("Catalog server is not running.")
        return

    # Default: start
    if _is_catalog_running():
        print(f"Catalog server already running (tmux session: {CATALOG_SESSION})")
        return

    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    cmd = f"{sys.executable} {app_path}"
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", CATALOG_SESSION, cmd],
        check=True,
    )
    from config import FLASK_PORT
    print(f"Catalog server started on port {FLASK_PORT} (tmux session: {CATALOG_SESSION})")


def cmd_migrate(args):
    registry.migrate_v1()


# --- Internal fzf callbacks ---

def internal_list():
    """Output model list formatted for fzf."""
    load_all_backends()
    data = registry.load()
    models = data.get("models", {})

    # Sort: starred first, then alphabetical
    sorted_keys = sorted(models.keys(), key=lambda k: (not models[k].get("starred", False), k))

    for key in sorted_keys:
        cfg = models[key]
        backend = get_backend(key, cfg)

        star = "\033[33m\u2605\033[0m" if cfg.get("starred") else "\033[90m\u2606\033[0m"
        if backend.is_running():
            icon = "\033[32m\u25cf ACTIVE\033[0m"
        else:
            icon = "\033[90m\u25cb IDLE  \033[0m"

        # Fixed-width: name (25 chars, truncated with ellipsis) + star + status + key
        MAX_NAME = 25
        if len(key) > MAX_NAME:
            display_name = key[:MAX_NAME - 1] + "\u2026"
        else:
            display_name = key.ljust(MAX_NAME)

        # Format: "name star | status | key" — key is last field for {-1}
        print(f"{display_name} {star} | {icon} | {key}")


def internal_preview(key: str):
    """Generate preview content for fzf."""
    load_all_backends()
    data = registry.load()
    if key not in data["models"]:
        return

    cfg = data["models"][key]
    backend = get_backend(key, cfg)

    star = "\033[33m\u2605\033[0m" if cfg.get("starred") else "\033[90m\u2606\033[0m"
    status = "\033[32m\u25cf ACTIVE\033[0m" if backend.is_running() else "\033[90m\u25cb IDLE\033[0m"

    print(f"\033[1;34mModel:\033[0m {key} {star} {status}")
    print(f"\033[1;34mBackend:\033[0m {cfg['backend']} | \033[1;34mPort:\033[0m {cfg['port']}")
    print(f"\033[1;34mRepo :\033[0m {cfg['repo']}")
    print("-" * 42)
    print(f"\033[1;33mFlags (Edit with Ctrl-E):\033[0m")

    flags = cfg.get("flags", {})
    if flags:
        for k, v in flags.items():
            if v:
                print(f"  {k} = {v}")
            else:
                print(f"  {k}")
    else:
        print("  (none)")

    print("-" * 42)

    if backend.is_running():
        print(f"\033[1;36mRecent Logs (last 30 lines):\033[0m")
        print(backend.logs(30))

    print("-" * 42)
    print(f"\033[32mENTER\033[0m  : Toggle Start/Stop")
    print(f"\033[33mCTRL-S\033[0m : Toggle Star/Favorite")
    print(f"\033[35mCTRL-E\033[0m : Edit Flags")
    print(f"\033[36mCTRL-L\033[0m : View Full Logs")
    print(f"\033[31mESC\033[0m    : Exit Console")


def internal_toggle(key: str):
    """Toggle model start/stop."""
    load_all_backends()
    data = registry.load()
    if key not in data["models"]:
        return
    backend = get_backend(key, data["models"][key])
    if backend.is_running():
        backend.stop()
    else:
        backend.start()


def internal_star(key: str):
    """Toggle star status."""
    registry.toggle_star(key)


def internal_edit(key: str):
    """Open flags in editor for editing."""
    data = registry.load()
    if key not in data["models"]:
        return

    cfg = data["models"][key]
    flags = cfg.get("flags", {})

    # Write flags to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=f"_{key}_flags.txt", delete=False) as f:
        for k, v in flags.items():
            if v:
                f.write(f"{k}={v}\n")
            else:
                f.write(f"{k}\n")
        tmp_path = f.name

    editor = os.environ.get("EDITOR", "vim")
    subprocess.run([editor, tmp_path])

    # Parse back
    new_flags = {}
    with open(tmp_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                new_flags[k.strip()] = v.strip()
            else:
                new_flags[line.strip()] = ""

    os.unlink(tmp_path)
    registry.set_flags_raw(key, new_flags)


def internal_logs(key: str):
    """Show full logs in fzf preview."""
    load_all_backends()
    data = registry.load()
    if key not in data["models"]:
        return

    log_file = str(LOG_DIR / f"service-{key}.log")
    if not os.path.exists(log_file):
        print(f"No logs found for {key}")
        input("Press any key to continue...")
        return

    subprocess.run([
        "fzf", "--ansi", "--height=~80%",
        f"--preview=tail -100 {log_file}",
        "--preview-window=up:wrap",
        f"--header=Logs: {key} (ESC to close)",
        "--layout=reverse",
        "--bind=esc:abort",
        "--bind=q:abort",
    ])


def cmd_internal(args):
    action = args.action
    key = args.internal_key

    if action == "list":
        internal_list()
    elif action == "preview":
        internal_preview(key)
    elif action == "toggle":
        internal_toggle(key)
    elif action == "star":
        internal_star(key)
    elif action == "edit":
        internal_edit(key)
    elif action == "logs":
        internal_logs(key)
    else:
        print(f"Unknown internal action: {action}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Local AI Model Inference Manager",
        prog="manage.py",
    )
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="Add a model to the registry")
    p_add.add_argument("repo", help="HuggingFace repo (e.g. unsloth/Qwen3.5-0.8B-GGUF:Q8_K_XL)")
    p_add.add_argument("--backend", default="llama", choices=["llama", "vllm", "whisper", "custom"])
    p_add.add_argument("--key", help="Override auto-generated key")
    p_add.add_argument("--port", type=int, help="Override auto-assigned port")
    p_add.add_argument("--flag", action="append", help="Flag in k=v format (repeatable)")
    p_add.set_defaults(func=cmd_add)

    # remove
    p_rm = sub.add_parser("remove", help="Remove a model")
    p_rm.add_argument("key")
    p_rm.set_defaults(func=cmd_remove)

    # edit
    p_edit = sub.add_parser("edit", help="Edit a model's config")
    p_edit.add_argument("key")
    p_edit.add_argument("--flag", action="append", help="Flag in k=v format (repeatable)")
    p_edit.add_argument("--port", type=int)
    p_edit.set_defaults(func=cmd_edit)

    # start
    p_start = sub.add_parser("start", help="Start a model")
    p_start.add_argument("key")
    p_start.set_defaults(func=cmd_start)

    # stop
    p_stop = sub.add_parser("stop", help="Stop a model")
    p_stop.add_argument("key")
    p_stop.set_defaults(func=cmd_stop)

    # restart
    p_restart = sub.add_parser("restart", help="Restart a model")
    p_restart.add_argument("key")
    p_restart.set_defaults(func=cmd_restart)

    # status
    p_status = sub.add_parser("status", help="Show model status")
    p_status.add_argument("key", nargs="?", help="Specific model (default: all)")
    p_status.set_defaults(func=cmd_status)

    # list
    p_list = sub.add_parser("list", help="List all registered models")
    p_list.set_defaults(func=cmd_list)

    # console
    p_console = sub.add_parser("console", help="Launch fzf TUI")
    p_console.set_defaults(func=cmd_console)

    # cache
    p_cache = sub.add_parser("cache", help="Cache management")
    p_cache.add_argument("cache_cmd", choices=["list", "orphans", "clean"])
    p_cache.add_argument("--dry-run", action="store_true")
    p_cache.set_defaults(func=cmd_cache)

    # serve-catalog
    p_serve = sub.add_parser("serve-catalog", help="Start/stop Flask web dashboard in tmux")
    p_serve.add_argument("catalog_action", nargs="?", default="start", choices=["start", "stop"])
    p_serve.set_defaults(func=cmd_serve_catalog)

    # migrate
    p_migrate = sub.add_parser("migrate", help="Migrate v1 registry to v2")
    p_migrate.set_defaults(func=cmd_migrate)

    # _internal (fzf callbacks)
    p_internal = sub.add_parser("_internal")
    p_internal.add_argument("action", choices=["list", "preview", "toggle", "star", "edit", "logs"])
    p_internal.add_argument("internal_key", nargs="?", default="")
    p_internal.set_defaults(func=cmd_internal)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
