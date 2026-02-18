#!/bin/bash

# --- CONFIGURATION ---
CONFIG_FILE="models.yaml"
LOG_DIR="/var/log/llama_cpp-inference"
SCRIPT_PATH="$(realpath "$0")"
FAVORITES_FILE="$HOME/.model-favorites"

export EDITOR="vim"
export LLAMA_LOG_COLORS=1
export LLAMA_LOG_PREFIX=1
export LLAMA_LOG_TIMESTAMPS=1

# --- START DIRECTORY APP ---
if ! tmux has-session -t "svc-directory" 2>/dev/null; then
  tmux new-session -d -s "svc-directory" "python3 $(dirname "$SCRIPT_PATH")/app.py"
  printf "[*] Model Hub Directory started on port 5000\n"
fi

mkdir -p "$LOG_DIR"

# --- INTERNAL PYTHON HELPERS ---
py_get() {
  python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_FILE'))['models']['$1'].get('$2', ''))" 2>/dev/null
}

py_set_flags() {
  python3 -c "import yaml;
data = yaml.safe_load(open('$CONFIG_FILE'));
data['models']['$1']['flags'] = '$2';
with open('$CONFIG_FILE', 'w') as f: yaml.dump(data, f, sort_keys=False)" 2>/dev/null
}

py_list_keys() {
  python3 -c "import yaml; print('\n'.join(yaml.safe_load(open('$CONFIG_FILE'))['models'].keys()))" 2>/dev/null
}

# --- FAVORITES MANAGEMENT ---
is_starred() {
  local KEY=$1
  [[ -f "$FAVORITES_FILE" ]] && grep -q "^${KEY}$" "$FAVORITES_FILE"
}

toggle_star() {
  local KEY=$1
  if is_starred "$KEY"; then
    grep -v "^${KEY}$" "$FAVORITES_FILE" >"$FAVORITES_FILE.tmp" 2>/dev/null
    mv "$FAVORITES_FILE.tmp" "$FAVORITES_FILE"
  else
    echo "$KEY" >>"$FAVORITES_FILE"
  fi
}

# --- SERVICE LOGIC ---

# Check if exact session is running (fixes partial matching bug)
is_session_running() {
  local KEY=$1
  tmux list-sessions 2>/dev/null | grep -q "^svc-${KEY}:"
}

launch_service() {
  local KEY=$1
  local TYPE=$(py_get "$KEY" "type")
  local REPO=$(py_get "$KEY" "repo")
  local PORT=$(py_get "$KEY" "port")
  local FLAGS=$(py_get "$KEY" "flags")

  local SESSION_NAME="svc-${KEY}"
  local LOG_FILE="$LOG_DIR/service-${KEY}.log"

  case "$TYPE" in
  LLAMA)
    local CMD_PATH="-hf $REPO"
    [[ "$REPO" == --* ]] && CMD_PATH="$REPO"
    tmux new-session -d -s "$SESSION_NAME" "llama-server $CMD_PATH --host 0.0.0.0 --port $PORT --ctx-size 0 --jinja -ub 2048 -b 2048 $FLAGS > $LOG_FILE 2>&1"
    ;;
  WHISPER)
    tmux new-session -d -s "$SESSION_NAME" "whisper-server -m $REPO --host 0.0.0.0 --port $PORT $FLAGS > $LOG_FILE 2>&1"
    ;;
  CUSTOM)
    tmux new-session -d -s "$SESSION_NAME" "bash -c '$REPO --host 0.0.0.0 --port $PORT $FLAGS' > $LOG_FILE 2>&1"
    ;;
  esac
}

# --- CLI DISPATCHER ---

case "$1" in
--internal-preview)
  KEY="$2"
  [[ -z "$KEY" ]] && exit 0

  if is_starred "$KEY"; then
    STAR_ICON="\e[33m★\e[0m"
  else
    STAR_ICON="\e[90m☆\e[0m"
  fi

  if is_session_running "$KEY"; then
    STATUS="\e[32m● ACTIVE\e[0m"
  else
    STATUS="\e[90m○ IDLE\e[0m"
  fi

  echo -e "\e[1;34mModel:\e[0m $KEY $STAR_ICON $STATUS"
  echo -e "\e[1;34mType :\e[0m $(py_get "$KEY" "type") | \e[1;34mPort:\e[0m $(py_get "$KEY" "port")"
  echo -e "\e[1;34mRepo :\e[0m $(py_get "$KEY" "repo")"
  echo "------------------------------------------"
  echo -e "\e[1;33mCurrent Flags (Edit with Ctrl-E):\e[0m"
  echo "$(py_get "$KEY" "flags")"
  echo "------------------------------------------"

  if is_session_running "$KEY"; then
    LOG_FILE="$LOG_DIR/service-${KEY}.log"
    if [[ -f "$LOG_FILE" ]]; then
      echo -e "\e[1;36mRecent Logs (last 30 lines):\e[0m"
      tail -30 "$LOG_FILE"
    fi
  fi

  echo "------------------------------------------"
  echo -e "\e[32mENTER\e[0m  : Toggle Start/Stop"
  echo -e "\e[33mCTRL-S\e[0m : Toggle Star/Favorite"
  echo -e "\e[35mCTRL-E\e[0m : Edit Flags"
  echo -e "\e[36mCTRL-L\e[0m : View Full Logs"
  echo -e "\e[31mESC\e[0m    : Exit Console"
  exit 0
  ;;
--internal-toggle)
  KEY="$2"
  if is_session_running "$KEY"; then
    tmux kill-session -t "svc-${KEY}"
  else
    launch_service "$KEY"
  fi
  exit 0
  ;;
--internal-edit)
  KEY="$2"
  TMP_FILE="/tmp/flags_$KEY"
  py_get "$KEY" "flags" >"$TMP_FILE"
  $EDITOR "$TMP_FILE"
  NEW_FLAGS=$(cat "$TMP_FILE" | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  py_set_flags "$KEY" "$NEW_FLAGS"
  rm "$TMP_FILE"
  exit 0
  ;;
--internal-star)
  KEY="$2"
  toggle_star "$KEY"
  exit 0
  ;;
--internal-logs)
  KEY="$2"
  LOG_FILE="$LOG_DIR/service-${KEY}.log"
  if [[ -f "$LOG_FILE" ]]; then
    fzf --ansi --height=~80% --preview="tail -100 $LOG_FILE" --preview-window=up:wrap \
      --header="Logs: $KEY (ESC to close)" --layout=reverse \
      --bind="esc:abort" --bind="q:abort"
  else
    echo "No logs found for $KEY"
    read -n 1
  fi
  exit 0
  ;;
--list-internal)
  # Output format: SORT_KEY|KEY (for fzf to parse properly)
  # Then we display with star icon in the list
  py_list_keys | while read -r KEY; do
    STAR_NUM=$(is_starred "$KEY" && echo "0" || echo "1")
    printf "%s|%s\n" "$STAR_NUM" "$KEY"
  done | sort -t'|' -k1,1n -k2,2 | cut -d'|' -f2 | while read -r KEY; do
    if is_starred "$KEY"; then
      STAR="\e[33m★\e[0m"
    else
      STAR="\e[90m☆\e[0m"
    fi

    if is_session_running "$KEY"; then
      ICON="\e[32m● ACTIVE\e[0m"
    else
      ICON="\e[90m○ IDLE  \e[0m"
    fi

    # Output: model name + star | status icon | key (so fzf can get the key with {3})
    printf "%s %b | %b | %s\n" "$KEY" "$STAR" "$ICON" "$KEY"
  done
  exit 0
  ;;
esac

# --- INTERFACE ---

fzf --ansi \
  --header="Model Management Console | Source: $CONFIG_FILE" \
  --preview="bash $SCRIPT_PATH --internal-preview {3}" \
  --preview-window="right:50%:wrap" \
  --bind "start:reload(bash $SCRIPT_PATH --list-internal)" \
  --bind "enter:execute-silent(bash $SCRIPT_PATH --internal-toggle {3})+reload(bash $SCRIPT_PATH --list-internal)" \
  --bind "ctrl-s:execute-silent(bash $SCRIPT_PATH --internal-star {3})+reload(bash $SCRIPT_PATH --list-internal)" \
  --bind "ctrl-e:execute(bash $SCRIPT_PATH --internal-edit {3})+reload(bash $SCRIPT_PATH --list-internal)" \
  --bind "ctrl-l:execute(bash $SCRIPT_PATH --internal-logs {3})" \
  --delimiter="\|" \
  --with-nth=1,2 \
  --layout=reverse
