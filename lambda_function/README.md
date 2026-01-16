# Cloudflare Data Sync Lambda Function

AWS Lambda function that retrieves data from Cloudflare KV API and stores it in DynamoDB.

## Project Structure

```
lambda_function/
├── lambda_function.py      # Main Lambda handler
├── requirements.txt        # Python dependencies
├── pytest.ini            # Test configuration
├── README.md              # This file
├── src/                   # Source code modules
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── cloudflare_client.py  # Cloudflare API client
│   ├── data_transformer.py   # Data transformation
│   ├── dynamodb_client.py    # DynamoDB operations
│   └── error_handler.py      # Error handling
└── tests/                 # Test files
    ├── __init__.py
    └── test_lambda_function.py
```

## Dependencies

- **boto3**: AWS SDK for Python
- **requests**: HTTP library for API calls
- **pytest**: Testing framework
- **pytest-mock**: Mocking utilities
- **hypothesis**: Property-based testing
- **moto**: AWS service mocking for tests

## Development

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
```bash
pytest
```

### Environment Variables Required

- `SECRETS_MANAGER_SECRET_NAME`: Name of the secret containing Cloudflare credentials
- `DYNAMODB_TABLE_NAME`: Target DynamoDB table name
- `RETRY_MAX_ATTEMPTS` (optional): Maximum retry attempts (default: 3)
- `API_TIMEOUT_SECONDS` (optional): API call timeout (default: 30)

### Secrets Manager Secret Format

```json
{
  "api_token": "cloudflare_api_token_here",
  "account_id": "cloudflare_account_id", 
  "kv_namespace_id": "kv_namespace_id",
  "kv_namespace": "namespace_name"
}
```

## Implementation Status

- [x] Task 1: Project structure and dependencies
- [ ] Task 2: Configuration management
- [ ] Task 3: Cloudflare API client
- [ ] Task 5: Data transformation
- [ ] Task 6: DynamoDB client
- [ ] Task 7: Error handling
- [ ] Task 9: Integration and main handler