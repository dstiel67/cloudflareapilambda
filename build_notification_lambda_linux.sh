#!/bin/bash
# Build notification Lambda deployment package (Linux optimized)

set -e

echo "Building notification Lambda deployment package (Linux)..."

# Clean up previous build
echo "Cleaning up previous build..."
rm -rf notification_package
rm -f notification_lambda.zip

# Create package directory
mkdir -p notification_package

# Copy Lambda function code
echo "Copying notification Lambda function code..."
cp notification_lambda/*.py notification_package/

# Install dependencies (minimal for this function)
echo "Installing Python dependencies..."
if [ -f "notification_lambda/requirements.txt" ]; then
    pip3 install -r notification_lambda/requirements.txt -t notification_package/ --quiet --no-cache-dir --disable-pip-version-check || true
fi

# Remove unnecessary files to reduce package size (Linux optimized)
echo "Cleaning up unnecessary files..."
cd notification_package

# Remove cache directories
echo "Removing cache directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Remove Python bytecode files
echo "Removing Python bytecode files..."
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true

# Remove documentation files
echo "Removing documentation files..."
find . -type f -name "*.md" -delete 2>/dev/null || true
find . -type f -name "*.rst" -delete 2>/dev/null || true
find . -type f -name "*.txt" -not -name "requirements.txt" -delete 2>/dev/null || true

# Remove package metadata
echo "Removing package metadata..."
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Create zip file with maximum compression
echo "Creating deployment package..."
cd ..
cd notification_package
zip -r ../notification_lambda.zip . -q -9  # Use maximum compression
cd ..

# Clean up
rm -rf notification_package

echo "✅ Notification Lambda deployment package created: notification_lambda.zip"

# Display package size
PACKAGE_SIZE=$(du -h notification_lambda.zip | cut -f1)
PACKAGE_SIZE_BYTES=$(stat -c%s notification_lambda.zip 2>/dev/null || stat -f%z notification_lambda.zip 2>/dev/null || echo "unknown")

echo "Package size: $PACKAGE_SIZE ($PACKAGE_SIZE_BYTES bytes)"

# Check if package is within Lambda limits
if [ "$PACKAGE_SIZE_BYTES" != "unknown" ] && [ "$PACKAGE_SIZE_BYTES" -gt 52428800 ]; then
    echo "⚠️  Warning: Package size exceeds 50MB Lambda limit!"
else
    echo "✅ Package size is within Lambda limits"
fi