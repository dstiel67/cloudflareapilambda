#!/bin/bash
# Universal build script that detects OS and calls appropriate build script

set -e

echo "Universal Lambda Build Script"
echo "============================="

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

# Call appropriate build script
case $OS in
    "linux")
        echo "Using Linux-optimized build script..."
        if [ -f "build_lambda_linux.sh" ]; then
            ./build_lambda_linux.sh
        else
            echo "Error: build_lambda_linux.sh not found!"
            exit 1
        fi
        ;;
    "macos")
        echo "Using cross-platform build script for macOS..."
        if [ -f "build_lambda.sh" ]; then
            ./build_lambda.sh
        else
            echo "Error: build_lambda.sh not found!"
            exit 1
        fi
        ;;
    "windows")
        echo "Using cross-platform build script for Windows..."
        if [ -f "build_lambda.sh" ]; then
            ./build_lambda.sh
        else
            echo "Error: build_lambda.sh not found!"
            exit 1
        fi
        ;;
    *)
        echo "Unknown OS detected. Trying cross-platform build script..."
        if [ -f "build_lambda.sh" ]; then
            ./build_lambda.sh
        else
            echo "Error: build_lambda.sh not found!"
            exit 1
        fi
        ;;
esac