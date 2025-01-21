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
run_once_per_ndays "sudo pacman -Syu" 7

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
alias cat=bat
alias bye=namaste.sh
alias startkde=startplasma-x11

# env variable updates
export PATH=$PATH:~/dotfiles/
export PATH=$PATH:/home/praneet/Android/Sdk/platform-tools

# tools

# fooocus
alias fooocus='~/dotfiles/fooocus.sh'
alias fooocus-server='~/dotfiles/fooocus.sh listen'

# micromamba --------
# To activate this environment, use:
alias mamba='micromamba activate /home/praneet/workspace/tools/miniforge3'

# Or to execute a single command in this environment, use:

alias mamba-run=' micromamba run -p /home/praneet/workspace/tools/miniforge3 '

#If you'd prefer that conda's base environment not be activated on startup,
#   run the following command when conda is activated:
#conda config --set auto_activate_base false
#You can undo this by running `conda init --reverse $SHELL`? [yes|no]
#


