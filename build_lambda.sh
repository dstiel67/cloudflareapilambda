#!/bin/bash
# Build Lambda deployment package with dependencies
# Compatible with Windows Git Bash and 7z

set -e

echo "Building Lambda deployment package..."

# Detect operating system
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    IS_WINDOWS=true
    echo "Detected Windows environment with Git Bash"
else
    IS_WINDOWS=false
    echo "Detected Unix-like environment"
fi

# Clean up previous build
echo "Cleaning up previous build..."
if [ -d "lambda_package" ]; then
    rm -rf lambda_package
fi
if [ -f "lambda_function.zip" ]; then
    rm -f lambda_function.zip
fi

# Create package directory
mkdir -p lambda_package

# Copy Lambda function code
echo "Copying Lambda function code..."
cp -r lambda_function/*.py lambda_package/ 2>/dev/null || true
cp -r lambda_function/src lambda_package/

# Install dependencies
echo "Installing Python dependencies..."
if $IS_WINDOWS; then
    # On Windows, try python first, then python3, then py
    if command -v python &> /dev/null; then
        python -m pip install -r lambda_function/requirements.txt -t lambda_package/ --quiet
    elif command -v python3 &> /dev/null; then
        python3 -m pip install -r lambda_function/requirements.txt -t lambda_package/ --quiet
    elif command -v py &> /dev/null; then
        py -m pip install -r lambda_function/requirements.txt -t lambda_package/ --quiet
    else
        echo "Error: Python not found. Please ensure Python is installed and in PATH."
        exit 1
    fi
else
    # On Unix-like systems, prefer pip3
    if command -v pip3 &> /dev/null; then
        pip3 install -r lambda_function/requirements.txt -t lambda_package/ --quiet
    elif command -v pip &> /dev/null; then
        pip install -r lambda_function/requirements.txt -t lambda_package/ --quiet
    else
        echo "Error: pip not found. Please ensure pip is installed."
        exit 1
    fi
fi

# Remove unnecessary files to reduce package size
echo "Cleaning up unnecessary files..."
cd lambda_package

# Windows-compatible cleanup using find (available in Git Bash)
echo "Removing test directories..."
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

echo "Removing cache directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

echo "Removing Python bytecode files..."
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

echo "Removing documentation files..."
find . -type f -name "*.md" -delete 2>/dev/null || true

echo "Removing package metadata..."
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Create zip file
echo "Creating deployment package..."
cd ..

if $IS_WINDOWS; then
    # Try to use 7z first (more reliable on Windows), then fall back to zip
    if command -v 7z &> /dev/null; then
        echo "Using 7z to create archive..."
        cd lambda_package
        7z a -tzip ../lambda_function.zip . -r > /dev/null
        cd ..
    elif command -v zip &> /dev/null; then
        echo "Using zip to create archive..."
        cd lambda_package
        zip -r ../lambda_function.zip . -q
        cd ..
    else
        echo "Error: Neither 7z nor zip found. Please install 7-Zip or ensure zip is available."
        echo "7-Zip can be downloaded from: https://www.7-zip.org/"
        exit 1
    fi
else
    # On Unix-like systems, use zip
    if command -v zip &> /dev/null; then
        cd lambda_package
        zip -r ../lambda_function.zip . -q
        cd ..
    else
        echo "Error: zip command not found. Please install zip."
        exit 1
    fi
fi

# Clean up temporary directory
rm -rf lambda_package

echo "✅ Lambda deployment package created: lambda_function.zip"

# Display package size (Windows-compatible)
if $IS_WINDOWS; then
    # Use ls -lh which works in Git Bash
    PACKAGE_SIZE=$(ls -lh lambda_function.zip | awk '{print $5}')
    echo "Package size: $PACKAGE_SIZE"
else
    # Use du on Unix-like systems
    echo "Package size: $(du -h lambda_function.zip | cut -f1)"
fi

echo ""
echo "Build completed successfully!"
echo "You can now run 'terraform apply' to deploy the updated Lambda function."
