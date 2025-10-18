#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting environment setup..."

# --- Helper ---
command_exists() { command -v "$1" >/dev/null 2>&1; }

# --- ZSH INSTALLATION ---
if ! command_exists zsh; then
  echo "📦 Installing Zsh and essentials..."
  sudo apt update -y
  sudo apt install -y zsh curl git fonts-powerline
else
  echo "✅ Zsh already installed."
fi

# --- OH MY ZSH INSTALLATION ---
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  echo "💡 Installing Oh My Zsh..."
  RUNZSH=no CHSH=no KEEP_ZSHRC=yes sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
else
  echo "✅ Oh My Zsh already installed. Updating..."
  git -C "$HOME/.oh-my-zsh" pull
fi

# --- PLUGINS ---
ZSH_CUSTOM="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"

if [ ! -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]; then
  echo "💬 Installing zsh-autosuggestions..."
  git clone https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
else
  echo "✅ zsh-autosuggestions already installed. Updating..."
  git -C "$ZSH_CUSTOM/plugins/zsh-autosuggestions" pull || true
fi

if [ ! -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ]; then
  echo "🎨 Installing zsh-syntax-highlighting..."
  git clone https://github.com/zsh-users/zsh-syntax-highlighting.git "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"
else
  echo "✅ zsh-syntax-highlighting already installed. Updating..."
  git -C "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" pull || true
fi

# --- LINK DOTFILES ---
echo "🔗 Linking dotfiles..."
ln -sf ~/Workspace/github/dotfiles/.zshrc ~/.zshrc
ln -sf ~/Workspace/github/dotfiles/.aliases ~/.aliases
ln -sf ~/Workspace/github/dotfiles/.exports ~/.exports
ln -sf ~/Workspace/github/dotfiles/.gitconfig ~/.gitconfig
ln -sf ~/Workspace/github/dotfiles/.gitignore_global ~/.gitignore_global

# --- GIT CONFIGURATION ---
echo "🔧 Checking Git global configuration..."

git_name="$(git config --global user.name || true)"
git_email="$(git config --global user.email || true)"

if [ -z "$git_name" ] || [ -z "$git_email" ]; then
  echo "🧩 Git global identity not set. Let's configure it."
  
  # Ask for username
  read -rp "Enter your Git username: " git_name
  # Ask for email securely (input hidden)
  read -rsp "Enter your Git email: " git_email
  echo ""
  
  git config --global user.name "$git_name"
  git config --global user.email "$git_email"

  echo "✅ Git configured as:"
  echo "   Name:  $git_name"
  echo "   Email: $git_email"
else
  echo "✅ Git already configured:"
  echo "   Name:  $git_name"
  echo "   Email: $git_email"
fi

# --- SET DEFAULT SHELL ---
if [ "$SHELL" != "$(which zsh)" ]; then
  echo "🔄 Changing default shell to zsh..."
  chsh -s "$(which zsh)"
else
  echo "✅ Default shell already set to zsh."
fi

# --- FZF INSTALLATION ---
if [ ! -d "$HOME/.fzf" ]; then
  echo "🧭 Installing fzf..."
  git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
  yes | ~/.fzf/install --no-bash --no-fish --key-bindings --completion --update-rc
else
  echo "✅ fzf already installed, updating..."
  git -C ~/.fzf pull
  yes | ~/.fzf/install --no-bash --no-fish --key-bindings --completion --update-rc
fi

# Ensure latest fzf binary takes precedence
if ! grep -q 'export PATH="$HOME/.fzf/bin:$PATH"' "$HOME/.zshrc"; then
  echo 'export PATH="$HOME/.fzf/bin:$PATH"' >> "$HOME/.zshrc"
fi

# Clean up deprecated fzf lines
sed -i '/fzf --zsh/d' ~/.fzf.zsh || true

# --- ENSURE .zshrc SOURCES FZF ---
if ! grep -q '\[ -f ~/.fzf.zsh \] && source ~/.fzf.zsh' "$HOME/.zshrc"; then
  echo "🧩 Adding fzf sourcing to ~/.zshrc"
  cat <<'EOF' >> "$HOME/.zshrc"

# --- fzf setup ---
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
# --- end fzf setup ---
EOF
fi

# --- MONITORING TOOLS ---
echo "📊 Installing monitoring tools..."
sudo apt update -y

ARCH=$(uname -m)

# Always safe to install these
sudo apt install -y btop glances || true

# Conditionally install GPU/UI tools if supported
if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
  sudo apt install -y nvtop s-tui || echo "⚠️ Skipping nvtop/s-tui (not available on $ARCH)"
else
  echo "⚠️ Skipping nvtop/s-tui (unsupported on ARM architecture)"
fi

# --- TMUX INSTALLATION ---
if ! command_exists tmux; then
  echo "🧱 Installing tmux..."
  sudo apt install -y tmux
else
  echo "✅ tmux already installed."
fi

# Optional: install or update tmux plugin manager (TPM)
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
  echo "🔌 Installing tmux plugin manager..."
  git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
else
  echo "✅ tmux plugin manager already installed. Updating..."
  git -C ~/.tmux/plugins/tpm pull || true
fi

# --- OPTIONAL: AUTO-START TMUX ---
# Uncomment below to auto-start tmux session named "main"
# if [ -z "$TMUX" ]; then
#   tmux attach -t main || tmux new -s main
# fi

echo ""
echo "🎉 All done!"
echo "➡️  Restart your terminal or run: exec zsh"
echo "✨ You can run 'btop', 'htop', 'nvtop', or 'tmux' to monitor your system anytime."


