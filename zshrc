# Use powerline
USE_POWERLINE="true"
# Has weird character width
# Example:
#    is not a diamond
HAS_WIDECHARS="false"
# Source manjaro-zsh-configuration
if [[ -e /usr/share/zsh/manjaro-zsh-config ]]; then
  source /usr/share/zsh/manjaro-zsh-config
fi
# Use manjaro zsh prompt
if [[ -e /usr/share/zsh/manjaro-zsh-prompt ]]; then
  source /usr/share/zsh/manjaro-zsh-prompt
fi

# greet + sync pacman packages (once a day)

source ~/dotfiles/once_per_day.sh

run_once_per_day "figlet Hello $(whoami) !"
run_once_per_day "sudo pacman -Syu"

eval "$(fzf --zsh)"

# functions

# Function for 'python environment switching'
pe_function() {
    # Get the list of files in the current directory
    files=(/home/praneet/workspace/code/python/venv/*)

    echo "Please select an environment:"

    select file in "${files[@]}"; do
        if [[ -n $file ]]; then
	    
            echo "You selected environment: $file"
            # Perform an action with the selected file
            # For example, display the file's contents
            source $file/bin/activate
            break
        else
            echo "Invalid selection. Please try again."
        fi
    done
}

# Create alias 'pe' to call the function
alias pe="pe_function"


# alias
alias vi='vim'
alias nano='vim'
alias editor='vim'
alias peds='source /home/praneet/workspace/code/python/venv/data-science/bin/activate' #python environment data-science (peds)


# env variable updates

export PATH=$PATH:/home/praneet/Android/Sdk/platform-tools
