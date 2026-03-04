# v2: Local AI Model Inference Manager

A Python rewrite of the bash-based inference management system. Manages local LLM/ML model services with a CLI, fzf TUI, and web dashboard.

## Quick Start

```bash
# Migrate existing v1 models
./manage.py migrate

# Add a new model
./manage.py add unsloth/Qwen3.5-0.8B-GGUF:UD-Q8_K_XL --backend llama --flag fa=on --flag ngl=999

# Start/stop/restart
./manage.py start qwen3.5-0.8b
./manage.py stop qwen3.5-0.8b

# Interactive TUI
./manage.py console

# Web dashboard
./manage.py serve
```

## Architecture

```
manage.py          CLI entry point (argparse) + fzf callback handler
config.py          Constants: paths, defaults, port range
registry.py        YAML registry CRUD, v1 migration, port auto-assign
cache.py           Cache scanner, orphan detection, deletion
console.py         fzf TUI launcher
app.py             Flask web dashboard
backends/
  __init__.py      BackendBase ABC + dispatch registry
  llama.py         tmux + llama-server
  vllm.py          docker run/stop/rm (nvcr.io/nvidia/vllm)
  whisper.py       tmux + whisper-server
  custom.py        tmux + arbitrary command
```

## Registry (`models.yaml`)

Models are stored in a v2 YAML schema:

```yaml
version: 2
port_range: [30000, 31000]

models:
  qwq32b:
    backend: llama
    repo: Qwen/QwQ-32B-GGUF
    port: 8198
    flags:
      fa: "on"
      temp: "1.0"
    starred: false
    added: "2026-03-03"
```

Key differences from v1: `type` renamed to `backend`, flags stored as a dict (not a raw string), starred status inline (not a separate file), `added` timestamp tracked.

### Auto-key generation

When adding a model, the key is derived from the repo name: strip the owner prefix, remove `-GGUF`/`-Instruct`/`-Chat`/`-it` suffixes, lowercase.

```
unsloth/Qwen3.5-122B-A10B-GGUF:Q5_K_S  ->  qwen3.5-122b-a10b
Qwen/QwQ-32B-GGUF                      ->  qwq-32b
```

### Auto-port assignment

Ports are allocated from `port_range` by scanning the registry for the next unused port.

## Backends

Each backend implements `start()`, `stop()`, `is_running()`, and `logs()`.

| Backend | Process model | Naming |
|---------|--------------|--------|
| `llama` | tmux session | `svc-<key>` |
| `vllm` | Docker container | `vllm-<key>` |
| `whisper` | tmux session | `svc-<key>` |
| `custom` | tmux session | `svc-<key>` |

**Flag serialization**: The flags dict is converted to CLI args. Single/double-char keys get a single dash, longer keys get double dash. Empty values produce bare flags.

```
{fa: "on", temp: "1.0", jinja: ""}  ->  -fa on --temp 1.0 --jinja
```

**vLLM**: Runs models via Docker with `--gpus all`, mounting `~/.cache/llama.cpp` as `/models:ro`. Override the image per-model with the `docker_image` field.

## CLI Reference

```
add <repo> [--backend llama|vllm|whisper|custom] [--key KEY] [--port PORT] [--flag k=v ...]
remove <key>
edit <key> [--flag k=v ...] [--port PORT]
start <key>
stop <key>
restart <key>
status [<key>]              # show running state for one or all models
list                        # show all registered models
console                     # launch fzf TUI
cache list                  # all cached models with sizes, grouped by repo
cache orphans               # cache entries not in the registry
cache clean [--dry-run]     # delete orphaned cache files (with confirmation)
serve                       # start Flask web dashboard on port 5000
migrate                     # one-time v1 -> v2 YAML migration
```

## fzf Console

The TUI is built by `console.py` which constructs an fzf command and `execvp`s it. All callbacks route through `manage.py _internal`:

| Key | Action |
|-----|--------|
| Enter | Toggle start/stop |
| Ctrl-S | Toggle star/favorite |
| Ctrl-E | Edit flags (opens `$EDITOR`) |
| Ctrl-L | View full logs |
| ESC | Exit |

Starred models sort to the top. The preview pane shows model details, current flags, and recent logs for running models.

## Cache Management

Scans `~/.cache/llama.cpp/` and groups files by `owner/repo` prefix (handles both flat filenames like `unsloth_Model-GGUF_file.gguf` and nested directory layouts). Cross-references against the registry to identify orphaned downloads.

```
$ ./manage.py cache list
REPO                                               FILES        SIZE  STATUS
-------------------------------------------------------------------------------------
AesSedai/Qwen3.5-122B-A10B-GGUF                        8     72.0 GB  ORPHANED
Qwen/QwQ-32B-GGUF                                      2     18.5 GB  REGISTERED
unsloth/Qwen3.5-122B-A10B-GGUF                        14    143.0 GB  REGISTERED
...
Total: 1.8 TB (23 registered, 65 orphaned)
```

`cache clean` deletes GGUF files, `.etag` files, and manifest files for orphaned groups, then removes empty directories.

## v1 Migration

`./manage.py migrate` reads the v1 `models.yaml` (one directory up) and `~/.model-favorites`, converts each entry to v2 format (parses flag strings into dicts, maps `type` to `backend`, inlines starred status), and writes to the v2 registry. Already-migrated keys are skipped.
