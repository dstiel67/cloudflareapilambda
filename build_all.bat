@echo off
REM Build all Lambda deployment packages
REM Windows batch file version

echo Universal Lambda Build Script (Windows)
echo ========================================
echo Building all Lambda functions...
echo.

REM Track build results
set MAIN_BUILD_SUCCESS=false
set NOTIFICATION_BUILD_SUCCESS=false
set SSE_BUILD_SUCCESS=false

REM Build main Lambda function
echo Building main Lambda function...
call build_lambda.bat
if %errorlevel% == 0 (
    set MAIN_BUILD_SUCCESS=true
    echo ✅ Main Lambda function build completed successfully
) else (
    echo ❌ Main Lambda function build failed
)

echo.

REM Build notification Lambda function
echo Building notification Lambda function...
call build_notification_lambda.bat
if %errorlevel% == 0 (
    set NOTIFICATION_BUILD_SUCCESS=true
    echo ✅ Notification Lambda function build completed successfully
) else (
    echo ❌ Notification Lambda function build failed
)

echo.

REM Build SSE Lambda function
echo Building SSE Lambda function...
call build_sse_lambda.bat
if %errorlevel% == 0 (
    set SSE_BUILD_SUCCESS=true
    echo ✅ SSE Lambda function build completed successfully
) else (
    echo ❌ SSE Lambda function build failed
)

echo.
echo Build Summary:
echo ==============
if "%MAIN_BUILD_SUCCESS%"=="true" (
    echo Main Lambda:         ✅ SUCCESS
) else (
    echo Main Lambda:         ❌ FAILED
)

if "%NOTIFICATION_BUILD_SUCCESS%"=="true" (
    echo Notification Lambda: ✅ SUCCESS
) else (
    echo Notification Lambda: ❌ FAILED
)

if "%SSE_BUILD_SUCCESS%"=="true" (
    echo SSE Lambda:          ✅ SUCCESS
) else (
    echo SSE Lambda:          ❌ FAILED
)

echo.

REM Check if all builds succeeded
if "%MAIN_BUILD_SUCCESS%"=="true" if "%NOTIFICATION_BUILD_SUCCESS%"=="true" if "%SSE_BUILD_SUCCESS%"=="true" (
    echo 🎉 All Lambda functions built successfully!
    echo You can now run 'terraform apply' to deploy all functions.
    echo.
    pause
    exit /b 0
) else (
    echo ⚠️  Some builds failed. Please check the error messages above.
    echo.
    pause
    exit /b 1
)