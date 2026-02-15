#!/bin/bash
# Build SSE Lambda deployment package

set -e

echo "Building SSE Lambda deployment package..."

# Clean up previous build
rm -rf sse_package
rm -f sse_lambda.zip

# Create package directory
mkdir -p sse_package

# Copy Lambda function code
echo "Copying SSE Lambda function code..."
cp sse_lambda/*.py sse_package/

# Install dependencies (minimal for this function)
echo "Installing Python dependencies..."
if [ -f "sse_lambda/requirements.txt" ]; then
    pip3 install -r sse_lambda/requirements.txt -t sse_package/ --quiet --no-cache-dir || true
fi

# Remove unnecessary files
echo "Cleaning up unnecessary files..."
cd sse_package
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Create zip file
echo "Creating deployment package..."
cd ..
cd sse_package
zip -r ../sse_lambda.zip . -q
cd ..

# Clean up
rm -rf sse_package

echo "✅ SSE Lambda deployment package created: sse_lambda.zip"
echo "Package size: $(du -h sse_lambda.zip | cut -f1)"