# Build Scripts for Lambda Deployment Package

This project includes multiple build scripts to accommodate different operating systems and environments.

## Available Scripts

### 1. `build.sh` (Universal - Recommended)

**Platforms:** Auto-detects Linux, macOS, Windows with Git Bash
**Requirements:** bash, python3/pip3, zip or 7z

```bash
./build.sh
```

**Features:**
- Automatically detects your operating system
- Builds ALL Lambda functions (main, notification, SSE)
- Calls the optimal build script for your platform
- Linux → uses Linux-optimized scripts
- macOS/Windows → uses cross-platform scripts
- Comprehensive build summary and error reporting

### 2. `build_all.bat` (Windows Universal)

**Platforms:** Windows Command Prompt, PowerShell
**Requirements:** python/pip, 7z or PowerShell

```cmd
build_all.bat
```

**Features:**
- Native Windows batch file for all Lambda functions
- Builds main, notification, and SSE Lambda functions
- Uses 7z if available, falls back to PowerShell compression
- Comprehensive build summary and error reporting

### 3. Individual Lambda Build Scripts

#### Main Lambda Function
- `build_lambda_linux.sh` (Linux optimized)
- `build_lambda.sh` (Cross-platform)
- `build_lambda.bat` (Windows)

#### Notification Lambda Function
- `build_notification_lambda_linux.sh` (Linux optimized)
- `build_notification_lambda.sh` (Cross-platform)
- `build_notification_lambda.bat` (Windows)

#### SSE Lambda Function
- `build_sse_lambda_linux.sh` (Linux optimized)
- `build_sse_lambda.sh` (Cross-platform)
- `build_sse_lambda.bat` (Windows)

## Quick Start

### Recommended Approach (Universal)
```bash
./build.sh
```
*Automatically detects your OS and builds ALL Lambda functions using optimal scripts*

### Platform-Specific Approaches

#### Linux Users (Optimized)
```bash
./build.sh  # Builds all functions with Linux optimization
```

#### Windows Users
1. **With Git Bash (Recommended):**
   - Install [Git for Windows](https://git-scm.com/download/win)
   - Install [7-Zip](https://www.7-zip.org/)
   - Run: `./build.sh`

2. **With Command Prompt:**
   - Install [7-Zip](https://www.7-zip.org/) (optional but recommended)
   - Run: `build_all.bat`

#### Unix/macOS Users
```bash
./build.sh
```

### Automatic with Terraform
```bash
terraform apply
```
*Terraform automatically builds all packages using the appropriate scripts*

## What the Scripts Do

1. **Clean up** previous builds for all Lambda functions
2. **Create** temporary package directories (`lambda_package`, `notification_package`, `sse_package`)
3. **Copy** respective Lambda function code (`*.py` files and directories)
4. **Install** Python dependencies from each `requirements.txt`
5. **Remove** unnecessary files (tests, cache, docs, metadata)
6. **Create** deployment packages:
   - `lambda_function.zip` - Main sync Lambda (~33-34MB)
   - `notification_lambda.zip` - Notification handler (~15MB)
   - `sse_lambda.zip` - SSE endpoint (~15MB)
7. **Clean up** temporary files
8. **Report** package sizes and completion status

## Output

Both scripts create:
- `lambda_function.zip` - Ready-to-deploy Lambda package (~33MB)

## Troubleshooting

### Python Not Found
- Ensure Python 3.11+ is installed and in PATH
- Try: `python --version`, `python3 --version`, or `py --version`

### 7z Not Found (Windows)
- Install 7-Zip from [7-zip.org](https://www.7-zip.org/)
- Add `C:\Program Files\7-Zip\` to PATH environment variable
- Restart command prompt

### Permission Denied (Unix/Linux/macOS)
```bash
chmod +x build_lambda.sh
```

### Git Bash Issues (Windows)
- Use forward slashes: `./build_lambda.sh`
- Run from project root directory
- Ensure Python is accessible in Git Bash

## Manual Alternative

If scripts don't work, see [BUILD.md](BUILD.md) for manual build instructions.

## After Building

Deploy with Terraform:
```bash
terraform apply
```

The new package will be automatically detected and deployed.