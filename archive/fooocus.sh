#!/bin/bash

source /home/praneet/workspace/code/ai/Fooocus/fooocus_env/bin/activate
pip install -r /home/praneet/workspace/code/ai/Fooocus/requirements_versions.txt

pip uninstall torch torchvision torchaudio torchtext functorch xformers 
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.6

# Check if $1 is empty
if [ -z "$1" ]; then
  python3 /home/praneet/workspace/code/ai/Fooocus/entry_with_update.py
else
  python3 /home/praneet/workspace/code/ai/Fooocus/entry_with_update.py --$1
fi

bye
