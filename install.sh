#!/usr/bin/env bash
# Cross-machine dotfiles installer.
# Uses GNU Stow to symlink packages into $HOME, detects the package manager,
# and keeps all private/machine-specific data out of the repo.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STOW_TARGET="$HOME"

say()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m==>\033[0m %s\n' "$*"; }

# --------------------------------------------------------------------------
# Package manager detection
# --------------------------------------------------------------------------
detect_pm() {
  for pm in apt pacman dnf zypper brew; do
    if command -v "$pm" >/dev/null 2>&1; then
      echo "$pm"
      return 0
    fi
  done
  echo "unknown"
}

install_pkgs() {
  case "$PM" in
    apt)    sudo apt update -y && sudo apt install -y "$@" ;;
    pacman) sudo pacman -S --noconfirm --needed "$@" ;;
    dnf)    sudo dnf install -y "$@" ;;
    zypper) sudo zypper install -y "$@" ;;
    brew)   brew install "$@" ;;
    *)
      warn "No supported package manager found. Install manually: $*"
      return 1
      ;;
  esac
}

PM="$(detect_pm)"
say "Detected package manager: $PM"

# --------------------------------------------------------------------------
# Core tools
# --------------------------------------------------------------------------
CORE=(stow git vim tmux bat)
say "Installing core tools: ${CORE[*]}"
install_pkgs "${CORE[@]}" || true

# --------------------------------------------------------------------------
# Oh My Zsh + plugins (guarded; requires zsh)
# --------------------------------------------------------------------------
if ! command -v zsh >/dev/null 2>&1; then
  say "Installing zsh..."
  install_pkgs zsh
fi

if [ ! -d "$HOME/.oh-my-zsh" ]; then
  say "Installing Oh My Zsh..."
  RUNZSH=no CHSH=no KEEP_ZSHRC=yes sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
else
  warn "Oh My Zsh already installed (skipping update)."
fi

ZSH_CUSTOM="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"
install_zsh_plugin() {
  local name="$1" url="$2"
  local dir="$ZSH_CUSTOM/plugins/$name"
  if [ ! -d "$dir" ]; then
    say "Installing zsh plugin: $name"
    git clone --depth 1 "$url" "$dir"
  else
    warn "zsh plugin $name already installed."
  fi
}
install_zsh_plugin zsh-autosuggestions https://github.com/zsh-users/zsh-autosuggestions
install_zsh_plugin zsh-syntax-highlighting https://github.com/zsh-users/zsh-syntax-highlighting

# --------------------------------------------------------------------------
# fzf
# --------------------------------------------------------------------------
if [ ! -d "$HOME/.fzf" ]; then
  say "Installing fzf..."
  git clone --depth 1 https://github.com/junegunn/fzf.git "$HOME/.fzf"
  "$HOME/.fzf/install" --all >/dev/null 2>&1 || true
else
  warn "fzf already installed."
fi

# --------------------------------------------------------------------------
# tmux plugin manager
# --------------------------------------------------------------------------
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
  say "Installing tmux plugin manager (TPM)..."
  git clone --depth 1 https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
fi

# --------------------------------------------------------------------------
# Stow symlinks
# --------------------------------------------------------------------------
# Back up any existing real files (not symlinks) that stow would replace, so
# the installer is safe and idempotent on machines with pre-existing configs.
BACKUP_DIR="$HOME/.dotfiles-backup-$(date +%Y%m%d-%H%M%S)"

backup_conflicts() {
  local pkg file target
  shopt -s dotglob nullglob
  for pkg in "$@"; do
    for file in "$REPO_DIR/$pkg"/*; do
      target="$HOME/$(basename "$file")"
      if [ -L "$target" ]; then
        continue                    # already a stow-managed symlink
      elif [ -e "$target" ]; then
        mkdir -p "$BACKUP_DIR"
        say "Backing up existing $target -> $BACKUP_DIR/"
        mv "$target" "$BACKUP_DIR/"
      fi
    done
  done
  shopt -u dotglob nullglob
}

backup_conflicts shell vim tmux git
say "Linking dotfiles with GNU Stow..."
stow -d "$REPO_DIR" -t "$STOW_TARGET" --verbose=2 shell vim tmux git

# --------------------------------------------------------------------------
# Machine-specific exports (private, written to ~/.exports.local)
# --------------------------------------------------------------------------
EXPORTS_LOCAL="$HOME/.exports.local"
if [ ! -f "$EXPORTS_LOCAL" ]; then
  say "Writing machine-specific exports to $EXPORTS_LOCAL"
  cat > "$EXPORTS_LOCAL" <<EOF
# Machine-specific exports (not tracked in git)
export DOTFILES_DIR="$REPO_DIR"
EOF
else
  warn "$EXPORTS_LOCAL already exists; leaving as-is (set DOTFILES_DIR manually if needed)."
fi

# --------------------------------------------------------------------------
# Git identity (private, written to ~/.gitconfig.local)
# --------------------------------------------------------------------------
GIT_LOCAL="$HOME/.gitconfig.local"
git_name="$(git config --global user.name || true)"
git_email="$(git config --global user.email || true)"

if [ -z "$git_name" ] || [ -z "$git_email" ]; then
  say "Git identity not set. Configuring $GIT_LOCAL..."
  read -rp "Enter your Git username: " git_name
  read -rsp "Enter your Git email: " git_email
  echo ""
  cat > "$GIT_LOCAL" <<EOF
[user]
	name = $git_name
	email = $git_email
EOF
else
  warn "Git identity already set (name=$git_name, email=$git_email)."
fi

# --------------------------------------------------------------------------
# Default shell
# --------------------------------------------------------------------------
if [ "$SHELL" != "$(command -v zsh)" ]; then
  say "Setting default shell to zsh..."
  chsh -s "$(command -v zsh)"
else
  warn "Default shell is already zsh."
fi

# --------------------------------------------------------------------------
# Done
# --------------------------------------------------------------------------
say "All done!"
warn "Start tmux once and press prefix + I to install TPM plugins."
warn "Restart your shell (exec zsh) for changes to take effect."
