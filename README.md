# dotfiles

Cross-machine dotfiles managed with [GNU Stow](https://www.gnu.org/software/stow/).
Portable by default; machine-specific bits live in gitignored `.local` files.

## Structure

```
install.sh          Portable bootstrap: detects OS, installs tools, runs Stow
shell/              Stow package -> $HOME  (.zshrc, .bashrc, .aliases, .exports)
vim/                Stow package -> $HOME  (.vimrc)
tmux/               Stow package -> $HOME  (.tmux.conf)
git/                Stow package -> $HOME  (.gitconfig, .gitignore_global)
archive/            Old / superseded scripts kept for reference
```

Each `*/` directory is a Stow package: its files mirror the home directory and
are symlinked there. Enable/disable a package independently with:

```bash
stow -d . -t ~ shell vim tmux git   # link
stow -D -d . -t ~ shell             # unlink just 'shell'
```

## Install

```bash
git clone <this-repo> ~/dotfiles
cd ~/dotfiles
./install.sh
```

The installer:
- Detects the package manager (apt / pacman / dnf / zypper / brew) and installs
  stow, git, vim, tmux, bat (plus zsh, oh-my-zsh plugins, fzf, TPM).
- Runs Stow to link all packages into `$HOME`.
- Writes private, machine-specific files that are **never committed**:
  - `~/.exports.local` — machine env (`DOTFILES_DIR`, extra `PATH`s)
  - `~/.gitconfig.local` — your git name/email (prompted once)

## Per-machine customization

Portable config sources a gitignored `.local` file at the end, so you can add
machine-specific settings without touching tracked files:

| Portable (tracked) | Machine-specific (gitignored) |
|--------------------|-------------------------------|
| `~/.zshrc`         | `~/.zshrc.local`, `~/.exports.local` |
| `~/.bashrc`        | `~/.bashrc.local`, `~/.exports.local` |
| `~/.gitconfig`     | `~/.gitconfig.local` |

Example `~/.zshrc.local`:

```zsh
export PATH="$HOME/.local/bin:$PATH"
alias ll='ls -alF'
```

After editing `.local` files, `exec zsh` to reload. When tmux starts, press
`prefix + I` (prefix is `Ctrl-a`) to install TPM plugins.
