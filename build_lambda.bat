@echo off
REM Build Lambda deployment package with dependencies
REM Windows batch file version

echo Building Lambda deployment package...

REM Clean up previous build
echo Cleaning up previous build...
if exist lambda_package rmdir /s /q lambda_package
if exist lambda_function.zip del lambda_function.zip

REM Create package directory
mkdir lambda_package

REM Copy Lambda function code
echo Copying Lambda function code...
copy lambda_function\*.py lambda_package\ >nul 2>&1
xcopy lambda_function\src lambda_package\src\ /e /i /q >nul

REM Install dependencies
echo Installing Python dependencies...
python -m pip install -r lambda_function\requirements.txt -t lambda_package\ --quiet
if errorlevel 1 (
    echo Error: Failed to install dependencies. Trying with python3...
    python3 -m pip install -r lambda_function\requirements.txt -t lambda_package\ --quiet
    if errorlevel 1 (
        echo Error: Failed to install dependencies. Trying with py...
        py -m pip install -r lambda_function\requirements.txt -t lambda_package\ --quiet
        if errorlevel 1 (
            echo Error: Python not found or pip failed. Please ensure Python is installed and in PATH.
            exit /b 1
        )
    )
)

REM Remove unnecessary files to reduce package size
echo Cleaning up unnecessary files...
cd lambda_package

REM Remove test directories
for /d /r %%d in (tests) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

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
    cd lambda_package
    7z a -tzip ..\lambda_function.zip . -r >nul
    cd ..
) else (
    echo Using PowerShell to create archive...
    powershell -command "Compress-Archive -Path 'lambda_package\*' -DestinationPath 'lambda_function.zip' -Force"
)

REM Clean up temporary directory
rmdir /s /q lambda_package

echo.
echo ✅ Lambda deployment package created: lambda_function.zip

REM Display package size
for %%A in (lambda_function.zip) do echo Package size: %%~zA bytes

echo.
echo Build completed successfully!
echo You can now run 'terraform apply' to deploy the updated Lambda function.

pause