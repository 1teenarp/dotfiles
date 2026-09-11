# ~/.zshrc
# Portable by default. Machine-specific overrides live in ~/.zshrc.local
# and ~/.exports.local (both gitignored, written by install.sh or by hand).

# ---- shared exports & aliases ----
[ -f ~/.exports ] && source ~/.exports
[ -f ~/.exports.local ] && source ~/.exports.local
[ -f ~/.aliases ] && source ~/.aliases

# ---- Oh My Zsh (only if installed) ----
export ZSH="$HOME/.oh-my-zsh"
if [ -d "$ZSH" ]; then
  ZSH_THEME="robbyrussell"   # try "agnoster" or "powerlevel10k/powerlevel10k" later
  plugins=(git zsh-autosuggestions zsh-syntax-highlighting fzf)
  source "$ZSH/oh-my-zsh.sh"
fi

# ---- pyenv (only if installed) ----
if [ -d "$HOME/.pyenv" ]; then
  export PYENV_ROOT="$HOME/.pyenv"
  export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init -)"
fi

# ---- fzf ----
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# ---- general settings ----
setopt autocd
setopt correct
setopt hist_ignore_dups
HISTSIZE=50000
HISTFILE=~/.zsh_history
SAVEHIST=10000

export BAT_THEME='ansi'

# ---- machine-specific overrides (gitignored) ----
[ -f ~/.zshrc.local ] && source ~/.zshrc.local
