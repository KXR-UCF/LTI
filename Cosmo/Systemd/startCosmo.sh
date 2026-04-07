#!/bin/bash

# Automates start of cosmo
# To run in command line: 'bash startCosmo.sh'
# To switch between tmux panes: 'crtl'+'b' followed by arrow key corresponding to pane direction
# Close an individual pane: type 'exit' in the pane's terminal
# Close tmux and trigger system shutdown: 'crtl'+'b' followed by 'd'

SESSION="cosmo"

# Paths
SOCKET_PATH="Cosmo_new"
BACKEND_PATH="Cosmo_new/Telemetry_visualization/Backend"
FRONTEND_PATH="Cosmo_new/Telemetry_visualization/Frontend/vite-project"

cleanup() {
    echo "Stopping system..."
    tmux kill-session -t "$SESSION" 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting Cosmo..."

# Kill old session
tmux kill-session -t "$SESSION" 2>/dev/null

# Create new session and first window
tmux new-session -d -s "$SESSION"

# Start backend in first pane
tmux send-keys -t "$SESSION:0" \
    "echo "Press Crtl+b and d to return to end the script"" C-m \
    "cd $BACKEND_PATH" C-m \
    "npm start" C-m

# Start socket client in new pane
tmux split-window -h -t "$SESSION"
tmux send-keys -t "$SESSION" \
    "echo "Press Crtl+b and d to return to end the script"" C-m \
    "cd $SOCKET_PATH" C-m \
    "python3 socket_client.py" C-m

# Start frontend in new window
tmux split-window -v -t "$SESSION"
tmux send-keys -t "$SESSION" \
    "echo "Press Crtl+b and d to return to end the script"" C-m \
    "cd $FRONTEND_PATH" C-m \
    "npm run dev" C-m

# Attach session
tmux attach-session -t "$SESSION"
wait
echo "Cosmo has been shut down"