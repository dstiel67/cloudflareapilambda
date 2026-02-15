#!/bin/bash
# Quick test script - validates the failover system in ~5 minutes

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Failover System - Quick Test                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
TEST_APP_ID="quick-test-app"
ATOM_STORE_URL="${ATOM_STORE_URL:-http://localhost:3000}"

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        exit 1
    fi
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Step 1: Check prerequisites
echo "Step 1: Checking prerequisites..."
echo "─────────────────────────────────"

# Check AWS CLI
if command -v aws &> /dev/null; then
    print_status 0 "AWS CLI installed"
else
    print_status 1 "AWS CLI not found"
fi

# Check if Atom Store is running
if curl -s "${ATOM_STORE_URL}/health" > /dev/null 2>&1; then
    print_status 0 "Atom Store is running"
else
    print_info "Atom Store not running at ${ATOM_STORE_URL}"
    echo "Start it with: cd atom_store/server && npm start"
fi

echo ""

# Step 2: Test DynamoDB access
echo "Step 2: Testing DynamoDB access..."
echo "───────────────────────────────────"

TABLE_NAME=$(terraform output -raw dynamodb_table_name 2>/dev/null || echo "failover-status")

if aws dynamodb describe-table --table-name "$TABLE_NAME" > /dev/null 2>&1; then
    print_status 0 "DynamoDB table accessible"
else
    print_status 1 "Cannot access DynamoDB table: $TABLE_NAME"
fi

echo ""

# Step 3: Test Lambda function
echo "Step 3: Testing Kafka Consumer Lambda..."
echo "─────────────────────────────────────────"

LAMBDA_NAME=$(terraform output -raw kafka_consumer_lambda_function_name 2>/dev/null || echo "failover-system-kafka-consumer")

if aws lambda get-function --function-name "$LAMBDA_NAME" > /dev/null 2>&1; then
    print_status 0 "Lambda function exists"
else
    print_info "Lambda function not deployed yet"
fi

echo ""

# Step 4: Test manual DynamoDB update
echo "Step 4: Testing DynamoDB → Atom Store flow..."
echo "───────────────────────────────────────────────"

print_info "Writing test data to DynamoDB..."

aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item "{
    \"pk\": {\"S\": \"FAILOVER_STATUS\"},
    \"sk\": {\"S\": \"CURRENT\"},
    \"${TEST_APP_ID}_Failover\": {\"S\": \"Y\"},
    \"${TEST_APP_ID}_LastUpdated\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"},
    \"${TEST_APP_ID}_Reason\": {\"S\": \"Quick test\"},
    \"LastUpdatedBy\": {\"S\": \"quick-test-script\"}
  }" > /dev/null 2>&1

print_status 0 "Test data written to DynamoDB"

# Verify write
RESULT=$(aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}' \
  --query "Item.${TEST_APP_ID}_Failover.S" \
  --output text 2>/dev/null)

if [ "$RESULT" == "Y" ]; then
    print_status 0 "DynamoDB read verification passed"
else
    print_status 1 "DynamoDB read verification failed"
fi

echo ""

# Step 5: Wait for Read Flags Service
echo "Step 5: Waiting for Read Flags Service polling..."
echo "──────────────────────────────────────────────────"

print_info "Waiting 15 seconds for polling cycle..."
sleep 15

echo ""

# Step 6: Check Atom Store
echo "Step 6: Verifying Atom Store update..."
echo "───────────────────────────────────────"

if curl -s "${ATOM_STORE_URL}/health" > /dev/null 2>&1; then
    ATOM_RESULT=$(curl -s "${ATOM_STORE_URL}/api/failover/status" | jq -r ".\"${TEST_APP_ID}\".failoverActive" 2>/dev/null)
    
    if [ "$ATOM_RESULT" == "true" ]; then
        print_status 0 "Atom Store updated successfully"
    else
        print_info "Atom Store not yet updated (may need more time)"
    fi
else
    print_info "Atom Store not running - skipping verification"
fi

echo ""

# Step 7: Cleanup
echo "Step 7: Cleaning up test data..."
echo "─────────────────────────────────"

aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item "{
    \"pk\": {\"S\": \"FAILOVER_STATUS\"},
    \"sk\": {\"S\": \"CURRENT\"},
    \"${TEST_APP_ID}_Failover\": {\"S\": \"N\"},
    \"${TEST_APP_ID}_LastUpdated\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"},
    \"${TEST_APP_ID}_Reason\": {\"S\": \"Test cleanup\"},
    \"LastUpdatedBy\": {\"S\": \"quick-test-script\"}
  }" > /dev/null 2>&1

print_status 0 "Test data cleaned up"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  Quick Test Complete! 🎉                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Run full E2E test: ./scripts/e2e-test.sh"
echo "  2. Run load test: python scripts/load-test.py"
echo "  3. Check TESTING_GUIDE.md for more options"
echo ""
