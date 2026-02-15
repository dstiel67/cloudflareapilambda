# API Key Quick Reference Card

## Get Your API Key

```bash
terraform output -raw update_api_key_value
```

## Use in Requests

### Bash/cURL
```bash
API_KEY="your-api-key-here"

curl -X POST "https://your-api.amazonaws.com/prod/redirect-status" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "ON", "updated_by": "admin"}'
```

### TypeScript/Angular
```typescript
const headers = new HttpHeaders({
  'Content-Type': 'application/json',
  'x-api-key': this.API_KEY
});

this.http.post(url, data, { headers });
```

### Python
```python
headers = {
    'Content-Type': 'application/json',
    'x-api-key': os.environ['UPDATE_API_KEY']
}

requests.post(url, headers=headers, json=data)
```

### Node.js
```javascript
const headers = {
  'Content-Type': 'application/json',
  'x-api-key': process.env.UPDATE_API_KEY
};

axios.post(url, data, { headers });
```

## Endpoints

### Require API Key ✅
- `POST /redirect-status` - Update status
- `GET /redirect-status` - Get status

### Public (No Key) ✅
- `GET /health` - Health check
- `OPTIONS /redirect-status` - CORS

## Rate Limits

- **Rate**: 1,000 requests/second
- **Burst**: 2,000 requests
- **Quota**: 1,000,000 requests/month

## Error Responses

### 403 Forbidden
Missing or invalid API key
```json
{"message": "Forbidden"}
```

### 429 Too Many Requests
Rate limit exceeded
```json
{"message": "Too Many Requests"}
```

## Security Rules

### DO ✅
- Store in environment variables
- Use secrets management
- Rotate regularly
- Monitor usage

### DON'T ❌
- Hardcode in source code
- Commit to version control
- Log in plain text
- Share publicly

## Monitoring

```bash
# Check usage
aws apigateway get-usage \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --key-id "$API_KEY_ID"

# View logs
aws logs tail /aws/lambda/redirect-status-update --follow
```

## More Info

- Full Guide: `API_AUTHENTICATION.md`
- Summary: `API_AUTHENTICATION_SUMMARY.md`
- README: `README.md`
