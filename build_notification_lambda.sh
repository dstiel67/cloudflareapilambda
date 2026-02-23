#!/bin/bash
# Build notification Lambda deployment package
# Compatible with Windows Git Bash and 7z

set -e

echo "Building notification Lambda deployment package..."

# Detect operating system
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    IS_WINDOWS=true
    echo "Detected Windows environment with Git Bash"
else
    IS_WINDOWS=false
    echo "Detected Unix-like environment"
fi

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
    if $IS_WINDOWS; then
        # On Windows, try python first, then python3, then py
        if command -v python &> /dev/null; then
            python -m pip install -r notification_lambda/requirements.txt -t notification_package/ --quiet --no-cache-dir || true
        elif command -v python3 &> /dev/null; then
            python3 -m pip install -r notification_lambda/requirements.txt -t notification_package/ --quiet --no-cache-dir || true
        elif command -v py &> /dev/null; then
            py -m pip install -r notification_lambda/requirements.txt -t notification_package/ --quiet --no-cache-dir || true
        fi
    else
        # On Unix-like systems, prefer pip3
        if command -v pip3 &> /dev/null; then
            pip3 install -r notification_lambda/requirements.txt -t notification_package/ --quiet --no-cache-dir || true
        elif command -v pip &> /dev/null; then
            pip install -r notification_lambda/requirements.txt -t notification_package/ --quiet --no-cache-dir || true
        fi
    fi
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

if $IS_WINDOWS; then
    # Try to use 7z first (more reliable on Windows), then fall back to zip
    if command -v 7z &> /dev/null; then
        echo "Using 7z to create archive..."
        cd notification_package
        7z a -tzip ../notification_lambda.zip . -r > /dev/null
        cd ..
    elif command -v zip &> /dev/null; then
        echo "Using zip to create archive..."
        cd notification_package
        zip -r ../notification_lambda.zip . -q
        cd ..
    else
        echo "Error: Neither 7z nor zip found. Please install 7-Zip or ensure zip is available."
        echo "7-Zip can be downloaded from: https://www.7-zip.org/"
        exit 1
    fi
else
    # On Unix-like systems, use zip
    if command -v zip &> /dev/null; then
        cd notification_package
        zip -r ../notification_lambda.zip . -q
        cd ..
    else
        echo "Error: zip command not found. Please install zip."
        exit 1
    fi
fi

# Clean up
rm -rf notification_package

echo "✅ Notification Lambda deployment package created: notification_lambda.zip"

# Display package size
if $IS_WINDOWS; then
    # Use ls -lh which works in Git Bash
    PACKAGE_SIZE=$(ls -lh notification_lambda.zip | awk '{print $5}')
    echo "Package size: $PACKAGE_SIZE"
else
    # Use du on Unix-like systems
    echo "Package size: $(du -h notification_lambda.zip | cut -f1)"
fi