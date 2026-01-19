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
- Calls the optimal build script for your platform
- Linux → `build_lambda_linux.sh`
- macOS → `build_lambda.sh`
- Windows → `build_lambda.sh`

### 2. `build_lambda_linux.sh` (Linux Optimized)

**Platforms:** Linux distributions
**Requirements:** bash, python3/pip3, zip

```bash
./build_lambda_linux.sh
```

**Features:**
- Linux-specific optimizations
- Maximum compression (-9 flag)
- Enhanced cleanup of unnecessary files
- Package size validation
- Optimized for CI/CD environments

### 3. `build_lambda.sh` (Cross-Platform)

**Platforms:** Unix, Linux, macOS, Windows with Git Bash
**Requirements:** bash, python3/pip3, zip or 7z

```bash
./build_lambda.sh
```

**Features:**
- Auto-detects Windows vs Unix environment
- Tries multiple Python commands (python, python3, py)
- Prefers 7z on Windows, zip on Unix
- Cross-platform file size reporting
- Comprehensive error handling

### 4. `build_lambda.bat` (Windows Native)

**Platforms:** Windows Command Prompt, PowerShell
**Requirements:** python/pip, 7z or PowerShell

```cmd
build_lambda.bat
```

**Features:**
- Native Windows batch file
- Tries multiple Python commands (python, python3, py)
- Uses 7z if available, falls back to PowerShell compression
- Windows-specific file operations
- Pauses at end for user review

## Quick Start

### Recommended Approach (Universal)
```bash
./build.sh
```
*Automatically detects your OS and uses the optimal build script*

### Platform-Specific Approaches

#### Linux Users (Optimized)
```bash
./build_lambda_linux.sh
```

#### Windows Users
1. **With Git Bash (Recommended):**
   - Install [Git for Windows](https://git-scm.com/download/win)
   - Install [7-Zip](https://www.7-zip.org/)
   - Run: `./build.sh` or `./build_lambda.sh`

2. **With Command Prompt:**
   - Install [7-Zip](https://www.7-zip.org/) (optional but recommended)
   - Run: `build_lambda.bat`

#### Unix/macOS Users
```bash
./build.sh
```
or
```bash
./build_lambda.sh
```

### Automatic with Terraform
```bash
terraform apply
```
*Terraform automatically builds the package using the appropriate script*

## What the Scripts Do

1. **Clean up** previous builds
2. **Create** temporary `lambda_package` directory
3. **Copy** Lambda function code (`*.py` files and `src/` directory)
4. **Install** Python dependencies from `requirements.txt`
5. **Remove** unnecessary files (tests, cache, docs, metadata)
6. **Create** `lambda_function.zip` deployment package
7. **Clean up** temporary files
8. **Report** package size and completion

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