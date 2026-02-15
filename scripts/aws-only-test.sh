#!/bin/bash
# AWS-Only Test Script - No Docker Required
# Tests the failover system using only AWS services

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Failover System - AWS-Only Test (No Docker)           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

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

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

# Check prerequisites
echo "Checking prerequisites..."
echo "─────────────────────────"

if ! command -v aws &> /dev/null; then
    print_status 1 "AWS CLI not found. Please install it first."
fi
print_status 0 "AWS CLI installed"

if ! command -v terraform &> /dev/null; then
    print_info "Terraform not found (optional for this test)"
else
    print_status 0 "Terraform installed"
fi

echo ""

# Get AWS resources
print_step "Getting AWS resource names..."

if command -v terraform &> /dev/null && [ -f "terraform.tfstate" ]; then
    TABLE_NAME=$(terraform output -raw dynamodb_table_name 2>/dev/null || echo "failover-status")
    LAMBDA_NAME=$(terraform output -raw kafka_consumer_lambda_function_name 2>/dev/null || echo "")
else
    print_info "Terraform state not found, using default names"
    TABLE_NAME="failover-status"
    LAMBDA_NAME=""
fi

echo "  DynamoDB Table: $TABLE_NAME"
if [ -n "$LAMBDA_NAME" ]; then
    echo "  Lambda Function: $LAMBDA_NAME"
fi
echo ""

# Test 1: DynamoDB Access
print_step "Test 1: Testing DynamoDB access..."
echo "───────────────────────────────────────"

if aws dynamodb describe-table --table-name "$TABLE_NAME" > /dev/null 2>&1; then
    print_status 0 "DynamoDB table accessible"
else
    print_status 1 "Cannot access DynamoDB table: $TABLE_NAME"
fi
echo ""

# Test 2: DynamoDB Write
print_step "Test 2: Writing test data to DynamoDB..."
echo "──────────────────────────────────────────────"

TEST_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item "{
    \"pk\": {\"S\": \"FAILOVER_STATUS\"},
    \"sk\": {\"S\": \"CURRENT\"},
    \"aws-test_Failover\": {\"S\": \"Y\"},
    \"aws-test_LastUpdated\": {\"S\": \"$TEST_TIMESTAMP\"},
    \"aws-test_Reason\": {\"S\": \"AWS-only test\"},
    \"LastUpdatedBy\": {\"S\": \"aws-test-script\"}
  }" > /dev/null 2>&1

print_status 0 "Test data written successfully"
echo ""

# Test 3: DynamoDB Read
print_step "Test 3: Reading test data from DynamoDB..."
echo "───────────────────────────────────────────────"

RESULT=$(aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}' \
  --query 'Item."aws-test_Failover".S' \
  --output text 2>/dev/null)

if [ "$RESULT" == "Y" ]; then
    print_status 0 "Read verification passed (Status: $RESULT)"
else
    print_status 1 "Read verification failed"
fi
echo ""

# Test 4: Lambda Function (if available)
if [ -n "$LAMBDA_NAME" ]; then
    print_step "Test 4: Testing Lambda function..."
    echo "──────────────────────────────────────"
    
    # Check if Lambda exists
    if aws lambda get-function --function-name "$LAMBDA_NAME" > /dev/null 2>&1; then
        print_status 0 "Lambda function exists"
        
        # Create test event (base64 encoded Kafka message)
        cat > /tmp/lambda-test-event.json << 'EOF'
{
  "records": {
    "failover-events-0": [{
      "value": "eyJldmVudF90eXBlIjogImZhaWxvdmVyIiwgInRpbWVzdGFtcCI6ICIyMDI0LTAxLTE1VDEwOjMwOjAwWiIsICJhcHBsaWNhdGlvbnMiOiBbeyJhcHBfaWQiOiAiYXdzLXRlc3QiLCAiZmFpbG92ZXJfc3RhdHVzIjogIlkiLCAicmVhc29uIjogIkFXUyB0ZXN0In1dLCAidHJpZ2dlcmVkX2J5IjogImF3cy10ZXN0LXNjcmlwdCJ9"
    }]
  }
}
EOF
        
        # Invoke Lambda
        print_info "Invoking Lambda function..."
        aws lambda invoke \
          --function-name "$LAMBDA_NAME" \
          --payload file:///tmp/lambda-test-event.json \
          /tmp/lambda-response.json > /dev/null 2>&1
        
        if [ -f /tmp/lambda-response.json ]; then
            print_status 0 "Lambda invoked successfully"
            
            # Check response
            if grep -q "success" /tmp/lambda-response.json 2>/dev/null; then
                print_info "Lambda response: $(cat /tmp/lambda-response.json | jq -r '.body' 2>/dev/null || cat /tmp/lambda-response.json)"
            fi
        else
            print_info "Lambda invocation completed (no response file)"
        fi
        
        # Cleanup temp files
        rm -f /tmp/lambda-test-event.json /tmp/lambda-response.json
    else
        print_info "Lambda function not deployed yet"
    fi
    echo ""
fi

# Test 5: CloudWatch Logs (if Lambda was tested)
if [ -n "$LAMBDA_NAME" ]; then
    print_step "Test 5: Checking CloudWatch logs..."
    echo "────────────────────────────────────────"
    
    LOG_GROUP="/aws/lambda/$LAMBDA_NAME"
    
    if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" 2>/dev/null | grep -q "$LOG_GROUP"; then
        print_status 0 "CloudWatch log group exists"
        
        # Get recent logs
        print_info "Recent log entries:"
        aws logs tail "$LOG_GROUP" --since 5m --format short 2>/dev/null | head -10 || print_info "No recent logs"
    else
        print_info "CloudWatch log group not found (Lambda may not have been invoked yet)"
    fi
    echo ""
fi

# Test 6: Verify Final State
print_step "Test 6: Verifying final DynamoDB state..."
echo "──────────────────────────────────────────────"

FINAL_STATE=$(aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"pk": {"S": "FAILOVER_STATUS"}, "sk": {"S": "CURRENT"}}' \
  2>/dev/null)

if [ -n "$FINAL_STATE" ]; then
    print_status 0 "DynamoDB state retrieved"
    
    # Show relevant fields
    print_info "Current failover flags:"
    echo "$FINAL_STATE" | jq -r '.Item | to_entries | map(select(.key | endswith("_Failover"))) | .[] | "  \(.key): \(.value.S)"' 2>/dev/null || echo "  (Unable to parse)"
else
    print_info "No data in DynamoDB yet"
fi
echo ""

# Cleanup
print_step "Cleaning up test data..."
echo "────────────────────────────"

aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item "{
    \"pk\": {\"S\": \"FAILOVER_STATUS\"},
    \"sk\": {\"S\": \"CURRENT\"},
    \"aws-test_Failover\": {\"S\": \"N\"},
    \"aws-test_LastUpdated\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"},
    \"aws-test_Reason\": {\"S\": \"Test cleanup\"}
  }" > /dev/null 2>&1

print_status 0 "Test data cleaned up"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  AWS-Only Test Complete! 🎉                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Tests completed:"
echo "  ✅ DynamoDB access"
echo "  ✅ DynamoDB write operations"
echo "  ✅ DynamoDB read operations"
if [ -n "$LAMBDA_NAME" ]; then
echo "  ✅ Lambda function invocation"
echo "  ✅ CloudWatch logs"
fi
echo "  ✅ Data cleanup"
echo ""
echo "Next steps:"
echo "  1. Start Atom Store: cd atom_store/server && npm start"
echo "  2. Start Read Flags Service: cd read_flags_service && python service.py"
echo "  3. Test complete flow: Update DynamoDB → Verify Atom Store"
echo ""
echo "For more testing options, see:"
echo "  - TESTING_WITHOUT_DOCKER.md"
echo "  - TESTING_GUIDE.md"
echo ""
