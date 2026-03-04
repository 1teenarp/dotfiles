"""fzf TUI launcher — builds the fzf command and execs it."""

import os
import sys

MANAGE_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manage.py")
PYTHON = sys.executable


def launch():
    """Build and exec the fzf-based model management console."""
    cmd = f"{PYTHON} {MANAGE_PY}"

    fzf_args = [
        "fzf", "--ansi",
        f"--header=Model Management Console (v2)",
        f"--preview={cmd} _internal preview {{-1}}",
        "--preview-window=right:50%:wrap",
        f"--bind=start:reload({cmd} _internal list)",
        f"--bind=enter:execute-silent({cmd} _internal toggle {{-1}})+reload({cmd} _internal list)",
        f"--bind=ctrl-s:execute-silent({cmd} _internal star {{-1}})+reload({cmd} _internal list)",
        f"--bind=ctrl-e:execute({cmd} _internal edit {{-1}})+reload({cmd} _internal list)",
        f"--bind=ctrl-l:execute({cmd} _internal logs {{-1}})",
        "--delimiter=|",
        "--with-nth=1,2",
        "--layout=reverse",
    ]

    os.execvp("fzf", fzf_args)
