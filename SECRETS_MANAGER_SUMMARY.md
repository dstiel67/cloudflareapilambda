# Secrets Manager - Quick Answer

## Do I Need Secrets Manager?

**NO** - Not for normal operations.

## What Components Use Secrets Manager?

### Primary System (No Secrets Manager)
- ✅ Update API Lambda - **Does NOT use Secrets Manager**
- ✅ Notification Lambda - **Does NOT use Secrets Manager**
- ✅ SSE Endpoint Lambda - **Does NOT use Secrets Manager**
- ✅ DynamoDB Tables - **Do NOT use Secrets Manager**
- ✅ API Gateways - **Do NOT use Secrets Manager**

### Legacy Component (Uses Secrets Manager)
- ⚠️ Cloudflare Sync Lambda - **Only component that uses Secrets Manager**

## When Do I Need to Configure Secrets Manager?

**Only if** you want to use the legacy Cloudflare sync Lambda for:
- Initial data migration from Cloudflare KV
- Backup/sync operations from Cloudflare

## Normal Workflow (No Secrets Manager Needed)

```bash
# 1. Deploy infrastructure
terraform apply

# 2. Update redirect status
curl -X POST "$(terraform output -raw update_redirect_status_endpoint)" \
  -H "Content-Type: application/json" \
  -d '{"value": "ON", "updated_by": "admin"}'

# 3. Get current status
curl "$(terraform output -raw get_redirect_status_endpoint)"

# 4. Connect to SSE for real-time updates
curl -N -H "Accept: text/event-stream" "$(terraform output -raw sse_events_endpoint)"
```

**That's it!** No Secrets Manager configuration needed.

## Cost Impact

- **If you never configure Secrets Manager**: ~$0.40/month (secret exists but unused)
- **If you configure and use it**: ~$0.40/month + minimal API call costs

## Why Does Terraform Create It?

For backwards compatibility and flexibility. Users who need the legacy sync can use it without additional Terraform changes.

## Can I Remove It?

Yes, but you'd need to:
1. Remove the Secrets Manager resources from `lambda.tf`
2. Remove the IAM permissions for Secrets Manager access
3. Remove the environment variable from legacy Lambda
4. Accept that legacy Cloudflare sync won't work

**Recommendation**: Keep it. The cost is minimal ($0.40/month) and it provides flexibility.

## Key Takeaway

**Secrets Manager is optional infrastructure that's only used by the legacy Cloudflare sync Lambda. The primary system (Update API, Notifications, SSE) works perfectly without it.**
