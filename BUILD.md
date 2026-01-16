# Building the Lambda Deployment Package

The Lambda function requires Python dependencies (boto3, requests) to be packaged with the code.

## Quick Build

Run the build script:

```bash
./build_lambda.sh
```

This will:
1. Create a temporary `lambda_package` directory
2. Copy the Lambda function code
3. Install Python dependencies from `requirements.txt`
4. Remove unnecessary files (tests, cache, etc.)
5. Create `lambda_function.zip` with everything

## Manual Build (Alternative)

If you prefer to build manually:

```bash
# Clean up
rm -rf lambda_package lambda_function.zip

# Create package directory
mkdir lambda_package

# Copy code
cp -r lambda_function/*.py lambda_package/
cp -r lambda_function/src lambda_package/

# Install dependencies
pip3 install -r lambda_function/requirements.txt -t lambda_package/

# Create zip
cd lambda_package
zip -r ../lambda_function.zip .
cd ..
rm -rf lambda_package
```

## When to Rebuild

Rebuild the package when:
- You modify any Python code in `lambda_function/`
- You update `requirements.txt`
- You add new dependencies

## Deployment

After building, deploy with Terraform:

```bash
terraform apply
```

Terraform will detect the new `lambda_function.zip` and update the Lambda function automatically.

## Package Size

The deployment package is approximately 33MB, which includes:
- Lambda function code
- boto3 (AWS SDK)
- requests (HTTP library)
- All dependencies

This is well within AWS Lambda's 50MB zipped / 250MB unzipped limit.

## Troubleshooting

### "pip: command not found"

Install pip:
```bash
# macOS
brew install python3

# Or use python3 -m pip instead
python3 -m pip install -r lambda_function/requirements.txt -t lambda_package/
```

### "Permission denied"

Make the script executable:
```bash
chmod +x build_lambda.sh
```

### Package too large

The script already removes unnecessary files. If still too large:
- Remove test dependencies from `requirements.txt`
- Use `--no-deps` flag for specific packages
- Consider using Lambda Layers for large dependencies
