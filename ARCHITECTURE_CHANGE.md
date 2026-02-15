# Architecture Change: DynamoDB as Source of Truth

## Overview

The system architecture has been updated to use DynamoDB as the single source of truth for redirect status, replacing the previous Cloudflare KV-centric design.

## What Changed

### Previous Architecture (Cloudflare-Centric)
- Cloudflare KV was the source of truth
- Lambda function synced data FROM Cloudflare TO DynamoDB
- Read-only system for web clients
- Manual sync required to update status

### New Architecture (DynamoDB-Centric)
- **DynamoDB is now the source of truth**
- New Update API Lambda to modify redirect status
- Web clients can both read AND update status
- Real-time notifications when status changes
- Cloudflare sync Lambda is now optional (legacy)

## New Components

### 1. Update Lambda Function
- **File**: `update_lambda/lambda_function.py`
- **Purpose**: REST API to update redirect status in DynamoDB
- **Endpoints**:
  - `POST /redirect-status` - Update status (ON/OFF)
  - `GET /redirect-status` - Get current status
  - `GET /health` - Health check
- **Features**:
  - Validates input (ON/OFF only)
  - Stores audit trail (who, when, why)
  - Triggers DynamoDB Stream for notifications

### 2. Update API Infrastructure
- **File**: `update_api.tf`
- **Components**:
  - API Gateway for HTTP endpoints
  - Lambda function with DynamoDB permissions
  - CORS configuration
  - CloudWatch logging

### 3. Angular Update Service
- **File**: `angular-client-example/redirect-update.service.ts`
- **Methods**:
  - `updateRedirectStatus()` - Update with custom value
  - `turnRedirectOn()` - Turn redirect ON
  - `turnRedirectOff()` - Turn redirect OFF
  - `toggleRedirectStatus()` - Toggle current status
  - `getCurrentRedirectStatus()` - Get current status
  - `checkHealth()` - Health check

### 4. Enhanced Angular Component
- **File**: `angular-client-example/redirect-status.component.ts`
- **New Features**:
  - Update controls (ON/OFF/Toggle buttons)
  - Loading states during updates
  - Error handling and display
  - Refresh status button
  - Real-time feedback via SSE

## Data Flow

### Old Flow (Read-Only)
```
Cloudflare KV → Sync Lambda → DynamoDB → Stream → Notification → SSE → Client
```

### New Flow (Read/Write)
```
Admin Client → Update API → DynamoDB → Stream → Notification → SSE → All Clients
                                ↓
                          Source of Truth
```

## Benefits

1. **Direct Control**: Update status without Cloudflare API
2. **Real-Time Updates**: Immediate notifications to all clients
3. **Audit Trail**: Track who changed what and when
4. **Simplified Architecture**: One less external dependency
5. **Better Performance**: No Cloudflare API latency
6. **Cost Reduction**: No Cloudflare API calls for updates

## Migration Notes

### For Existing Deployments

1. **Build new Lambda package**:
   ```bash
   ./build.sh  # Builds all Lambda functions including update_lambda
   ```

2. **Deploy infrastructure**:
   ```bash
   terraform apply
   ```

3. **Get new endpoints**:
   ```bash
   terraform output update_api_base_url
   terraform output update_redirect_status_endpoint
   ```

4. **Update Angular configuration**:
   - Update `UPDATE_API_URL` in `redirect-update.service.ts`
   - Deploy updated Angular application

### Legacy Cloudflare Sync

The original Cloudflare sync Lambda (`cloudflare-data-sync`) is still available for:
- Initial data migration from Cloudflare KV
- Backup/sync operations if needed
- Can be removed if not needed

## Testing

### Test Update API
```bash
# Turn redirect ON
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -d '{"value": "ON", "updated_by": "admin", "reason": "Testing"}'

# Get current status
curl "$(terraform output -raw get_redirect_status_endpoint)"
```

### Test Real-Time Notifications
```bash
# Terminal 1: Connect to SSE
curl -N -H "Accept: text/event-stream" "$(terraform output -raw sse_events_endpoint)"

# Terminal 2: Update status
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -d '{"value": "OFF", "updated_by": "test"}'

# Terminal 1 should immediately show the update
```

## Documentation Updates

All documentation has been updated to reflect the new architecture:
- ✅ `README.md` - Updated with Update API usage
- ✅ `SYSTEM_OVERVIEW.md` - New architecture diagram and flow
- ✅ `angular-client-example/README.md` - Update service documentation
- ✅ `outputs.tf` - New Update API outputs
- ✅ `build.sh` - Builds update Lambda package

## Security Considerations

The Update API is currently **publicly accessible** with no authentication. Consider adding:
- AWS IAM authentication
- API keys
- Lambda authorizers
- Cognito user pools
- Rate limiting

## Next Steps

1. ✅ Complete Angular component implementation
2. ✅ Update all documentation
3. ✅ Add Update API outputs to Terraform
4. ⏭️ Test complete flow end-to-end
5. ⏭️ Consider adding authentication to Update API
6. ⏭️ Consider deprecating Cloudflare sync Lambda if not needed
7. ⏭️ Add monitoring/alerting for Update API
8. ⏭️ Implement rate limiting

## Summary

The system now provides a complete, self-contained solution for managing redirect status with real-time notifications. DynamoDB serves as the single source of truth, eliminating the dependency on Cloudflare KV for normal operations.
