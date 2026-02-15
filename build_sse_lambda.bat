@echo off
REM Build SSE Lambda deployment package
REM Windows batch file version

echo Building SSE Lambda deployment package...

REM Clean up previous build
echo Cleaning up previous build...
if exist sse_package rmdir /s /q sse_package
if exist sse_lambda.zip del sse_lambda.zip

REM Create package directory
mkdir sse_package

REM Copy Lambda function code
echo Copying SSE Lambda function code...
copy sse_lambda\*.py sse_package\ >nul 2>&1

REM Install dependencies
echo Installing Python dependencies...
if exist sse_lambda\requirements.txt (
    python -m pip install -r sse_lambda\requirements.txt -t sse_package\ --quiet
    if errorlevel 1 (
        echo Error: Failed to install dependencies. Trying with python3...
        python3 -m pip install -r sse_lambda\requirements.txt -t sse_package\ --quiet
        if errorlevel 1 (
            echo Error: Failed to install dependencies. Trying with py...
            py -m pip install -r sse_lambda\requirements.txt -t sse_package\ --quiet
            if errorlevel 1 (
                echo Error: Python not found or pip failed. Please ensure Python is installed and in PATH.
                exit /b 1
            )
        )
    )
)

REM Remove unnecessary files to reduce package size
echo Cleaning up unnecessary files...
cd sse_package

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
    cd sse_package
    7z a -tzip ..\sse_lambda.zip . -r >nul
    cd ..
) else (
    echo Using PowerShell to create archive...
    powershell -command "Compress-Archive -Path 'sse_package\*' -DestinationPath 'sse_lambda.zip' -Force"
)

REM Clean up temporary directory
rmdir /s /q sse_package

echo.
echo ✅ SSE Lambda deployment package created: sse_lambda.zip

REM Display package size
for %%A in (sse_lambda.zip) do echo Package size: %%~zA bytes

echo.
echo SSE Lambda build completed successfully!