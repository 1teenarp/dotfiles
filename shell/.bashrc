# ~/.bashrc
# If not running interactively, don't do anything (leave this at the top)
[[ $- != *i* ]] && return

# Shared aliases & exports (portable)
[ -f ~/.aliases ] && source ~/.aliases
[ -f ~/.exports ] && source ~/.exports
[ -f ~/.exports.local ] && source ~/.exports.local

list() {
  fzf -m --preview '[[ $(file --mime {}) =~ binary ]] && echo {} is a binary file || bat --style=numbers --color=always {}' | xargs -r ls -lha
}

fshow() {
  git log --graph --color=always \
      --format="%C(auto)%h%d %s %C(black)%C(bold)%cr" "$@" |
  fzf --ansi --no-sort --reverse --tiebreak=index --bind=ctrl-s:toggle-sort \
      --bind "ctrl-m:execute:
                (grep -o '[a-f0-9]\{7\}' | head -1 |
                xargs -I % sh -c 'git show --color=always % | less -R') << 'FZF-EOF'
                {}
FZF-EOF"
}

# Machine-specific overrides (gitignored)
[ -f ~/.bashrc.local ] && source ~/.bashrc.local
