# Building the Lambda Deployment Package

The Lambda function requires Python dependencies (boto3, requests) to be packaged with the code.

## Quick Build

### Universal Build Script (Recommended)

```bash
./build.sh
```
*Automatically detects your OS and builds ALL Lambda functions using optimal scripts*

### Platform-Specific Build Scripts

#### Linux (Optimized)

**All Lambda functions:**
```bash
./build.sh  # Recommended - builds all functions
```

**Individual functions:**
```bash
./build_lambda_linux.sh           # Main Lambda (optimized)
./build_notification_lambda_linux.sh  # Notification Lambda (optimized)
./build_sse_lambda_linux.sh       # SSE Lambda (optimized)
```

#### Unix/Linux/macOS or Windows with Git Bash

**All Lambda functions:**
```bash
./build.sh  # Recommended - builds all functions
```

**Individual functions:**
```bash
./build_lambda.sh                 # Main Lambda
./build_notification_lambda.sh    # Notification Lambda
./build_sse_lambda.sh             # SSE Lambda
```

#### Windows (Command Prompt/PowerShell)

**All Lambda functions:**
```cmd
build_all.bat
```

**Individual functions:**
```cmd
build_lambda.bat                  # Main Lambda
build_notification_lambda.bat     # Notification Lambda
build_sse_lambda.bat              # SSE Lambda
```

All scripts will:
1. Create temporary package directories for each Lambda
2. Copy the respective Lambda function code
3. Install Python dependencies from requirements.txt
4. Remove unnecessary files (tests, cache, etc.)
5. Create deployment zip files for each Lambda function

## Requirements

### All Platforms
- Python 3.11+ with pip installed and in PATH

### Windows Specific
- **Option 1**: Git Bash + 7-Zip (recommended)
  - Install [Git for Windows](https://git-scm.com/download/win) (includes Git Bash)
  - Install [7-Zip](https://www.7-zip.org/)
- **Option 2**: Command Prompt/PowerShell + 7-Zip
  - Install [7-Zip](https://www.7-zip.org/) and add to PATH
- **Option 3**: Command Prompt/PowerShell only
  - Uses built-in PowerShell compression (slower but works)

### Unix/Linux/macOS
- `zip` command (usually pre-installed)
- `find` command (usually pre-installed)

## Output Files

The build process creates these deployment packages:

- `lambda_function.zip` - Main Cloudflare sync Lambda (~33-34MB)
- `notification_lambda.zip` - DynamoDB Stream notification handler (~15MB)
- `sse_lambda.zip` - Server-Sent Events endpoint (~15MB)

## Manual Build (Alternative)

### Unix/Linux/macOS or Git Bash

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

### Windows Command Prompt

```cmd
REM Clean up
if exist lambda_package rmdir /s /q lambda_package
if exist lambda_function.zip del lambda_function.zip

REM Create package directory
mkdir lambda_package

REM Copy code
copy lambda_function\*.py lambda_package\
xcopy lambda_function\src lambda_package\src\ /e /i /q

REM Install dependencies
python -m pip install -r lambda_function\requirements.txt -t lambda_package\

REM Create zip (requires 7z or PowerShell)
7z a -tzip lambda_function.zip lambda_package\*
REM OR: powershell -command "Compress-Archive -Path 'lambda_package\*' -DestinationPath 'lambda_function.zip' -Force"

REM Clean up
rmdir /s /q lambda_package
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

### "pip: command not found" (Unix/Linux/macOS)

Install pip:
```bash
# macOS
brew install python3

# Or use python3 -m pip instead
python3 -m pip install -r lambda_function/requirements.txt -t lambda_package/
```

### "python: command not found" (Windows)

Try these alternatives:
```cmd
python3 -m pip install -r lambda_function\requirements.txt -t lambda_package\
REM OR
py -m pip install -r lambda_function\requirements.txt -t lambda_package\
```

### "Permission denied" (Unix/Linux/macOS)

Make the script executable:
```bash
chmod +x build_lambda.sh
```

### "7z: command not found" (Windows)

Install 7-Zip and add to PATH:
1. Download from [7-zip.org](https://www.7-zip.org/)
2. Install to default location (usually `C:\Program Files\7-Zip\`)
3. Add `C:\Program Files\7-Zip\` to your PATH environment variable
4. Restart your command prompt

### Package too large

The script already removes unnecessary files. If still too large:
- Remove test dependencies from `requirements.txt`
- Use `--no-deps` flag for specific packages
- Consider using Lambda Layers for large dependencies

### Git Bash on Windows Issues

If you encounter path issues in Git Bash:
- Use forward slashes in paths: `./build_lambda.sh`
- Ensure Python is accessible: `python --version`
- Try running from the project root directory
