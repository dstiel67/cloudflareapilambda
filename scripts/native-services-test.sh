#!/bin/bash
# Native Services Test - Run services without Docker
# Starts Atom Store and Read Flags Service natively

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Native Services Test (No Docker Required)             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Check prerequisites
print_step "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 20+"
    exit 1
fi
print_success "Node.js installed: $(node --version)"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.11+"
    exit 1
fi
print_success "Python installed: $(python3 --version)"

if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install npm"
    exit 1
fi
print_success "npm installed: $(npm --version)"

echo ""

# Setup Atom Store
print_step "Setting up Atom Store..."

if [ ! -d "atom_store/server/node_modules" ]; then
    print_info "Installing Atom Store dependencies..."
    cd atom_store/server
    npm install > /dev/null 2>&1
    cd ../..
    print_success "Dependencies installed"
else
    print_success "Dependencies already installed"
fi

# Setup Read Flags Service
print_step "Setting up Read Flags Service..."

if ! python3 -c "import boto3" 2>/dev/null; then
    print_info "Installing Read Flags Service dependencies..."
    pip3 install -r read_flags_service/requirements.txt > /dev/null 2>&1
    print_success "Dependencies installed"
else
    print_success "Dependencies already installed"
fi

echo ""

# Instructions
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  Services Ready to Start                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Open 3 terminal windows and run:"
echo ""
echo "Terminal 1 - Atom Store:"
echo "  cd atom_store/server"
echo "  npm start"
echo ""
echo "Terminal 2 - Read Flags Service:"
echo "  cd read_flags_service"
echo "  export DYNAMODB_TABLE_NAME=failover-status"
echo "  export ATOM_STORE_URL=http://localhost:3000"
echo "  export POLLING_INTERVAL=10"
echo "  export AWS_REGION=us-east-1"
echo "  python service.py"
echo ""
echo "Terminal 3 - Test Commands:"
echo "  # Update DynamoDB"
echo "  aws dynamodb put-item --table-name failover-status --item '{"
echo "    \"pk\": {\"S\": \"FAILOVER_STATUS\"},"
echo "    \"sk\": {\"S\": \"CURRENT\"},"
echo "    \"test_Failover\": {\"S\": \"Y\"}"
echo "  }'"
echo ""
echo "  # Check Atom Store"
echo "  curl http://localhost:3000/api/failover/status | jq"
echo ""
echo "Or use tmux to run all in one window:"
echo "  ./scripts/start-native-services-tmux.sh"
echo ""
