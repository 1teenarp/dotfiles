#!/bin/bash

# Default values
PORT=22
CLEANUP=false
HELP=false

# Print help message
print_help() {
    echo "Usage: manage_ssh_server.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --port <port>       Set the SSH server port (default: 22)."
    echo "  --start             Start the SSH server as a blocking thread."
    echo "  --stop              Stop the SSH server."
    echo "  --cleanup           Clean up the SSH setup (disable and remove configurations)."
    echo "  --help              Show this help message."
    echo ""
    echo "Examples:"
    echo "  ./manage_ssh_server.sh --port 2222 --start"
    echo "  ./manage_ssh_server.sh --stop"
    echo "  ./manage_ssh_server.sh --cleanup"
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --port) PORT="$2"; shift ;;
        --start) ACTION="start" ;;
        --stop) ACTION="stop" ;;
        --cleanup) CLEANUP=true ;;
        --help) HELP=true ;;
        *) echo "Unknown option: $1"; print_help; exit 1 ;;
    esac
    shift
done

# Display help and exit
if [ "$HELP" = true ]; then
    print_help
    exit 0
fi

# Start SSH server
start_ssh_server() {
    echo "Starting SSH server on port $PORT..."
    sudo sed -i "s/^Port 2222/Port $PORT/" /etc/ssh/sshd_config
    sudo systemctl restart sshd
    echo "SSH server started on port $PORT."
    echo "Press Ctrl+C to stop the server."
    sudo journalctl -f -u sshd  # Blocking thread to monitor SSH logs
}

# Stop SSH server
stop_ssh_server() {
    echo "Stopping SSH server..."
    sudo systemctl stop sshd
    echo "SSH server stopped."
}

# Clean up SSH setup
cleanup_ssh() {
    echo "Cleaning up SSH setup..."
    sudo systemctl disable sshd
    sudo pacman -R openssh --noconfirm
    echo "SSH setup cleaned up."
}

# Main logic
case $ACTION in
    start)
        start_ssh_server
        ;;
    stop)
        stop_ssh_server
        ;;
    *)
        if [ "$CLEANUP" = true ]; then
            cleanup_ssh
        else
            echo "No valid action specified. Use --help for usage details."
        fi
        ;;
esac

