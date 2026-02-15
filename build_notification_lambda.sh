#!/bin/bash
# Build notification Lambda deployment package

set -e

echo "Building notification Lambda deployment package..."

# Clean up previous build
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
    pip3 install -r notification_lambda/requirements.txt -t notification_package/ --quiet --no-cache-dir || true
fi

# Remove unnecessary files
echo "Cleaning up unnecessary files..."
cd notification_package
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Create zip file
echo "Creating deployment package..."
cd ..
cd notification_package
zip -r ../notification_lambda.zip . -q
cd ..

# Clean up
rm -rf notification_package

echo "✅ Notification Lambda deployment package created: notification_lambda.zip"
echo "Package size: $(du -h notification_lambda.zip | cut -f1)"