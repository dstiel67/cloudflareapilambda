#!/bin/bash
# Build update Lambda deployment package

set -e

echo "Building update Lambda deployment package..."

# Clean up previous build
rm -rf update_package
rm -f update_lambda.zip

# Create package directory
mkdir -p update_package

# Copy Lambda function code
echo "Copying update Lambda function code..."
cp update_lambda/*.py update_package/

# Install dependencies (minimal for this function)
echo "Installing Python dependencies..."
if [ -f "update_lambda/requirements.txt" ]; then
    pip3 install -r update_lambda/requirements.txt -t update_package/ --quiet --no-cache-dir || true
fi

# Remove unnecessary files
echo "Cleaning up unnecessary files..."
cd update_package
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Create zip file
echo "Creating deployment package..."
cd ..
cd update_package
zip -r ../update_lambda.zip . -q
cd ..

# Clean up
rm -rf update_package

echo "✅ Update Lambda deployment package created: update_lambda.zip"
echo "Package size: $(du -h update_lambda.zip | cut -f1)"