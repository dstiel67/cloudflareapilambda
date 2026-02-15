#!/bin/bash
# Universal build script that detects OS and builds all Lambda functions

set -e

echo "Universal Lambda Build Script"
echo "============================="
echo "Building all Lambda functions..."

# Detect operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo "Detected: Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo "Detected: macOS"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
    echo "Detected: Windows (Git Bash/Cygwin)"
else
    OS="unknown"
    echo "Detected: Unknown OS ($OSTYPE)"
fi

echo ""

# Function to build main Lambda function
build_main_lambda() {
    echo "Building main Lambda function..."
    case $OS in
        "linux")
            echo "Using Linux-optimized build script..."
            if [ -f "build_lambda_linux.sh" ]; then
                ./build_lambda_linux.sh
            else
                echo "Error: build_lambda_linux.sh not found!"
                return 1
            fi
            ;;
        "macos"|"windows"|*)
            echo "Using cross-platform build script..."
            if [ -f "build_lambda.sh" ]; then
                ./build_lambda.sh
            else
                echo "Error: build_lambda.sh not found!"
                return 1
            fi
            ;;
    esac
}

# Function to build notification Lambda function
build_notification_lambda() {
    echo ""
    echo "Building notification Lambda function..."
    case $OS in
        "linux")
            echo "Using Linux-optimized notification build script..."
            if [ -f "build_notification_lambda_linux.sh" ]; then
                ./build_notification_lambda_linux.sh
            else
                echo "Error: build_notification_lambda_linux.sh not found!"
                return 1
            fi
            ;;
        "macos"|"windows"|*)
            echo "Using cross-platform notification build script..."
            if [ -f "build_notification_lambda.sh" ]; then
                ./build_notification_lambda.sh
            else
                echo "Error: build_notification_lambda.sh not found!"
                return 1
            fi
            ;;
    esac
}

# Function to build SSE Lambda function
build_sse_lambda() {
    echo ""
    echo "Building SSE Lambda function..."
    case $OS in
        "linux")
            echo "Using Linux-optimized SSE build script..."
            if [ -f "build_sse_lambda_linux.sh" ]; then
                ./build_sse_lambda_linux.sh
            else
                echo "Error: build_sse_lambda_linux.sh not found!"
                return 1
            fi
            ;;
        "macos"|"windows"|*)
            echo "Using cross-platform SSE build script..."
            if [ -f "build_sse_lambda.sh" ]; then
                ./build_sse_lambda.sh
            else
                echo "Error: build_sse_lambda.sh not found!"
                return 1
            fi
            ;;
    esac
}

# Function to build update Lambda function
build_update_lambda() {
    echo ""
    echo "Building update Lambda function..."
    if [ -f "build_update_lambda.sh" ]; then
        ./build_update_lambda.sh
    else
        echo "Error: build_update_lambda.sh not found!"
        return 1
    fi
}

# Function to build Kafka consumer Lambda function
build_kafka_consumer_lambda() {
    echo ""
    echo "Building Kafka consumer Lambda function..."
    if [ -f "build_kafka_consumer_lambda.sh" ]; then
        ./build_kafka_consumer_lambda.sh
    else
        echo "Error: build_kafka_consumer_lambda.sh not found!"
        return 1
    fi
}

# Build all Lambda functions
echo "Starting build process for all Lambda functions..."
echo ""

# Track build results
MAIN_BUILD_SUCCESS=false
NOTIFICATION_BUILD_SUCCESS=false
SSE_BUILD_SUCCESS=false
UPDATE_BUILD_SUCCESS=false
KAFKA_CONSUMER_BUILD_SUCCESS=false

# Build main Lambda function
if build_main_lambda; then
    MAIN_BUILD_SUCCESS=true
    echo "✅ Main Lambda function build completed successfully"
else
    echo "❌ Main Lambda function build failed"
fi

# Build notification Lambda function
if build_notification_lambda; then
    NOTIFICATION_BUILD_SUCCESS=true
    echo "✅ Notification Lambda function build completed successfully"
else
    echo "❌ Notification Lambda function build failed"
fi

# Build SSE Lambda function
if build_sse_lambda; then
    SSE_BUILD_SUCCESS=true
    echo "✅ SSE Lambda function build completed successfully"
else
    echo "❌ SSE Lambda function build failed"
fi

# Build update Lambda function
if build_update_lambda; then
    UPDATE_BUILD_SUCCESS=true
    echo "✅ Update Lambda function build completed successfully"
else
    echo "❌ Update Lambda function build failed"
fi

# Build Kafka consumer Lambda function
if build_kafka_consumer_lambda; then
    KAFKA_CONSUMER_BUILD_SUCCESS=true
    echo "✅ Kafka consumer Lambda function build completed successfully"
else
    echo "❌ Kafka consumer Lambda function build failed"
fi

# Summary
echo ""
echo "Build Summary:"
echo "=============="
echo "Main Lambda:          $([ "$MAIN_BUILD_SUCCESS" = true ] && echo "✅ SUCCESS" || echo "❌ FAILED")"
echo "Notification Lambda:  $([ "$NOTIFICATION_BUILD_SUCCESS" = true ] && echo "✅ SUCCESS" || echo "❌ FAILED")"
echo "SSE Lambda:           $([ "$SSE_BUILD_SUCCESS" = true ] && echo "✅ SUCCESS" || echo "❌ FAILED")"
echo "Update Lambda:        $([ "$UPDATE_BUILD_SUCCESS" = true ] && echo "✅ SUCCESS" || echo "❌ FAILED")"
echo "Kafka Consumer Lambda: $([ "$KAFKA_CONSUMER_BUILD_SUCCESS" = true ] && echo "✅ SUCCESS" || echo "❌ FAILED")"

# Check if all builds succeeded
if [ "$MAIN_BUILD_SUCCESS" = true ] && [ "$NOTIFICATION_BUILD_SUCCESS" = true ] && [ "$SSE_BUILD_SUCCESS" = true ] && [ "$UPDATE_BUILD_SUCCESS" = true ] && [ "$KAFKA_CONSUMER_BUILD_SUCCESS" = true ]; then
    echo ""
    echo "🎉 All Lambda functions built successfully!"
    echo "You can now run 'terraform apply' to deploy all functions."
    exit 0
else
    echo ""
    echo "⚠️  Some builds failed. Please check the error messages above."
    exit 1
fi