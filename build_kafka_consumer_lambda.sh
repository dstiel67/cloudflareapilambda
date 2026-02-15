#!/bin/bash
# Build script for Kafka Consumer Lambda function

set -e

echo "Building Kafka Consumer Lambda function..."

# Create temporary build directory
BUILD_DIR="kafka_consumer_build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy Lambda function code
cp kafka_consumer_lambda/lambda_function.py "$BUILD_DIR/"
cp kafka_consumer_lambda/requirements.txt "$BUILD_DIR/"

# Install dependencies
echo "Installing Python dependencies..."
pip install -r "$BUILD_DIR/requirements.txt" -t "$BUILD_DIR/" --quiet

# Create deployment package
echo "Creating deployment package..."
cd "$BUILD_DIR"
zip -r ../kafka_consumer_lambda.zip . -q
cd ..

# Cleanup
rm -rf "$BUILD_DIR"

# Get package size
PACKAGE_SIZE=$(du -h kafka_consumer_lambda.zip | cut -f1)
echo "✅ Kafka Consumer Lambda package created: kafka_consumer_lambda.zip ($PACKAGE_SIZE)"
