@echo off
REM Build notification Lambda deployment package
REM Windows batch file version

echo Building notification Lambda deployment package...

REM Clean up previous build
echo Cleaning up previous build...
if exist notification_package rmdir /s /q notification_package
if exist notification_lambda.zip del notification_lambda.zip

REM Create package directory
mkdir notification_package

REM Copy Lambda function code
echo Copying notification Lambda function code...
copy notification_lambda\*.py notification_package\ >nul 2>&1

REM Install dependencies
echo Installing Python dependencies...
if exist notification_lambda\requirements.txt (
    python -m pip install -r notification_lambda\requirements.txt -t notification_package\ --quiet
    if errorlevel 1 (
        echo Error: Failed to install dependencies. Trying with python3...
        python3 -m pip install -r notification_lambda\requirements.txt -t notification_package\ --quiet
        if errorlevel 1 (
            echo Error: Failed to install dependencies. Trying with py...
            py -m pip install -r notification_lambda\requirements.txt -t notification_package\ --quiet
            if errorlevel 1 (
                echo Error: Python not found or pip failed. Please ensure Python is installed and in PATH.
                exit /b 1
            )
        )
    )
)

REM Remove unnecessary files to reduce package size
echo Cleaning up unnecessary files...
cd notification_package

REM Remove cache directories
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
for /d /r %%d in (.pytest_cache) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

REM Remove Python bytecode files
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul

REM Remove documentation files
del /s /q *.md 2>nul

REM Remove package metadata directories
for /d /r %%d in (*.dist-info) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
for /d /r %%d in (*.egg-info) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

REM Create zip file
echo Creating deployment package...
cd ..

REM Try 7z first, then fall back to PowerShell
where 7z >nul 2>&1
if %errorlevel% == 0 (
    echo Using 7z to create archive...
    cd notification_package
    7z a -tzip ..\notification_lambda.zip . -r >nul
    cd ..
) else (
    echo Using PowerShell to create archive...
    powershell -command "Compress-Archive -Path 'notification_package\*' -DestinationPath 'notification_lambda.zip' -Force"
)

REM Clean up temporary directory
rmdir /s /q notification_package

echo.
echo ✅ Notification Lambda deployment package created: notification_lambda.zip

REM Display package size
for %%A in (notification_lambda.zip) do echo Package size: %%~zA bytes

echo.
echo Notification Lambda build completed successfully!