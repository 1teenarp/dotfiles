#!/bin/bash

# Function to execute a command once per day
run_once_per_day() {
    # The command to be run
    local COMMAND="$1"

    # Directory to store the logs for each command (you can customize this path)
    local LOG_DIR="$HOME/.once_per_day_logs"
    mkdir -p "$LOG_DIR"

    # Generate a unique filename based on the command
    local COMMAND_HASH=$(echo -n "$COMMAND" | md5sum | cut -d' ' -f1)
    local LOG_FILE="$LOG_DIR/$COMMAND_HASH.log"

    # Get the current date
    local CURRENT_DATE=$(date +"%Y-%m-%d")

    # Check if the log file exists and read the date from it
    if [ -f "$LOG_FILE" ]; then
        LAST_RUN_DATE=$(cat "$LOG_FILE")
    else
        LAST_RUN_DATE=""
    fi

    # Run the command if it hasn't run today
    if [ "$LAST_RUN_DATE" != "$CURRENT_DATE" ]; then
        echo "Running command: $COMMAND"
        eval "$COMMAND"

        # Update the log file with the current date
        echo "$CURRENT_DATE" > "$LOG_FILE"
    else
        echo "Command '$COMMAND' has already been run today. Skipping."
    fi
}

