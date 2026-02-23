#!/bin/bash
# Build script for Kafka Consumer Lambda function
# Compatible with Windows Git Bash and 7z

set -e

echo "Building Kafka Consumer Lambda function..."

# Detect operating system
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    IS_WINDOWS=true
    echo "Detected Windows environment with Git Bash"
else
    IS_WINDOWS=false
    echo "Detected Unix-like environment"
fi

# Create temporary build directory
BUILD_DIR="kafka_consumer_build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy Lambda function code
cp kafka_consumer_lambda/lambda_function.py "$BUILD_DIR/"
cp kafka_consumer_lambda/requirements.txt "$BUILD_DIR/"

# Install dependencies
echo "Installing Python dependencies..."
if $IS_WINDOWS; then
    # On Windows, try python first, then python3, then py
    if command -v python &> /dev/null; then
        python -m pip install -r "$BUILD_DIR/requirements.txt" -t "$BUILD_DIR/" --quiet
    elif command -v python3 &> /dev/null; then
        python3 -m pip install -r "$BUILD_DIR/requirements.txt" -t "$BUILD_DIR/" --quiet
    elif command -v py &> /dev/null; then
        py -m pip install -r "$BUILD_DIR/requirements.txt" -t "$BUILD_DIR/" --quiet
    else
        echo "Error: Python not found. Please ensure Python is installed and in PATH."
        exit 1
    fi
else
    # On Unix-like systems, prefer pip3
    if command -v pip3 &> /dev/null; then
        pip3 install -r "$BUILD_DIR/requirements.txt" -t "$BUILD_DIR/" --quiet
    elif command -v pip &> /dev/null; then
        pip install -r "$BUILD_DIR/requirements.txt" -t "$BUILD_DIR/" --quiet
    else
        echo "Error: pip not found. Please ensure pip is installed."
        exit 1
    fi
fi

# Create deployment package
echo "Creating deployment package..."
cd "$BUILD_DIR"

if $IS_WINDOWS; then
    # Try to use 7z first (more reliable on Windows), then fall back to zip
    if command -v 7z &> /dev/null; then
        echo "Using 7z to create archive..."
        7z a -tzip ../kafka_consumer_lambda.zip . -r > /dev/null
    elif command -v zip &> /dev/null; then
        echo "Using zip to create archive..."
        zip -r ../kafka_consumer_lambda.zip . -q
    else
        echo "Error: Neither 7z nor zip found. Please install 7-Zip or ensure zip is available."
        echo "7-Zip can be downloaded from: https://www.7-zip.org/"
        exit 1
    fi
else
    # On Unix-like systems, use zip
    if command -v zip &> /dev/null; then
        zip -r ../kafka_consumer_lambda.zip . -q
    else
        echo "Error: zip command not found. Please install zip."
        exit 1
    fi
fi

cd ..

# Cleanup
rm -rf "$BUILD_DIR"

# Get package size
if $IS_WINDOWS; then
    # Use ls -lh which works in Git Bash
    PACKAGE_SIZE=$(ls -lh kafka_consumer_lambda.zip | awk '{print $5}')
else
    # Use du on Unix-like systems
    PACKAGE_SIZE=$(du -h kafka_consumer_lambda.zip | cut -f1)
fi

echo "✅ Kafka Consumer Lambda package created: kafka_consumer_lambda.zip ($PACKAGE_SIZE)"
