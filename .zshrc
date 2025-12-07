# ~/.zshrc

# Load exports and aliases
[ -f ~/.exports ] && source ~/.exports
[ -f ~/.aliases ] && source ~/.aliases

# Add local bin to PATH

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"


export PATH="$HOME/.local/bin:$PATH"

# Poetry, pyenv, etc.
#if command -v pyenv &>/dev/null; then
#  eval "$(pyenv init -)"
#fi

#if command -v poetry &>/dev/null; then
#  export PATH="$HOME/.local/bin:$PATH"
#fi

# Prompt (if using Powerlevel10k)
# [[ -f ~/.p10k.zsh ]] && source ~/.p10k.zsh

# --- Oh My Zsh initialization ---
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"  # try "agnoster" or "powerlevel10k/powerlevel10k" later

# Add the plugins you want Oh My Zsh to manage
plugins=(
  git
  zsh-autosuggestions
  zsh-syntax-highlighting
  fzf
)

# Load Oh My Zsh
source $ZSH/oh-my-zsh.sh
# --- End Oh My Zsh section ---


# fzf
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh


# General settings
setopt autocd
setopt correct
setopt hist_ignore_dups
HISTFILE=~/.zsh_history
SAVEHIST=10000

