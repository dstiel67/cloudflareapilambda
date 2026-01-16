#!/bin/bash
# Build Lambda deployment package with dependencies

set -e

echo "Building Lambda deployment package..."

# Clean up previous build
rm -rf lambda_package
rm -f lambda_function.zip

# Create package directory
mkdir -p lambda_package

# Copy Lambda function code
echo "Copying Lambda function code..."
cp -r lambda_function/*.py lambda_package/
cp -r lambda_function/src lambda_package/

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r lambda_function/requirements.txt -t lambda_package/ --quiet

# Remove unnecessary files to reduce package size
echo "Cleaning up unnecessary files..."
cd lambda_package
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.md" -delete
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Create zip file
echo "Creating deployment package..."
zip -r ../lambda_function.zip . -q

cd ..
rm -rf lambda_package

echo "✅ Lambda deployment package created: lambda_function.zip"
echo "Package size: $(du -h lambda_function.zip | cut -f1)"
