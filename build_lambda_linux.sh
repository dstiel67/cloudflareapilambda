#!/bin/bash
# Build Lambda deployment package with dependencies
# Optimized for Linux systems

set -e

echo "Building Lambda deployment package (Linux)..."

# Clean up previous build
echo "Cleaning up previous build..."
rm -rf lambda_package
rm -f lambda_function.zip

# Create package directory
mkdir -p lambda_package

# Copy Lambda function code
echo "Copying Lambda function code..."
cp -r lambda_function/*.py lambda_package/ 2>/dev/null || true
cp -r lambda_function/src lambda_package/

# Install dependencies with Linux-specific optimizations
echo "Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r lambda_function/requirements.txt -t lambda_package/ --quiet --no-cache-dir --disable-pip-version-check
elif command -v pip &> /dev/null; then
    pip install -r lambda_function/requirements.txt -t lambda_package/ --quiet --no-cache-dir --disable-pip-version-check
else
    echo "Error: pip not found. Please install pip."
    exit 1
fi

# Remove unnecessary files to reduce package size (Linux optimized)
echo "Cleaning up unnecessary files..."
cd lambda_package

# Remove test directories
echo "Removing test directories..."
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "test" -exec rm -rf {} + 2>/dev/null || true

# Remove cache directories
echo "Removing cache directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".tox" -exec rm -rf {} + 2>/dev/null || true

# Remove Python bytecode files
echo "Removing Python bytecode files..."
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true

# Remove documentation and development files
echo "Removing documentation files..."
find . -type f -name "*.md" -delete 2>/dev/null || true
find . -type f -name "*.rst" -delete 2>/dev/null || true
find . -type f -name "*.txt" -not -name "requirements.txt" -delete 2>/dev/null || true
find . -type f -name "LICENSE*" -delete 2>/dev/null || true
find . -type f -name "NOTICE*" -delete 2>/dev/null || true
find . -type f -name "CHANGELOG*" -delete 2>/dev/null || true

# Remove package metadata
echo "Removing package metadata..."
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Remove development and testing files
echo "Removing development files..."
find . -type f -name "*.cfg" -delete 2>/dev/null || true
find . -type f -name "setup.py" -delete 2>/dev/null || true
find . -type f -name "setup.cfg" -delete 2>/dev/null || true
find . -type f -name "pyproject.toml" -delete 2>/dev/null || true
find . -type f -name "tox.ini" -delete 2>/dev/null || true
find . -type f -name ".coverage" -delete 2>/dev/null || true

# Remove unnecessary binary files for Lambda (if any)
echo "Removing unnecessary binaries..."
find . -type f -name "*.so" -path "*/tests/*" -delete 2>/dev/null || true
find . -type f -name "*.dylib" -delete 2>/dev/null || true

# Create zip file using standard zip command
echo "Creating deployment package..."
cd ..

if command -v zip &> /dev/null; then
    cd lambda_package
    zip -r ../lambda_function.zip . -q -9  # Use maximum compression
    cd ..
else
    echo "Error: zip command not found. Please install zip."
    exit 1
fi

# Clean up temporary directory
rm -rf lambda_package

echo "✅ Lambda deployment package created: lambda_function.zip"

# Display package size
PACKAGE_SIZE=$(du -h lambda_function.zip | cut -f1)
PACKAGE_SIZE_BYTES=$(stat -c%s lambda_function.zip 2>/dev/null || stat -f%z lambda_function.zip 2>/dev/null || echo "unknown")

echo "Package size: $PACKAGE_SIZE ($PACKAGE_SIZE_BYTES bytes)"

# Check if package is within Lambda limits
if [ "$PACKAGE_SIZE_BYTES" != "unknown" ] && [ "$PACKAGE_SIZE_BYTES" -gt 52428800 ]; then
    echo "⚠️  Warning: Package size exceeds 50MB Lambda limit!"
else
    echo "✅ Package size is within Lambda limits"
fi

echo ""
echo "Build completed successfully!"
echo "You can now run 'terraform apply' to deploy the updated Lambda function."