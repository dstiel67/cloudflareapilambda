#!/bin/bash
# Start all services in tmux (no Docker required)

set -e

SESSION="failover-test"

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux not found. Install with:"
    echo "  macOS: brew install tmux"
    echo "  Ubuntu: sudo apt install tmux"
    echo "  Or run services manually in separate terminals"
    exit 1
fi

# Kill existing session if it exists
tmux kill-session -t $SESSION 2>/dev/null || true

# Create new session
tmux new-session -d -s $SESSION

# Window 1: Atom Store
tmux rename-window -t $SESSION:0 'Atom Store'
tmux send-keys -t $SESSION:0 'cd atom_store/server' C-m
tmux send-keys -t $SESSION:0 'npm start' C-m

# Window 2: Read Flags Service
tmux new-window -t $SESSION:1 -n 'Read Flags'
tmux send-keys -t $SESSION:1 'cd read_flags_service' C-m
tmux send-keys -t $SESSION:1 'export DYNAMODB_TABLE_NAME=failover-status' C-m
tmux send-keys -t $SESSION:1 'export ATOM_STORE_URL=http://localhost:3000' C-m
tmux send-keys -t $SESSION:1 'export POLLING_INTERVAL=10' C-m
tmux send-keys -t $SESSION:1 'export AWS_REGION=us-east-1' C-m
tmux send-keys -t $SESSION:1 'python service.py' C-m

# Window 3: Test Commands
tmux new-window -t $SESSION:2 -n 'Test'
tmux send-keys -t $SESSION:2 'echo "Services starting... wait 10 seconds"' C-m
tmux send-keys -t $SESSION:2 'sleep 10' C-m
tmux send-keys -t $SESSION:2 'echo ""' C-m
tmux send-keys -t $SESSION:2 'echo "Test commands:"' C-m
tmux send-keys -t $SESSION:2 'echo "  1. Update DynamoDB: aws dynamodb put-item --table-name failover-status --item '"'"'{\"pk\":{\"S\":\"FAILOVER_STATUS\"},\"sk\":{\"S\":\"CURRENT\"},\"test_Failover\":{\"S\":\"Y\"}}'"'"'"' C-m
tmux send-keys -t $SESSION:2 'echo "  2. Check Atom Store: curl http://localhost:3000/api/failover/status | jq"' C-m
tmux send-keys -t $SESSION:2 'echo ""' C-m

# Attach to session
echo "Starting services in tmux..."
echo ""
echo "Tmux commands:"
echo "  Switch windows: Ctrl+b then 0/1/2"
echo "  Detach: Ctrl+b then d"
echo "  Kill session: tmux kill-session -t $SESSION"
echo ""
sleep 2

tmux attach-session -t $SESSION
